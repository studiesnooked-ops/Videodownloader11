import os
import asyncio
import aiohttp
import time
from pathlib import Path
from urllib.parse import urlparse

from utils.ffmpeg import run_ffmpeg

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_name(url):
    return str(int(time.time())) + "_" + urlparse(url).path.split("/")[-1]


async def download_file(session, url, path):
    async with session.get(url, headers=HEADERS) as r:
        with open(path, "wb") as f:
            while True:
                chunk = await r.content.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)


async def process_stream(url, out_path):
    cmd = [
        "ffmpeg",
        "-y",
        "-headers",
        "User-Agent: Mozilla/5.0\r\n",
        "-i",
        url,
        "-c",
        "copy",
        out_path
    ]
    await run_ffmpeg(cmd)


async def send_file(bot, chat_id, path, is_video=False):

    with open(path, "rb") as f:
        if is_video:
            await bot.send_video(chat_id, f, supports_streaming=True)
        else:
            await bot.send_document(chat_id, f)


async def handle_course(bot, chat_id, links):

    async with aiohttp.ClientSession() as session:

        for url in links:

            name = get_name(url)
            path = DOWNLOAD_DIR / name

            try:

                if "m3u8" in url:
                    await process_stream(url, str(path))

                else:
                    await download_file(session, url, path)

                is_video = any(x in url for x in ["mp4", "mkv", "m3u8"])

                await send_file(bot, chat_id, path, is_video)

                os.remove(path)

            except Exception as e:
                await bot.send_message(chat_id, f"❌ Failed: {url}")
