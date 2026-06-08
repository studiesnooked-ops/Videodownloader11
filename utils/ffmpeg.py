"""
FFmpeg helper utilities for Telegram Video Bot
"""

import asyncio
import logging

logger = logging.getLogger("bot.ffmpeg")


# ───────────────────────── COMMAND BUILDER ─────────────────────────

def get_ffmpeg_cmd(input_file: str, output_file: str, fast_mode: bool = True):
    """
    Build FFmpeg command for MP4/MKV conversion
    """

    if fast_mode:
        return [
            "ffmpeg", "-y",
            "-i", input_file,
            "-preset", "ultrafast",
            "-threads", "0",
            "-loglevel", "error",
            "-c:v", "libx264",
            "-crf", "30",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_file
        ]

    return [
        "ffmpeg", "-y",
        "-i", input_file,
        "-preset", "fast",
        "-threads", "0",
        "-loglevel", "error",
        "-c:v", "libx264",
        "-crf", "24",
        "-c:a", "aac",
        "-b:a", "192k",
        output_file
    ]


# ───────────────────────── RUNNER ─────────────────────────

async def run_ffmpeg(cmd: list) -> int:
    """
    Run FFmpeg asynchronously and return exit code
    """

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error("FFmpeg error: %s", stderr.decode(errors="ignore"))

        return process.returncode

    except Exception as e:
        logger.exception("FFmpeg execution failed: %s", e)
        return 1
