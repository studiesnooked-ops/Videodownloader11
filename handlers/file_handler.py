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
