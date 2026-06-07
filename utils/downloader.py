"""
Async video downloader with FFmpeg speed optimization.
Render-safe + 1GB support + cloud upload (S3/R2) + crash-proof pipeline.
"""

import asyncio
import logging
import os
import re
import time
import aiohttp
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse, unquote

from telegram import Bot

from utils.queue_manager import QueueManager
from utils.ffmpeg import get_ffmpeg_cmd, run_ffmpeg
from utils.cloud_storage import upload_to_s3   # ✅ STEP 5.3 ADD

logger = logging.getLogger("bot.downloader")

# ── STORAGE ─────────────────────────────
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# ── SETTINGS ─────────────────────────────
CHUNK_SIZE = 2 * 1024 * 1024
SEND_SIZE_LIMIT = 50 * 1024 * 1024
MAX_FILE_SIZE = 1024 * 1024 * 1024

CONNECT_TIMEOUT = 20
READ_TIMEOUT = 7200
MAX_RETRIES = 3
RETRY_DELAY = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
}


# ───────────────────────── FILE NAME ─────────────────────────

def _guess_filename(url: str) -> str:
    path = unquote(urlparse(url).path)
    name = path.split("/")[-1]
    name = re.sub(r"\?.*", "", name)

    if not name or "." not in name:
        name = f"video_{int(time.time())}.mp4"

    name = re.sub(r"[^\w.\-]", "_", name)
    return f"{int(time.time())}_{name}"


# ───────────────────────── DOWNLOAD CORE ─────────────────────────

async def _download_one(session, url, dest_path, progress_cb=None):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with session.get(url, headers=HEADERS) as resp:
                resp.raise_for_status()

                total = int(resp.headers.get("Content-Length", 0))

                # block huge files early
                if total and total > MAX_FILE_SIZE:
                    logger.warning("File >1GB skipped")
                    return False

                done = 0

                with open(dest_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                        f.write(chunk)
                        done += len(chunk)

                        if progress_cb and total:
                            await progress_cb(done, total)

            return True

        except Exception as e:
            logger.warning("Download error %s (attempt %d)", e, attempt)

        await asyncio.sleep(RETRY_DELAY * attempt)

    return False


# ───────────────────────── MAIN PIPELINE ─────────────────────────

async def download_and_send_videos(
    bot: Bot,
    chat_id: int,
    urls: List[str],
    queue_manager: Optional[QueueManager] = None,
):

    connector = aiohttp.TCPConnector(
        limit=20,
        limit_per_host=8,
        ttl_dns_cache=300,
        ssl=False
    )

    timeout = aiohttp.ClientTimeout(
        connect=CONNECT_TIMEOUT,
        total=READ_TIMEOUT
    )

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout
    ) as session:

        sem = asyncio.Semaphore(2)

        async def worker(i, url):
            async with sem:
                await _process(bot, chat_id, session, i, url, len(urls))

        await asyncio.gather(
            *[worker(i, u) for i, u in enumerate(urls, 1)],
            return_exceptions=True
        )

    await bot.send_message(chat_id, "✅ All videos processed successfully.")


# ───────────────────────── PROCESS SINGLE ─────────────────────────

async def _process(bot, chat_id, session, idx, url, total):

    msg = await bot.send_message(
        chat_id,
        f"⬇️ {idx}/{total} Downloading..."
    )

    filename = _guess_filename(url)
    raw_file = DOWNLOAD_DIR / f"raw_{filename}"
    final_file = DOWNLOAD_DIR / f"final_{filename}"

    last_update = [0]

    async def progress(done, total_bytes):
        now = time.time()
        if now - last_update[0] < 2:
            return
        last_update[0] = now

        pct = (done / total_bytes) * 100 if total_bytes else 0
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))

        try:
            await msg.edit_text(
                f"⬇️ {idx}/{total}\n{bar} {pct:.0f}%"
            )
        except:
            pass

    # ── DOWNLOAD ──
    success = await _download_one(session, url, raw_file, progress)

    if not success:
        await msg.edit_text(f"❌ Failed {idx}/{total}")
        return

    # ── FFmpeg PROCESSING ──
    try:
        # FORCE MKV OUTPUT FOR LARGE FILES
output_name = str(final_file).replace(".mp4", ".mkv")

cmd = get_ffmpeg_cmd(
    str(raw_file),
    output_name,
    fast_mode=True
)

        await run_ffmpeg(cmd)

    except Exception as e:
        await msg.edit_text(f"⚠️ FFmpeg error: {e}")
        return

    size = final_file.stat().st_size

    # ── OUTPUT LOGIC ──
    if size <= SEND_SIZE_LIMIT:
        try:
            with open(final_file, "rb") as f:
                await bot.send_video(
                    chat_id,
                    video=f,
                    caption=f"🎬 {filename}"
                )
            await msg.delete()

        except Exception as e:
            await msg.edit_text(f"⚠️ Send error: {e}")

    else:
        # ── STEP 5.3 CLOUD UPLOAD ──
        try:
            file_url = await upload_to_s3(str(final_file), filename)

            if not file_url:
                raise Exception("Upload failed")

            await msg.edit_text(
                "📦 File too large for Telegram\n\n"
                f"Size: {size/1024/1024:.2f} MB\n"
                f"☁️ Download link:\n{file_url}"
            )

        except Exception as e:
            logger.error("Cloud upload error: %s", e)
            await msg.edit_text(
                "❌ File too large AND upload failed\n"
                f"Size: {size/1024/1024:.2f} MB"
            )

    # ── CLEANUP ──
    try:
        raw_file.unlink(missing_ok=True)
        final_file.unlink(missing_ok=True)
    except Exception as e:
        logger.warning("Cleanup failed: %s", e)
