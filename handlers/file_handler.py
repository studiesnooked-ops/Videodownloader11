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
        "-headers", "User-Agent: Mozilla/5.0\r\n",
        "-i", url,
        "-c", "copy",
        out_path
    ]
    await run_ffmpeg(cmd)

async def send_file(bot, chat_id, path, is_video=False):
    with open(path, "rb") as f:
        if is_video:
            await bot.send_video(chat_id, f, supports_streaming=True)
        else:
            await bot.send_document(chat_id, f)

async def fetch_video_url(session, api_url):
    """Extract video URL from JSON API response"""
    try:
        async with session.get(api_url, headers=HEADERS) as response:
            data = await response.json()
            
            video_url = (
                data.get("video_url") or 
                data.get("url") or 
                data.get("link") or
                data.get("download_url") or
                data.get("data", {}).get("video_url") or
                data.get("data", {}).get("url") or
                data.get("result", {}).get("video_url") or
                data.get("result", {}).get("url")
            )
            
            return video_url
    except Exception as e:
        print(f"Error fetching video URL: {e}")
        return None

async def handle_course(bot, chat_id, links):
    async with aiohttp.ClientSession() as session:
        for url in links:
            name = get_name(url)
            path = DOWNLOAD_DIR / name
            
            try:
                if "json" in url or "api" in url:
                    # It's an API URL - fetch video URL from JSON
                    video_url = await fetch_video_url(session, url)
                    
                    if not video_url:
                        await bot.send_message(chat_id, f"❌ No video URL found in API response")
                        continue
                    
                    print(f"Extracted URL: {video_url}")
                    
                    # Check if extracted URL is also an API
                    if "json" in video_url or "api" in video_url:
                        video_url = await fetch_video_url(session, video_url)
                    
                    await process_stream(video_url, str(path))
                    
                elif "m3u8" in url:
                    # Direct m3u8 stream
                    await process_stream(url, str(path))
                    
                else:
                    # Direct file download
                    await download_file(session, url, path)
                
                # Detect file type
                is_video = path.suffix.lower() in [".mp4", ".mkv", ".avi", ".mov"] or "m3u8" in url
                
                # Send to Telegram
                await send_file(bot, chat_id, path, is_video)
                
                # Cleanup
                if path.exists():
                    os.remove(path)
                    
            except Exception as e:
                await bot.send_message(chat_id, f"❌ Failed: {str(e)}")
                print(f"Error: {e}")

async def handle_txt_file(bot, chat_id, file_path):
    """Handle text file download and send"""
    try:
        with open(file_path, "rb") as f:
            await bot.send_document(chat_id, f)
    except Exception as e:
        await bot.send_message(chat_id, f"❌ Error: {str(e)}")

async def download_and_send_videos(bot, chat_id, urls, queue_manager=None):
    await handle_course(bot, chat_id, urls)

async def download_and_send_pdfs(bot, chat_id, urls):
    await handle_course(bot, chat_id, urls)

async def download_and_send_images(bot, chat_id, urls):
    await handle_course(bot, chat_id, urls)
