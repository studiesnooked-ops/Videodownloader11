"""
PRO Callback Handler
Supports:
- Download All Videos
- PDF Notes
- Thumbnails
- URL Listing
- Pick Videos
- Queue Integration
"""

import asyncio
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
)

from utils.downloader import (
    download_and_send_videos,
    download_and_send_pdfs,
    download_and_send_images,
)

from utils.url_parser import format_url_list

logger = logging.getLogger("bot.callbacks")

PAGE_SIZE = 8


async def _callback_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query
    await query.answer()

    data = query.data or ""
    user_id = update.effective_user.id

    # ----------------------------------------------------
    # DOWNLOAD ALL VIDEOS
    # ----------------------------------------------------

    if data.startswith("dl_all_"):

        uid = int(data.split("_")[-1])

        if uid != user_id:
            await query.answer(
                "⛔ Not your session",
                show_alert=True
            )
            return

        videos = context.bot_data.get(
            f"videos_{uid}",
            []
        )

        if not videos:
            await query.edit_message_text(
                "⚠️ Session expired."
            )
            return

        await query.edit_message_text(
            f"🚀 Downloading {len(videos)} video(s)..."
        )

        asyncio.create_task(
            download_and_send_videos(
                bot=context.bot,
                chat_id=update.effective_chat.id,
                urls=videos,
                queue_manager=context.bot_data.get(
                    "queue_manager"
                ),
            )
        )

    # ----------------------------------------------------
    # PDF NOTES
    # ----------------------------------------------------

    elif data.startswith("pdfs_"):

        uid = int(data.split("_")[-1])

        pdfs = context.bot_data.get(
            f"pdfs_{uid}",
            []
        )

        if not pdfs:
            await query.edit_message_text(
                "⚠️ No PDF notes found."
            )
            return

        await query.edit_message_text(
            f"📄 Downloading {len(pdfs)} PDF(s)..."
        )

        asyncio.create_task(
            download_and_send_pdfs(
                bot=context.bot,
                chat_id=update.effective_chat.id,
                urls=pdfs,
            )
        )

    # ----------------------------------------------------
    # THUMBNAILS
    # ----------------------------------------------------

    elif data.startswith("thumbs_"):

        uid = int(data.split("_")[-1])

        images = context.bot_data.get(
            f"images_{uid}",
            []
        )

        if not images:
            await query.edit_message_text(
                "⚠️ No thumbnails found."
            )
            return

        await query.edit_message_text(
            f"🖼 Downloading {len(images)} image(s)..."
        )

        asyncio.create_task(
            download_and_send_images(
                bot=context.bot,
                chat_id=update.effective_chat.id,
                urls=images,
            )
        )

    # ----------------------------------------------------
    # LIST URLS
    # ----------------------------------------------------

    elif data.startswith("list_"):

        uid = int(data.split("_")[-1])

        videos = context.bot_data.get(
            f"videos_{uid}",
            []
        )

        pdfs = context.bot_data.get(
            f"pdfs_{uid}",
            []
        )

        images = context.bot_data.get(
            f"images_{uid}",
            []
        )

        urls = videos + pdfs + images

        if not urls:
            await query.edit_message_text(
                "⚠️ Session expired."
            )
            return

        text = format_url_list(urls)

        chunks = [
            text[i:i + 4000]
            for i in range(0, len(text), 4000)
        ]

        await query.edit_message_text(
            chunks[0]
        )

        for chunk in chunks[1:]:
            await update.effective_chat.send_message(
                chunk
            )

    # ----------------------------------------------------
    # PICK VIDEOS
    # ----------------------------------------------------

    elif data.startswith("pick_"):

        uid = int(data.split("_")[-1])

        videos = context.bot_data.get(
            f"videos_{uid}",
            []
        )

        selected = set()

        context.bot_data[
            f"selected_{uid}"
        ] = selected

        await _show_pick_page(
            query,
            context,
            uid,
            videos,
            0,
            selected
        )

    # ----------------------------------------------------
    # PAGE
    # ----------------------------------------------------

    elif data.startswith("page_"):

        _, uid_str, page_str = data.split("_")

        uid = int(uid_str)
        page = int(page_str)

        videos = context.bot_data.get(
            f"videos_{uid}",
            []
        )

        selected = context.bot_data.get(
            f"selected_{uid}",
            set()
        )

        await _show_pick_page(
            query,
            context,
            uid,
            videos,
            page,
            selected
        )

    # ----------------------------------------------------
    # TOGGLE
    # ----------------------------------------------------

    elif data.startswith("toggle_"):

        _, uid_str, idx_str, page_str = data.split("_")

        uid = int(uid_str)
        idx = int(idx_str)
        page = int(page_str)

        selected = context.bot_data.get(
            f"selected_{uid}",
            set()
        )

        if idx in selected:
            selected.remove(idx)
        else:
            selected.add(idx)

        context.bot_data[
            f"selected_{uid}"
        ] = selected

        videos = context.bot_data.get(
            f"videos_{uid}",
            []
        )

        await _show_pick_page(
            query,
            context,
            uid,
            videos,
            page,
            selected
        )

    # ----------------------------------------------------
    # CONFIRM
    # ----------------------------------------------------

    elif data.startswith("confirm_"):

        uid = int(data.split("_")[-1])

        videos = context.bot_data.get(
            f"videos_{uid}",
            []
        )

        selected = context.bot_data.get(
            f"selected_{uid}",
            set()
        )

        chosen = [
            videos[i]
            for i in selected
            if i < len(videos)
        ]

        if not chosen:
            await query.answer(
                "Select videos first."
            )
            return

        await query.edit_message_text(
            f"🚀 Downloading {len(chosen)} selected video(s)..."
        )

        asyncio.create_task(
            download_and_send_videos(
                bot=context.bot,
                chat_id=update.effective_chat.id,
                urls=chosen,
                queue_manager=context.bot_data.get(
                    "queue_manager"
                ),
            )
        )

    # ----------------------------------------------------
    # CANCEL
    # ----------------------------------------------------

    elif data.startswith("cancel_"):

        uid = int(data.split("_")[-1])

        context.bot_data.pop(
            f"videos_{uid}",
            None
        )

        context.bot_data.pop(
            f"pdfs_{uid}",
            None
        )

        context.bot_data.pop(
            f"images_{uid}",
            None
        )

        context.bot_data.pop(
            f"selected_{uid}",
            None
        )

        await query.edit_message_text(
            "❌ Cancelled."
        )

    elif data == "noop":
        pass


async def _show_pick_page(
    query,
    context,
    uid,
    urls,
    page,
    selected
):

    total = len(urls)

    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)

    rows = []

    for i in range(start, end):

        checked = "✅ " if i in selected else ""

        rows.append([
            InlineKeyboardButton(
                f"{checked}{i+1}",
                callback_data=f"toggle_{uid}_{i}_{page}"
            )
        ])

    rows.append([
        InlineKeyboardButton(
            "⬅️",
            callback_data=f"page_{uid}_{max(page-1,0)}"
        ),
        InlineKeyboardButton(
            "➡️",
            callback_data=f"page_{uid}_{page+1}"
        ),
    ])

    rows.append([
        InlineKeyboardButton(
            "🚀 Download",
            callback_data=f"confirm_{uid}"
        )
    ])

    await query.edit_message_text(
        "Select videos:",
        reply_markup=InlineKeyboardMarkup(rows)
    )


handle_callback = CallbackQueryHandler(
    _callback_router
)
