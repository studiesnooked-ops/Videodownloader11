"""
FFmpeg helper utilities for Telegram Video Bot
"""

import asyncio
import logging
import shutil

logger = logging.getLogger("bot.ffmpeg")


# ─────────────────────────────────────────────
# FFmpeg Installed?
# ─────────────────────────────────────────────

def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


# ─────────────────────────────────────────────
# Command Builder
# ─────────────────────────────────────────────

def get_ffmpeg_cmd(
    input_file: str,
    output_file: str,
    fast_mode: bool = True,
    copy_mode: bool = False,
):
    """
    Build FFmpeg command.

    copy_mode=True
        Stream copy (fastest)

    fast_mode=True
        Faster encode

    fast_mode=False
        Better quality encode
    """

    if copy_mode:
        return [
            "ffmpeg",
            "-y",
            "-i",
            input_file,
            "-c",
            "copy",
            "-loglevel",
            "error",
            output_file,
        ]

    if fast_mode:
        return [
            "ffmpeg",
            "-y",
            "-i",
            input_file,
            "-preset",
            "ultrafast",
            "-threads",
            "0",
            "-loglevel",
            "error",
            "-c:v",
            "libx264",
            "-crf",
            "30",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            output_file,
        ]

    return [
        "ffmpeg",
        "-y",
        "-i",
        input_file,
        "-preset",
        "fast",
        "-threads",
        "0",
        "-loglevel",
        "error",
        "-c:v",
        "libx264",
        "-crf",
        "24",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        output_file,
    ]


# ─────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────

async def run_ffmpeg(cmd: list) -> int:
    """
    Run FFmpeg asynchronously.
    Returns process exit code.
    """

    if not ffmpeg_available():
        logger.error("FFmpeg not installed")
        return 1

    try:

        logger.info("Running FFmpeg: %s", " ".join(cmd))

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if stdout:
            logger.debug(stdout.decode(errors="ignore"))

        if process.returncode != 0:
            logger.error(
                "FFmpeg failed (%s): %s",
                process.returncode,
                stderr.decode(errors="ignore"),
            )

        return process.returncode

    except Exception as e:
        logger.exception("FFmpeg execution failed: %s", e)
        return 1
