import asyncio

def get_ffmpeg_cmd(input_file, output_file, fast_mode=True):

    # FORCE MKV for large stability (BEST FOR 1GB+)
    output_file = output_file.replace(".mp4", ".mkv")

    if fast_mode:
        return [
            "ffmpeg", "-y",
            "-i", input_file,

            # ── FIX FOR M3U8 STREAMS ──
            "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
            "-c:v", "copy",
            "-c:a", "copy",

            # ── FAST + STABLE ──
            "-threads", "0",
            "-preset", "ultrafast",

            output_file
        ]

    return [
        "ffmpeg", "-y",
        "-i", input_file,

        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",

        "-c:a", "aac",
        "-b:a", "192k",

        "-movflags", "+faststart",
        "-threads", "0",

        output_file
    ]


async def run_ffmpeg(cmd):
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()
    return process.returncode
