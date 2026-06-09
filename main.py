import logging
from telegram.ext import Application, MessageHandler, filters

from handlers.your_file import handle_txt_file  # change filename here

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# error handler
async def error_handler(update, context):
    logger.error("Exception occurred:", exc_info=context.error)


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # handler registration
    application.add_handler(
        MessageHandler(filters.Document.ALL, handle_txt_file)
    )

    # error handler
    application.add_error_handler(error_handler)

    # start bot
    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
