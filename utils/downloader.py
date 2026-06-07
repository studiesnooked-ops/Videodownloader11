"""
Async video downloader with FFmpeg speed optimization.
Render-safe + 1GB support + no-crash architecture.
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

logger = logging.getLogger("bot.downloader")

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# ── SPEED + LIMITS ─────────────────────────────
CHUNK_SIZE = 2 * 1024 * 1024          # 2MB FAST MODE
SEND_SIZE_LIMIT = 50 * 1024 * 1024    # Telegram limit
MAX_FILE_SIZE = 1024 * 1024 * 1024    # 1GB SUPPORT

CONNECT_TIMEOUT = 15
READ_TIMEOUT = 3600   # IMPORTANT for 1GB
MAX_RETRIES = 3
RETRY_DELAY = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
}


# ───────────────────────── FILE NAME ─────────────────────────

def _guess_filename(url: str, content_type: str = "") -> str:
    path = unquote(urlparse(url).path)
    name = path.split("/")[-1]
    name = re.sub(r"\?.*", "", name)

    if not name or "." not in name:
        name = f"video_{int(time.time())}.mp4"

    return re.sub(r"[^\w.\-]", "_", name)


# ───────────────────────── DOWNLOAD CORE ─────────────────────────

async def _download_one(session, url, dest_path, progress_cb=None):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with session.get(url, headers=HEADERS) as resp:
                resp.raise_for_status()

                # 🔥 BLOCK >1GB FILES EARLY
                total = int(resp.headers.get("Content-Length", 0))
                if total and total > MAX_FILE_SIZE:
                    logger.warning("File too large (>1GB), skipping")
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
) -> None:

    connector = aiohttp.TCPConnector(
        limit=25,
        limit_per_host=10,
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

        sem = asyncio.Semaphore(2)  # Render-safe

        async def worker(i, url):
            async with sem:
                await _process(bot, chat_id, session, i, url, len(urls))

        tasks = [
            asyncio.create_task(worker(i, u))
            for i, u in enumerate(urls, 1)
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

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

    success = await _download_one(session, url, raw_file, progress)

    if not success:
        await msg.edit_text(f"❌ Failed {idx}/{total}")
        return

    # ── FFmpeg PROCESSING ──
    try:
        cmd = get_ffmpeg_cmd(
            str(raw_file),
            str(final_file),
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
        file_url = f"{os.environ.get('RENDER_EXTERNAL_URL')}/file/{filename}"

        await msg.edit_text(
            "📦 File too large for Telegram\n\n"
            f"Size: {size/1024/1024:.2f} MB\n"
            f"🔗 Download:\n{file_url}"
        )

    # ── CLEANUP ──
    try:
        raw_file.unlink(missing_ok=True)
        final_file.unlink(missing_ok=True)
    except Exception:
        pass
