import asyncio
import logging
import os

logger = logging.getLogger("bot.ffmpeg")


# ───────────────────────── FFmpeg COMMAND BUILDER ─────────────────────────

def get_ffmpeg_cmd(input_file, output_file, fast_mode=True):

    cpu_threads = os.cpu_count() or 2

    if fast_mode:
        return [
            "ffmpeg", "-y",
            "-i", input_file,

            # ⚡ SPEED OPTIMIZATION
            "-preset", "ultrafast",
            "-threads", str(cpu_threads),
            "-loglevel", "error",

            # 🎬 VIDEO SETTINGS (FAST + STABLE)
            "-c:v", "libx264",
            "-crf", "30",

            # 🔊 AUDIO
            "-c:a", "aac",
            "-b:a", "128k",

            # ⚡ FAST START (STREAMING)
            "-movflags", "+faststart",

            output_file
        ]

    else:
        return [
            "ffmpeg", "-y",
            "-i", input_file,

            "-preset", "fast",
            "-threads", str(cpu_threads),
            "-loglevel", "error",

            "-c:v", "libx264",
            "-crf", "24",

            "-c:a", "aac",
            "-b:a", "192k",

            "-movflags", "+faststart",

            output_file
        ]


# ───────────────────────── FFmpeg RUNNER (SAFE) ─────────────────────────

async def run_ffmpeg(cmd, timeout=3600):
    """
    Safe FFmpeg runner:
    - prevents infinite hang
    - logs errors
    - Render-safe timeout
    """

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            _, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            logger.error("FFmpeg timeout reached, process killed")
            return -1

        if process.returncode != 0:
            logger.error("FFmpeg error: %s", stderr.decode(errors="ignore")[:500])

        return process.returncode

    except Exception as e:
        logger.error("FFmpeg crash: %s", e)
        return -1
