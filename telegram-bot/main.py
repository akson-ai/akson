import asyncio
import logging
import os
import uuid
from functools import wraps
from io import StringIO

from akson_client import AksonClient
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
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

akson = AksonClient(AKSON_API_BASE_URL)
listener: "Listener"


async def post_init(app: Application):
    global listener
    listener = Listener(app)


class Listener:

    def __init__(self, app: Application):
        self.app = app
        # TODO load state and set both akson_chat_id and telegram_chat_id
        self.akson_chat_id = str(uuid.uuid4()).replace("-", "")
        self.telegram_chat_id: int | None = None
        self._task: asyncio.Task | None = None
        self._start()

    async def set_akson_chat_id(self, akson_chat_id: str):
        if akson_chat_id != self.akson_chat_id:
            self.akson_chat_id = akson_chat_id
            self._start()

    async def set_telegram_chat_id(self, telegram_chat_id: int):
        self.telegram_chat_id = telegram_chat_id

    def _start(self):
        if self._task:
            self._task.cancel()
        self._task = self.app.create_task(self._listen_events(self.akson_chat_id))

    async def _listen_events(self, akson_chat_id: str):
        logger.info("Listening for events...")
        content = StringIO()
        async for event in akson.stream_events(akson_chat_id):
            logger.info(f"Event: {event}")
            match event["type"]:
                case "begin_message":
                    content.truncate(0)
                    if self.telegram_chat_id:
                        await self.app.bot.send_chat_action(chat_id=self.telegram_chat_id, action=ChatAction.TYPING)
                case "add_chunk":
                    if event["location"] == "content":
                        content.write(event["chunk"])
                case "end_message":
                    if self.telegram_chat_id:
                        text = markdownify(content.getvalue())
                        await self.app.bot.send_message(
                            chat_id=self.telegram_chat_id, text=text, parse_mode=ParseMode.MARKDOWN_V2
                        )
                    content.truncate(0)


def restricted(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != TELEGRAM_USER_ID:
            logger.warning(f"Unauthorized access denied for {user_id}.")
            return
        return await func(update, context, *args, **kwargs)

    return wrapped


@restricted
async def handle_new(update: Update, _: ContextTypes.DEFAULT_TYPE):
    assert update.message
    logger.info("handle_new")
    await listener.set_akson_chat_id(str(uuid.uuid4()).replace("-", ""))
    await update.message.reply_text(text=f"New chat created: {listener.akson_chat_id}")


@restricted
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.effective_chat
    assert update.message
    assert update.message.text
    logger.info("handle_message")
    await listener.set_telegram_chat_id(update.effective_chat.id)
    # TODO move typing under "add_chunk" event
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await akson.send_message(listener.akson_chat_id, update.message.text)


application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
application.post_init = post_init
application.add_handler(CommandHandler("new", handle_new))
application.add_handler(MessageHandler(filters.ALL, handle_message))
application.run_polling()
