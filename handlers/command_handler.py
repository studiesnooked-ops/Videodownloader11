"""
Command handlers for Telegram Video Extractor Bot.
PRO Version
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger("bot.commands")


HELP_TEXT = """
📖 PRO VIDEO EXTRACTOR BOT

━━━━━━━━━━━━━━━━━━
AVAILABLE COMMANDS
━━━━━━━━━━━━━━━━━━

/start
/help
/status
/cancel

━━━━━━━━━━━━━━━━━━
SUPPORTED INPUT
━━━━━━━━━━━━━━━━━━

✅ MP4
✅ MKV
✅ M3U8
✅ HLS Streams
✅ TXT Course Dumps
✅ PDF Notes

━━━━━━━━━━━━━━━━━━
TXT FORMAT
━━━━━━━━━━━━━━━━━━

Course Video:
https://example.com/video.m3u8

Course Notes:
https://example.com/notes.pdf

━━━━━━━━━━━━━━━━━━
LIMITS
━━━━━━━━━━━━━━━━━━

📄 TXT Size:
100 MB

🎥 Video Size:
1 GB

📚 Notes:
PDF Supported

⚡ Concurrent Jobs:
2 per User

━━━━━━━━━━━━━━━━━━
OUTPUT
━━━━━━━━━━━━━━━━━━

≤ 50MB
→ Sent directly to Telegram

> 50MB
→ Download link generated

━━━━━━━━━━━━━━━━━━
FEATURES
━━━━━━━━━━━━━━━━━━

✅ MP4 Download

✅ MKV Download

✅ M3U8 Extraction

✅ PDF Notes Download

✅ Auto Retry

✅ Progress Bar

✅ Queue System

✅ Stuck Job Recovery

✅ Crash Protection

✅ Render Optimized

━━━━━━━━━━━━━━━━━━
"""


async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = """
🎬 PRO VIDEO EXTRACTOR BOT

Send a TXT file containing:

✅ MP4 Links

✅ MKV Links

✅ M3U8 Streams

✅ PDF Notes

━━━━━━━━━━━━━━━━━━

The bot will:

📥 Extract links

📥 Download videos

📥 Download notes

📤 Send files or download links

━━━━━━━━━━━━━━━━━━

Maximum Video Size:
1 GB

Maximum URLs:
500+

━━━━━━━━━━━━━━━━━━

Use /help for full details.
"""

    await update.message.reply_text(text)


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        HELP_TEXT
    )


async def status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    qm = context.bot_data.get("queue_manager")

    if not qm:
        await update.message.reply_text(
            "⚠️ Queue Manager unavailable."
        )
        return

    stats = qm.get_stats(
        update.effective_user.id
    )

    text = (
        "📊 BOT STATUS\n\n"

        f"🟢 Active Jobs: {stats['global_active']}\n"
        f"🟡 Queued Jobs: {stats['global_queued']}\n\n"

        f"👤 Your Active Jobs: {stats['user_active']}\n"
        f"📥 Your Queued Jobs: {stats['user_queued']}\n"
        f"✅ Completed Today: {stats['user_completed']}\n\n"

        f"⚙ Workers: {stats['max_workers']}\n"
        f"👤 Max/User: {stats.get('max_per_user', 2)}"
    )

    await update.message.reply_text(text)


async def cancel_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    qm = context.bot_data.get("queue_manager")

    if not qm:
        await update.message.reply_text(
            "⚠️ Queue Manager unavailable."
        )
        return

    count = qm.cancel_user_jobs(
        update.effective_user.id
    )

    await update.message.reply_text(
        f"❌ Cancelled {count} job(s)."
    )
