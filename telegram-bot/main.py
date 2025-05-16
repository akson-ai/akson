import asyncio
import logging
import os
import uuid
from typing import cast

from akson_client import AksonClient
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
AKSON_API_BASE_URL = os.environ.get("AKSON_API_BASE_URL", "http://localhost:8000")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

client = AksonClient(AKSON_API_BASE_URL)

# Global state
akson_chat_id = str(uuid.uuid4())
telegram_chat_id = None


async def listen_events():
    logger.info("Listening for events...")
    async for event in client.stream_events(akson_chat_id):
        logger.info(f"Event: {event}")
        if telegram_chat_id:
            await application.bot.send_message(chat_id=telegram_chat_id, text=str(event))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.effective_chat
    assert update.message
    assert update.message.text

    global akson_chat_id
    global telegram_chat_id

    telegram_chat_id = update.effective_chat.id

    # application.job_queue.run_once(listen_events, 0)
    # loop = asyncio.get_running_loop()

    logger.info("Sending message...")
    await client.send_message(akson_chat_id, update.message.text, "ChatGPT")
    logger.info("Message sent")

    # await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# start_handler = CommandHandler("start", start)
# application.add_handler(start_handler)

# echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
# application.add_handler(echo_handler)

message_handler = MessageHandler(filters.ALL, handle_message)
application.add_handler(message_handler)


async def post_init(app):
    app.create_task(listen_events())


application.post_init = post_init
# application.create_task(listen_events())

application.run_polling()
