import asyncio
import logging
import os
import uuid
from functools import wraps

from akson_client import AksonClient
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegramify_markdown import markdownify

load_dotenv()

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_USER_ID = int(os.environ["TELEGRAM_USER_ID"])
AKSON_API_BASE_URL = os.environ.get("AKSON_API_BASE_URL", "http://localhost:8000")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

client = AksonClient(AKSON_API_BASE_URL)

# Global state
# TODO save state in telegram chat context
akson_chat_id = str(uuid.uuid4())
event_listener_task: asyncio.Task


def restricted(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != TELEGRAM_USER_ID:
            logger.warning(f"Unauthorized access denied for {user_id}.")
            return
        return await func(update, context, *args, **kwargs)

    return wrapped


async def listen_events(chat_id):
    logger.info("Listening for events...")
    async for event in client.stream_events(chat_id):
        logger.info(f"Event: {event}")


@restricted
async def handle_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message
    logger.info("handle_new")
    global akson_chat_id
    global event_listener_task
    akson_chat_id = str(uuid.uuid4())
    await update.message.reply_text(text=f"New chat created: {akson_chat_id}")
    event_listener_task.cancel()
    event_listener_task = context.application.create_task(listen_events(akson_chat_id))


@restricted
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.effective_chat
    assert update.message
    assert update.message.text
    logger.info("handle_message")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    # TODO set assistant
    replies = await client.send_message(akson_chat_id, update.message.text, "ChatGPT")
    for reply in replies:
        text = markdownify(reply["content"])
        await update.message.reply_markdown_v2(text=text)


async def post_init(app):
    global event_listener_task
    event_listener_task = app.create_task(listen_events(akson_chat_id))


application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
application.post_init = post_init
application.add_handler(CommandHandler("new", handle_new))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.run_polling()
