import json
import time
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

from utils.ffmpeg import run_ffmpeg

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_name(url: str) -> str:
    name = urlparse(url).path.split("/")[-1]

    if not name:
        name = f"file_{int(time.time())}"

    return f"{int(time.time())}_{name}"


async def download_file(session, url, path):
    async with session.get(url, headers=HEADERS) as response:
        response.raise_for_status()

        with open(path, "wb") as f:
            async for chunk in response.content.iter_chunked(1024 * 1024):
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
        out_path,
    ]

    return await run_ffmpeg(cmd)


async def send_file(bot, chat_id, path, is_video=False):
    with open(path, "rb") as f:

        if is_video:
            await bot.send_video(
                chat_id=chat_id,
                video=f,
                supports_streaming=True,
            )
        else:
            await bot.send_document(
                chat_id=chat_id,
                document=f,
            )


async def handle_course(bot, chat_id, links):

    timeout = aiohttp.ClientTimeout(total=7200)

    async with aiohttp.ClientSession(timeout=timeout) as session:

        for url in links:

            filename = get_name(url)
            path = DOWNLOAD_DIR / filename

            try:

                lower = url.lower()

                if ".m3u8" in lower:

                    rc = await process_stream(
                        url,
                        str(path)
                    )

                    if rc != 0:
                        raise Exception(
                            f"FFmpeg exited with code {rc}"
                        )

                else:

                    await download_file(
                        session,
                        url,
                        path
                    )

                is_video = (
                    ".mp4" in lower
                    or ".mkv" in lower
                    or ".m3u8" in lower
                )

                await send_file(
                    bot,
                    chat_id,
                    path,
                    is_video
                )

            except Exception as e:

                await bot.send_message(
                    chat_id,
                    f"❌ Failed:\n{url}\n\n{e}"
                )

            finally:

                try:
                    if path.exists():
                        path.unlink()
                except Exception:
                    pass


async def download_and_send_videos(
    bot,
    chat_id,
    urls,
    queue_manager=None,
):
    await handle_course(bot, chat_id, urls)


async def download_and_send_pdfs(
    bot,
    chat_id,
    urls,
):
    await handle_course(bot, chat_id, urls)


async def download_and_send_images(
    bot,
    chat_id,
    urls,
):
    await handle_course(bot, chat_id, urls)
