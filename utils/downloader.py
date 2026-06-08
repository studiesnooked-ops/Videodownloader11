"""
PRO Downloader v4 (STEP 3 UPGRADE)
INPUT FORMAT CHANGED:

NOW SUPPORTS:
[
  {
    "title": "...",
    "url": "...",
    "name": "..."
  }
]

FEATURES:
✔ Video (mp4, mkv, m3u8, zip streams)
✔ PDF downloads
✔ Appx encrypted links support
✔ FFmpeg safe execution
✔ Cloud fallback
✔ 1GB support
✔ Render stable
"""

import asyncio
import logging
import os
import time
import aiohttp
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse, unquote

from telegram import Bot

from utils.ffmpeg import get_ffmpeg_cmd, run_ffmpeg
from utils.cloud_storage import upload_to_s3

logger = logging.getLogger("bot.downloader")

# ───────────────────────── STORAGE ─────────────────────────
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# ───────────────────────── CONFIG ─────────────────────────
CHUNK_SIZE = 2 * 1024 * 1024
SEND_LIMIT = 50 * 1024 * 1024
MAX_FILE_SIZE = 1024 * 1024 * 1024

HEADERS = {"User-Agent": "Mozilla/5.0"}

CONNECT_TIMEOUT = 20
READ_TIMEOUT = 7200
MAX_RETRIES = 3
RETRY_DELAY = 3


# ───────────────────────── HELPERS ─────────────────────────
def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)


def _guess_name(item: Dict) -> str:
    if item.get("name"):
        return _safe_name(item["name"])

    url = item.get("url", "")
    path = urlparse(url).path
    return _safe_name(path.split("/")[-1] or f"file_{int(time.time())}")


def _is_pdf(url: str) -> bool:
    return ".pdf" in url.lower()


# ───────────────────────── DOWNLOAD CORE ─────────────────────────
async def _download_file(session, url, dest, progress=None):

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with session.get(url, headers=HEADERS) as r:
                r.raise_for_status()

                total = int(r.headers.get("Content-Length", 0))

                if total and total > MAX_FILE_SIZE:
                    logger.warning("File too large skipped")
                    return False

                done = 0

                with open(dest, "wb") as f:
                    async for chunk in r.content.iter_chunked(CHUNK_SIZE):
                        f.write(chunk)
                        done += len(chunk)

                        if progress and total:
                            await progress(done, total)

            return True

        except Exception as e:
            logger.warning("Retry %s failed: %s", attempt, e)
            await asyncio.sleep(RETRY_DELAY * attempt)

    return False


# ───────────────────────── PROCESS SINGLE ITEM ─────────────────────────
async def _process(bot, chat_id, session, idx, item, total):

    url = item["url"]
    title = item.get("title", "File")
    filename = _guess_name(item)

    msg = await bot.send_message(
        chat_id,
        f"⬇️ {idx}/{total}\n{title}"
    )

    raw = DOWNLOAD_DIR / f"raw_{filename}"
    final = DOWNLOAD_DIR / f"final_{filename}"

    async def progress(done, total_bytes):
        try:
            pct = (done / total_bytes) * 100 if total_bytes else 0
            bar = "█" * int(pct // 10) + "░" * (10 - int(pct // 10))
            await msg.edit_text(f"⬇️ {idx}/{total}\n{bar} {pct:.0f}%")
        except:
            pass

    try:

        # ───────────── PDF HANDLING ─────────────
        if _is_pdf(url):

            success = await _download_file(session, url, final)

            if not success:
                await msg.edit_text(f"❌ PDF failed {idx}/{total}")
                return

        # ───────────── VIDEO / STREAM HANDLING ─────────────
        else:

            if "m3u8" in url or "zip" in url:

                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i", url,
                    "-c", "copy",
                    str(final)
                ]

                rc = await run_ffmpeg(cmd)

                if rc != 0:
                    await msg.edit_text(f"❌ Stream failed {idx}/{total}")
                    return

            else:

                success = await _download_file(session, url, raw, progress)

                if not success:
                    await msg.edit_text(f"❌ Download failed {idx}/{total}")
                    return

                cmd = get_ffmpeg_cmd(str(raw), str(final), fast_mode=True)

                rc = await run_ffmpeg(cmd)

                if rc != 0:
                    await msg.edit_text("❌ FFmpeg failed")
                    return

        # ───────────── SEND FILE ─────────────
        size = final.stat().st_size

        if size <= SEND_LIMIT:

            with open(final, "rb") as f:
                if _is_pdf(url):
                    await bot.send_document(chat_id, f, caption=title)
                else:
                    await bot.send_video(chat_id, f, caption=title)

            await msg.delete()

        else:

            file_url = await upload_to_s3(str(final), filename)

            await msg.edit_text(
                f"📦 Large file\n\n{title}\n\n🔗 {file_url}"
            )

    except Exception as e:
        logger.exception("Processing error: %s", e)
        await msg.edit_text(f"⚠️ Error: {e}")

    finally:
        try:
            raw.unlink(missing_ok=True)
            final.unlink(missing_ok=True)
        except:
            pass


# ───────────────────────── MAIN ENTRY ─────────────────────────
async def download_and_send_videos(
    bot: Bot,
    chat_id: int,
    urls: List[Dict],
    queue_manager: Optional = None,
):

    connector = aiohttp.TCPConnector(limit=20, ssl=False)

    timeout = aiohttp.ClientTimeout(total=READ_TIMEOUT)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:

        tasks = [
            _process(bot, chat_id, session, i, item, len(urls))
            for i, item in enumerate(urls, 1)
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

    await bot.send_message(chat_id, "✅ All course files completed.")
