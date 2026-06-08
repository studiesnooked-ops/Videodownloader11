#!/usr/bin/env python3
"""
Telegram Video Extractor Bot (PRO Render Web Service Mode)
Stable + Queue System + Safe File Server + Crash-Proof
"""

import os
import sys
import logging
import threading
import asyncio
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

# ── HANDLERS ─────────────────────────────────────────────
from handlers.file_handler import handle_txt_file
from handlers.command_handler import (
    start_command,
    help_command,
    status_command,
    cancel_command,
)
from handlers.callback_handler import handle_callback

# ── CORE SYSTEM ──────────────────────────────────────────
from utils.logger import setup_logger
from utils.queue_manager import QueueManager
from utils.health_server import run_health_server

# OPTIONAL FILE SERVER (SAFE IMPORT)
try:
    from utils.file_server import run_file_server
    FILE_SERVER_ENABLED = True
except Exception:
    run_file_server = None
    FILE_SERVER_ENABLED = False


# ── CONFIG ───────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", 3))
PORT = int(os.environ.get("PORT", 10000))

logger = setup_logger("bot", "logs/bot.log")


# ── ENV VALIDATION ───────────────────────────────────────
def validate_env():
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN missing!")
        sys.exit(1)


# ── LIFECYCLE INIT ───────────────────────────────────────
async def post_init(application: Application):

    qm = QueueManager(
        max_workers=MAX_WORKERS,
        max_user_jobs=2,
        job_timeout=3600
    )

    application.bot_data["queue_manager"] = qm
    logger.info("QueueManager started (%d workers)", MAX_WORKERS)

    # ── CLEANUP LOOP (SAFE BACKGROUND TASK) ──
    async def cleanup_loop():
        while True:
            try:
                await asyncio.sleep(300)  # 5 minutes
                await qm.cleanup_stuck_jobs()
                logger.info("Stuck job cleanup executed")
            except Exception as e:
                logger.error("Cleanup loop error: %s", e)

    asyncio.create_task(cleanup_loop())


# ── SHUTDOWN ─────────────────────────────────────────────
async def post_shutdown(application: Application):

    qm = application.bot_data.get("queue_manager")

    if qm:
        await qm.shutdown()

    logger.info("Bot shutdown complete")


# ── APPLICATION BUILDER ──────────────────────────────────
def build_application() -> Application:

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .concurrent_updates(True)
        .build()
    )

    # ── COMMANDS ──
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("cancel", cancel_command))

    # ── FILE HANDLER ──
    app.add_handler(MessageHandler(filters.Document.TXT, handle_txt_file))

    # ── CALLBACK HANDLER ──
    app.add_handler(handle_callback)

    return app


# ── MAIN START ───────────────────────────────────────────
def main():

    validate_env()

    # create required folders
    for folder in ("logs", "uploads", "downloads"):
        Path(folder).mkdir(exist_ok=True)

    application = build_application()

    logger.info("🚀 Bot starting in WEB SERVICE MODE (Render)")

    # ── HEALTH SERVER ──
    try:
        threading.Thread(
            target=run_health_server,
            args=(PORT,),
            daemon=True,
            name="health-server"
        ).start()
        logger.info("Health server started on port %s", PORT)

    except Exception as e:
        logger.error("Health server failed: %s", e)

    # ── FILE SERVER (OPTIONAL SAFE) ──
    if FILE_SERVER_ENABLED and run_file_server:

        try:
            threading.Thread(
                target=run_file_server,
                args=(8000,),
                daemon=True,
                name="file-server"
            ).start()

            logger.info("File server started on port 8000")

        except Exception as e:
            logger.error("File server failed: %s", e)

    # ── START BOT ──
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )

    except Exception as e:
        logger.critical("Bot crashed: %s", e)


if __name__ == "__main__":
    main()
