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


# ---------------------------------------------------
# JSON / APPX RESOLVER
# ---------------------------------------------------

async def resolve_stream_url(session, url):

    if "appxapi.vercel.app/json/" not in url:
        return url

    async with session.get(url, headers=HEADERS) as resp:

        resp.raise_for_status()

        try:
            data = await resp.json()
        except Exception:
            text = await resp.text()

            try:
                data = json.loads(text)
            except Exception:
                return url

    candidates = [
        "url",
        "video_url",
        "stream_url",
        "master_m3u8",
        "m3u8",
        "playlist",
    ]

    for key in candidates:

        value = data.get(key)

        if isinstance(value, str) and value.startswith("http"):
            return value

    return url


# ---------------------------------------------------
# FILE DOWNLOAD
# ---------------------------------------------------

async def download_file(session, url, path):

    async with session.get(
        url,
        headers=HEADERS,
        allow_redirects=True
    ) as response:

        response.raise_for_status()

        with open(path, "wb") as f:

            async for chunk in response.content.iter_chunked(
                1024 * 1024
            ):
                f.write(chunk)


# ---------------------------------------------------
# M3U8 PROCESSOR
# ---------------------------------------------------

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


# ---------------------------------------------------
# SEND FILE
# ---------------------------------------------------

async def send_file(
    bot,
    chat_id,
    path,
    is_video=False
):

    with open(path, "rb") as f:

        if is_video:

            await bot.send_document(
                chat_id=chat_id,
                document=f,
                caption=path.name
            )

        else:

            await bot.send_document(
                chat_id=chat_id,
                document=f
            )


# ---------------------------------------------------
# MAIN COURSE HANDLER
# ---------------------------------------------------

async def handle_course(
    bot,
    chat_id,
    links
):

    timeout = aiohttp.ClientTimeout(
        total=7200
    )

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        for url in links:

            try:

                real_url = await resolve_stream_url(
                    session,
                    url
                )

                lower = real_url.lower()

                if any(
                    x in lower
                    for x in [".m3u8"]
                ):

                    filename = (
                        f"{int(time.time())}.mp4"
                    )

                else:

                    filename = get_name(
                        real_url
                    )

                path = DOWNLOAD_DIR / filename

                if ".m3u8" in lower:

                    rc = await process_stream(
                        real_url,
                        str(path)
                    )

                    if rc != 0:

                        raise Exception(
                            f"FFmpeg exited with code {rc}"
                        )

                else:

                    await download_file(
                        session,
                        real_url,
                        path
                    )

                is_video = any(
                    x in lower
                    for x in [
                        ".mp4",
                        ".mkv",
                        ".m3u8",
                        ".ts"
                    ]
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
                    f"❌ Failed\n\n{url}\n\n{e}"
                )

            finally:

                try:
                    if path.exists():
                        path.unlink()
                except Exception:
                    pass


# ---------------------------------------------------
# COMPATIBILITY FUNCTIONS
# ---------------------------------------------------

async def download_and_send_videos(
    bot,
    chat_id,
    urls,
    queue_manager=None,
):
    await handle_course(
        bot,
        chat_id,
        urls
    )


async def download_and_send_pdfs(
    bot,
    chat_id,
    urls,
):
    await handle_course(
        bot,
        chat_id,
        urls
    )


async def download_and_send_images(
    bot,
    chat_id,
    urls,
):
    await handle_course(
        bot,
        chat_id,
        urls
    )
