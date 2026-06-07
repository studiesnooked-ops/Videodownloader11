async def ffmpeg_download(url, output_file):
    cmd = [
        "ffmpeg", "-y",
        "-i", url,

        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",

        "-threads", "0",
        output_file
    ]

    process = await asyncio.create_subprocess_exec(*cmd)
    await process.communicate()
