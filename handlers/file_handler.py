"""
PRO File Handler v2
Supports:
- Appx course TXT parsing
- Videos (m3u8 / mkv / zip / mp4)
- PDF notes
- Structured course extraction
- Queue system integration
"""

import logging
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes

from utils.file_utils import cleanup_file
from utils.content_engine import parse_course_text

logger = logging.getLogger("bot.file_handler")

# ───────────────────────── CONFIG ─────────────────────────
MAX_FILE_SIZE = 50 * 1024 * 1024   # 50MB
MAX_VIDEOS = 2000


# ───────────────────────── MAIN HANDLER ─────────────────────────
async def handle_txt_file(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:

    doc = update.message.document
    user = update.effective_user

    if not doc:
        return

    # ───────────────────────── SIZE CHECK ─────────────────────────
    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            f"❌ File too large.\nLimit: {MAX_FILE_SIZE // (1024*1024)} MB"
        )
        return

    status = await update.message.reply_text("📂 Parsing course file...")

    upload_path = None

    try:
        # ───────────────────────── DOWNLOAD TXT ─────────────────────────
        tg_file = await context.bot.get_file(doc.file_id)

        upload_path = Path("uploads") / f"{user.id}_{doc.file_name}"
        await tg_file.download_to_drive(str(upload_path))

        with open(upload_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        cleanup_file(upload_path)

        # ───────────────────────── PARSE COURSE ─────────────────────────
        parsed = parse_course_text(text)

        videos = parsed.get("videos", [])
        pdfs = parsed.get("pdfs", [])

        # ───────────────────────── LIMIT SAFETY ─────────────────────────
        if len(videos) > MAX_VIDEOS:
            videos = videos[:MAX_VIDEOS]

        total_items = len(videos) + len(pdfs)

        if total_items == 0:
            await status.edit_text(
                "❌ No valid course content found.\n\n"
                "Supported:\n"
                "• MKV / MP4 / M3U8 / ZIP\n"
                "• PDF Notes\n"
                "• Appx Course Links"
            )
            return

        # ───────────────────────── SAVE SESSION ─────────────────────────
        context.bot_data[f"videos_{user.id}"] = videos
        context.bot_data[f"pdfs_{user.id}"] = pdfs

        # ───────────────────────── PREVIEW ─────────────────────────
        preview_lines = []

        for i, item in enumerate(videos[:5], start=1):
            preview_lines.append(
                f"`{i}.` {item['title'][:50]}..."
            )

        preview_text = "\n".join(preview_lines)

        # ───────────────────────── BUTTONS ─────────────────────────
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"🎬 Download Videos ({len(videos)})",
                    callback_data=f"dl_all_{user.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    f"📄 PDFs ({len(pdfs)})",
                    callback_data=f"pdfs_{user.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "📋 List All URLs",
                    callback_data=f"list_{user.id}"
                ),
                InlineKeyboardButton(
                    "🔢 Pick Videos",
                    callback_data=f"pick_{user.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Cancel",
                    callback_data=f"cancel_{user.id}"
                )
            ]
        ])

        # ───────────────────────── RESPONSE ─────────────────────────
        await status.edit_text(
            f"✅ Course File Parsed Successfully\n\n"
            f"🎬 Videos : {len(videos)}\n"
            f"📄 PDFs   : {len(pdfs)}\n\n"
            f"📌 Preview:\n{preview_text}\n\n"
            f"Choose an action below:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.exception("File processing failed: %s", e)

        await status.edit_text(
            f"❌ Error while processing file:\n`{e}`",
            parse_mode="Markdown"
        )

    finally:
        if upload_path and upload_path.exists():
            try:
                cleanup_file(upload_path)
            except Exception:
                pass
