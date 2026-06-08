from utils.course_parser import parse_course
from utils.downloader import handle_course

async def handle_txt_file(update, context):

    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)

    path = f"uploads/{doc.file_name}"
    await file.download_to_drive(path)

    text = open(path, "r", encoding="utf-8", errors="ignore").read()

    parsed = parse_course(text)

    videos = parsed["videos"]
    pdfs = parsed["pdfs"]

    await update.message.reply_text(
        f"🎬 Videos: {len(videos)}\n📄 PDFs: {len(pdfs)}\n🚀 Processing..."
    )

    await handle_course(
        context.bot,
        update.effective_chat.id,
        videos + pdfs
    )
