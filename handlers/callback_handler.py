"""
PRO Callback Handler (STABLE + RENDER SAFE VERSION)
Supports:
- Download All Videos
- URL Listing
- Pick Videos (pagination)
- Cancel session
- Queue integration safe
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

from utils.downloader import download_and_send_videos
from utils.url_parser import format_url_list

logger = logging.getLogger("bot.callbacks")

PAGE_SIZE = 8


# ─────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────
async def _callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data or ""
    user_id = update.effective_user.id

    # ───────────────────────── DOWNLOAD ALL ─────────────────────────
    if data.startswith("dl_all_"):

        uid = int(data.split("_")[-1])

        if uid != user_id:
            await query.answer("⛔ Not your session", show_alert=True)
            return

        videos = context.bot_data.get(f"videos_{uid}", [])

        if not videos:
            await query.edit_message_text("⚠️ Session expired or empty list.")
            return

        await query.edit_message_text(
            f"🚀 Starting download of {len(videos)} video(s)..."
        )

        asyncio.create_task(
            download_and_send_videos(
                bot=context.bot,
                chat_id=update.effective_chat.id,
                urls=videos,
                queue_manager=context.bot_data.get("queue_manager"),
            )
        )

    # ───────────────────────── LIST ALL URLS ─────────────────────────
    elif data.startswith("list_"):

        uid = int(data.split("_")[-1])

        videos = context.bot_data.get(f"videos_{uid}", [])
        pdfs = context.bot_data.get(f"pdfs_{uid}", [])
        images = context.bot_data.get(f"images_{uid}", [])

        urls = videos + pdfs + images

        if not urls:
            await query.edit_message_text("⚠️ Session expired.")
            return

        text = format_url_list(urls)

        chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]

        await query.edit_message_text(chunks[0])

        for chunk in chunks[1:]:
            await update.effective_chat.send_message(chunk)

    # ───────────────────────── PICK MODE ─────────────────────────
    elif data.startswith("pick_"):

        uid = int(data.split("_")[-1])

        videos = context.bot_data.get(f"videos_{uid}", [])

        context.bot_data[f"selected_{uid}"] = set()

        await _show_pick_page(query, context, uid, videos, 0, set())

    # ───────────────────────── PAGE NAVIGATION ─────────────────────────
    elif data.startswith("page_"):

        _, uid_str, page_str = data.split("_")

        uid = int(uid_str)
        page = int(page_str)

        videos = context.bot_data.get(f"videos_{uid}", [])
        selected = context.bot_data.get(f"selected_{uid}", set())

        await _show_pick_page(query, context, uid, videos, page, selected)

    # ───────────────────────── TOGGLE SELECTION ─────────────────────────
    elif data.startswith("toggle_"):

        _, uid_str, idx_str, page_str = data.split("_")

        uid = int(uid_str)
        idx = int(idx_str)
        page = int(page_str)

        selected = context.bot_data.get(f"selected_{uid}", set())

        if idx in selected:
            selected.remove(idx)
        else:
            selected.add(idx)

        context.bot_data[f"selected_{uid}"] = selected

        videos = context.bot_data.get(f"videos_{uid}", [])

        await _show_pick_page(query, context, uid, videos, page, selected)

    # ───────────────────────── CONFIRM SELECTION ─────────────────────────
    elif data.startswith("confirm_"):

        uid = int(data.split("_")[-1])

        videos = context.bot_data.get(f"videos_{uid}", [])
        selected = context.bot_data.get(f"selected_{uid}", set())

        chosen = [videos[i] for i in selected if i < len(videos)]

        if not chosen:
            await query.answer("Select at least one video!", show_alert=True)
            return

        await query.edit_message_text(
            f"🚀 Downloading {len(chosen)} selected video(s)..."
        )

        asyncio.create_task(
            download_and_send_videos(
                bot=context.bot,
                chat_id=update.effective_chat.id,
                urls=chosen,
                queue_manager=context.bot_data.get("queue_manager"),
            )
        )

    # ───────────────────────── CANCEL ─────────────────────────
    elif data.startswith("cancel_"):

        uid = int(data.split("_")[-1])

        context.bot_data.pop(f"videos_{uid}", None)
        context.bot_data.pop(f"pdfs_{uid}", None)
        context.bot_data.pop(f"images_{uid}", None)
        context.bot_data.pop(f"selected_{uid}", None)

        await query.edit_message_text("❌ Cancelled.")

    elif data == "noop":
        pass


# ─────────────────────────────────────────────
# PICK PAGE UI
# ─────────────────────────────────────────────
async def _show_pick_page(query, context, uid, urls, page, selected):

    total = len(urls)

    if total == 0:
        await query.edit_message_text("No videos found.")
        return

    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    page = max(0, min(page, pages - 1))

    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)

    rows = []

    for i in range(start, end):
        label = ("✅ " if i in selected else "") + f"{i+1}"
        rows.append([
            InlineKeyboardButton(
                label,
                callback_data=f"toggle_{uid}_{i}_{page}"
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"page_{uid}_{page-1}"))

    nav.append(InlineKeyboardButton(f"{page+1}/{pages}", callback_data="noop"))

    if page < pages - 1:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"page_{uid}_{page+1}"))

    rows.append(nav)

    rows.append([
        InlineKeyboardButton("🚀 Download Selected", callback_data=f"confirm_{uid}")
    ])

    await query.edit_message_text(
        f"Select videos ({len(selected)} selected):",
        reply_markup=InlineKeyboardMarkup(rows)
    )


# ─────────────────────────────────────────────
# EXPORT HANDLER
# ─────────────────────────────────────────────
handle_callback = CallbackQueryHandler(_callback_router)
