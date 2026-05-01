"""
💩 POOP TRACKER BOT для Telegram
"""

import logging
import asyncio
import aiosqlite
import os
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ─── НАСТРОЙКИ ────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
_default_db_dir = "/data" if os.path.isdir("/data") else os.getcwd()
DB_PATH = os.getenv("DB_PATH", os.path.join(_default_db_dir, "poop.db"))

WAITING_REVIEW = 1

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ─── БАЗА ДАННЫХ ───────────────────────────────────────────────
async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS poops (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                username  TEXT    NOT NULL,
                timestamp TEXT    NOT NULL,
                review    TEXT
            )
        """)
        await db.commit()


async def add_poop(user_id: int, username: str) -> int:
    ts = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO poops (user_id, username, timestamp, review) VALUES (?, ?, ?, NULL)",
            (user_id, username, ts)
        )
        await db.commit()
        return cursor.lastrowid


async def update_review(poop_id: int, review: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE poops SET review = ? WHERE id = ?", (review, poop_id))
        await db.commit()


async def get_leaderboard():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT username, COUNT(*) as cnt
            FROM poops
            GROUP BY user_id
            ORDER BY cnt DESC
            LIMIT 10
        """) as cursor:
            return await cursor.fetchall()


async def get_reviews(limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT username, review, timestamp
            FROM poops
            WHERE review IS NOT NULL AND review != ''
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)) as cursor:
            return await cursor.fetchall()


async def get_user_stats(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN review IS NOT NULL AND review != '' THEN 1 ELSE 0 END) as with_review
            FROM poops WHERE user_id = ?
        """, (user_id,)) as cursor:
            return await cursor.fetchone()


# ─── ХЕЛПЕРЫ ──────────────────────────────────────────────────
def get_username(user) -> str:
    if user.username:
        return f"@{user.username}"
    return user.first_name or f"user_{user.id}"


def medal(pos: int) -> str:
    medals = ["🥇", "🥈", "🥉"]
    return medals[pos] if pos < 3 else f"{pos + 1}."


def format_time(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str).astimezone()
    return dt.strftime("%d.%m %H:%M")


def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💩  Я посрал!", callback_data="poop")],
        [
            InlineKeyboardButton("🏆 Таблица лидеров", callback_data="leaderboard"),
            InlineKeyboardButton("📖 Отзывы друзей",   callback_data="reviews"),
        ],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats")],
    ])


# ─── ХЭНДЛЕРЫ ─────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "друг"
    await update.message.reply_text(
        f"👋 Привет, {name}!\n\n"
        "Добро пожаловать в 💩 *Poop Tracker* —\n"
        "самый честный дневник жизнедеятельности твоей компании!\n\n"
        "Нажми кнопку, когда природа позвала 👇",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    dispatch = {
        "poop":        handle_poop,
        "leaderboard": show_leaderboard,
        "reviews":     show_reviews,
        "my_stats":    show_my_stats,
        "skip_review": skip_review,
        "back":        back_to_menu,
    }
    handler = dispatch.get(query.data)
    if handler:
        return await handler(update, context)


async def handle_poop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    username = get_username(user)

    poop_id = await add_poop(user.id, username)
    context.user_data["last_poop_id"] = poop_id

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭  Пропустить", callback_data="skip_review")]
    ])
    await query.edit_message_text(
        "📝 Расскажи как посрал:\n",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    return WAITING_REVIEW


async def receive_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    review = update.message.text.strip()
    poop_id = context.user_data.get("last_poop_id")

    if poop_id and review:
        await update_review(poop_id, review)
        msg = "📝 *Отзыв сохранён!* Потомки оценят.\n\n"
    else:
        msg = ""

    await update.message.reply_text(
        msg + "Что дальше?",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )
    return ConversationHandler.END


async def skip_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text(
        "👌 Окей, без отзыва. Главное — факт зафиксирован!\n\nЧто дальше?",
        reply_markup=main_keyboard()
    )
    return ConversationHandler.END


async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    rows = await get_leaderboard()

    if not rows:
        text = "🏆 *Таблица лидеров пуста*\n\nБудь первым — нажми 💩!"
    else:
        lines = ["🏆 *ТАБЛИЦА ЛИДЕРОВ*\n_(кто больше — тот чемпион)_\n"]
        for i, row in enumerate(rows):
            lines.append(f"{medal(i)} {row['username']} — *{row['cnt']}* раз")
        text = "\n".join(lines)

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back")]])
    )


async def show_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    rows = await get_reviews()

    if not rows:
        text = "📖 *Отзывов пока нет*\n\nПокакай и оставь первый!"
    else:
        lines = ["📖 *ОТЗЫВЫ ТВОИХ ДРУЗЕЙ*\n"]
        for row in rows:
            lines.append(f"*{row['username']}* [{format_time(row['timestamp'])}]")
            lines.append(f"_{row['review']}_\n")
        text = "\n".join(lines)

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back")]])
    )


async def show_my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    username = get_username(user)
    stats = await get_user_stats(user.id)
    total       = stats["total"]       if stats else 0
    with_review = stats["with_review"] if stats else 0

    board = await get_leaderboard()
    rank = next((i + 1 for i, r in enumerate(board) if r["username"] == username), "—")

    await query.edit_message_text(
        f"📊 *Твоя статистика*\n\n"
        f"👤 {username}\n"
        f"💩 Всего раз: *{total}*\n"
        f"📝 С отзывом: *{with_review}*\n"
        f"🏆 Место в рейтинге: *{rank}*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back")]])
    )


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text(
        "💩 *Poop Tracker*\n\nЧто хочешь сделать?",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Окей, отменено.", reply_markup=main_keyboard())
    return ConversationHandler.END


# ─── ЗАПУСК ───────────────────────────────────────────────────
async def main():
    if not BOT_TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN. Установи переменную окружения BOT_TOKEN и перезапусти бота.")
    await init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            WAITING_REVIEW: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_review),
                CallbackQueryHandler(button_handler),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)

    print("🚀 Бот запущен! Ctrl+C для остановки.")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        import nest_asyncio  # type: ignore
        nest_asyncio.apply()
    except Exception:
        pass
    asyncio.run(main())
