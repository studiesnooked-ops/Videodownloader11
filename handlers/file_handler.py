"""
PRO File Handler
Supports:
- Videos (.mp4 .mkv .m3u8)
- PDF Notes
- Course Thumbnails
- Download Queue System
"""

import logging
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes

from utils.url_parser import parse_content
from utils.file_utils import cleanup_file

logger = logging.getLogger("bot.file_handler")

# TXT upload size
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# URLs inside txt
MAX_URLS = 2000


async def handle_txt_file(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:

    doc = update.message.document
    user = update.effective_user

    if not doc:
        return

    # --------------------------------------------------
    # FILE SIZE CHECK
    # --------------------------------------------------

    if doc.file_size and doc.file_size > MAX_FILE_SIZE:

        await update.message.reply_text(
            f"❌ TXT file too large.\n\n"
            f"Limit: {MAX_FILE_SIZE // (1024 * 1024)} MB"
        )
        return

    status = await update.message.reply_text(
        "📂 Reading TXT file..."
    )

    upload_path = None

    try:

        # --------------------------------------------------
        # DOWNLOAD TXT
        # --------------------------------------------------

        tg_file = await context.bot.get_file(doc.file_id)

        upload_path = (
            Path("uploads")
            / f"{user.id}_{doc.file_name}"
        )

        await tg_file.download_to_drive(
            str(upload_path)
        )

        with open(
            upload_path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as f:

            text = f.read()

        cleanup_file(upload_path)

        # --------------------------------------------------
        # PARSE CONTENT
        # --------------------------------------------------

        parsed = parse_content(text)

        videos = parsed["videos"]
        pdfs = parsed["pdfs"]
        images = parsed["images"]

        total_items = (
            len(videos)
            + len(pdfs)
            + len(images)
        )

        if total_items == 0:

            await status.edit_text(
                "❌ No supported URLs found.\n\n"
                "Supported:\n"
                "• MP4\n"
                "• MKV\n"
                "• M3U8\n"
                "• PDF\n"
                "• JPG / PNG"
            )

            return

        # --------------------------------------------------
        # LIMITS
        # --------------------------------------------------

        if len(videos) > MAX_URLS:
            videos = videos[:MAX_URLS]

        # --------------------------------------------------
        # SAVE DATA
        # --------------------------------------------------

        context.bot_data[
            f"videos_{user.id}"
        ] = videos

        context.bot_data[
            f"pdfs_{user.id}"
        ] = pdfs

        context.bot_data[
            f"images_{user.id}"
        ] = images

        # --------------------------------------------------
        # PREVIEW
        # --------------------------------------------------

        preview = []

        for i, url in enumerate(videos[:5], start=1):
            preview.append(
                f"`{i}.` {_truncate(url, 55)}"
            )

        preview_text = "\n".join(preview)

        # --------------------------------------------------
        # BUTTONS
        # --------------------------------------------------

        keyboard = InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    f"🎬 Download Videos ({len(videos)})",
                    callback_data=f"dl_all_{user.id}"
                )
            ],

            [
                InlineKeyboardButton(
                    f"📄 Notes ({len(pdfs)})",
                    callback_data=f"pdfs_{user.id}"
                ),

                InlineKeyboardButton(
                    f"🖼 Thumbnails ({len(images)})",
                    callback_data=f"thumbs_{user.id}"
                )
            ],

            [
                InlineKeyboardButton(
                    "📋 List URLs",
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

        # --------------------------------------------------
        # RESULT
        # --------------------------------------------------

        await status.edit_text(
            f"✅ TXT Parsed Successfully\n\n"

            f"🎬 Videos : {len(videos)}\n"
            f"📄 PDFs   : {len(pdfs)}\n"
            f"🖼 Images : {len(images)}\n\n"

            f"{preview_text}\n\n"

            f"Choose an action below.",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except Exception as e:

        logger.exception(
            "TXT processing failed: %s",
            e
        )

        await status.edit_text(
            f"❌ Error:\n`{e}`",
            parse_mode="Markdown"
        )

    finally:

        if upload_path and upload_path.exists():

            try:
                cleanup_file(upload_path)
            except Exception:
                pass


def _truncate(
    text: str,
    max_len: int = 60
) -> str:

    if len(text) <= max_len:
        return text

    return text[:max_len - 3] + "..."
