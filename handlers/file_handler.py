"""
PRO File Handler (RENDER SAFE FULL VERSION)
Handles:
- Video URLs (.mp4, .mkv, .m3u8)
- PDF URLs (safe placeholder support)
- Image URLs
- Large TXT parsing
- Queue integration ready
"""

import logging
import re
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils.url_parser import parse_video_urls
from utils.file_utils import cleanup_file

logger = logging.getLogger("bot.file_handler")

# ───────────────────────── CONFIG ─────────────────────────
MAX_FILE_SIZE = 50 * 1024 * 1024   # 50MB TXT limit
MAX_URLS = 2000

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# ───────────────────────── MAIN HANDLER ─────────────────────────
async def handle_txt_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    doc = update.message.document
    user = update.effective_user

    if not doc:
        return

    # ───────────────── FILE SIZE CHECK ─────────────────
    if doc.file_size and doc.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            f"❌ TXT file too large.\n\n"
            f"Max allowed: {MAX_FILE_SIZE // (1024 * 1024)} MB"
        )
        return

    status = await update.message.reply_text("📂 Processing your TXT file...")

    upload_path = None

    try:
        # ───────────────── DOWNLOAD FILE ─────────────────
        tg_file = await context.bot.get_file(doc.file_id)

        safe_name = re.sub(r"[^\w\.-]", "_", doc.file_name or "file.txt")
        upload_path = UPLOAD_DIR / f"{user.id}_{safe_name}"

        await tg_file.download_to_drive(str(upload_path))

        # ───────────────── READ FILE ─────────────────
        with open(upload_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        cleanup_file(upload_path)

        # ───────────────── PARSE VIDEO URLS ─────────────────
        all_urls = parse_video_urls(text)

        # ───────────────── SEPARATE TYPES ─────────────────
        videos = []
        pdfs = []
        images = []

        for url in all_urls:
            u = url.lower()

            if ".pdf" in u:
                pdfs.append(url)
            elif any(x in u for x in [".jpg", ".jpeg", ".png", ".webp"]):
                images.append(url)
            else:
                videos.append(url)

        # ───────────────── LIMIT SAFETY ─────────────────
        videos = videos[:MAX_URLS]
        pdfs = pdfs[:MAX_URLS]
        images = images[:MAX_URLS]

        total = len(videos) + len(pdfs) + len(images)

        if total == 0:
            await status.edit_text(
                "❌ No supported content found.\n\n"
                "Supported:\n"
                "• MP4 / MKV / M3U8\n"
                "• PDF\n"
                "• JPG / PNG"
            )
            return

        # ───────────────── SAVE SESSION ─────────────────
        context.bot_data[f"videos_{user.id}"] = videos
        context.bot_data[f"pdfs_{user.id}"] = pdfs
        context.bot_data[f"images_{user.id}"] = images

        # ───────────────── PREVIEW ─────────────────
        preview = "\n".join(
            f"`{i+1}.` {u[:55]}"
            for i, u in enumerate(videos[:5])
        )

        # ───────────────── BUTTON UI ─────────────────
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
                ),
                InlineKeyboardButton(
                    f"🖼 Images ({len(images)})",
                    callback_data=f"thumbs_{user.id}"
                )
            ],

            [
                InlineKeyboardButton(
                    "📋 List All",
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

        # ───────────────── FINAL RESPONSE ─────────────────
        await status.edit_text(
            f"✅ TXT Parsed Successfully\n\n"
            f"🎬 Videos : {len(videos)}\n"
            f"📄 PDFs   : {len(pdfs)}\n"
            f"🖼 Images : {len(images)}\n\n"
            f"{preview}\n\n"
            "Choose an action below:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.exception("TXT processing failed")
        await status.edit_text(f"❌ Error:\n`{e}`", parse_mode="Markdown")

    finally:
        if upload_path and upload_path.exists():
            try:
                cleanup_file(upload_path)
            except Exception:
                pass
