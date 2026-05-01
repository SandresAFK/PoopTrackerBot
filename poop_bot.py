"""
💩 POOP TRACKER BOT для Telegram
"""

import logging
import asyncio
import aiosqlite
import os
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.helpers import escape_markdown
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

TEXT = {
    "ru": {
        "btn_poop": "💩  Я посрал!",
        "btn_leaderboard": "🏆 Таблица лидеров",
        "btn_reviews": "📖 Отзывы друзей",
        "btn_my_stats": "📊 Моя статистика",
        "btn_all_events": "📜 Все события",
        "btn_skip": "⏭  Пропустить",
        "btn_back": "◀️ Назад",
        "btn_prev": "⬅️ Ранее",
        "btn_next": "➡️ Позже",
        "start": (
            "👋 Привет, {name}!\n\n"
            "Добро пожаловать в 💩 *Poop Tracker* —\n"
            "самый честный дневник жизнедеятельности твоей компании!\n\n"
            "Нажми кнопку, когда природа позвала 👇"
        ),
        "ask_review": "📝 Расскажи как посрал:\n",
        "review_saved": "📝 *Отзыв сохранён!* Потомки оценят.\n\n",
        "what_next": "Что дальше?",
        "skip_review_done": "👌 Окей, без отзыва. Главное — факт зафиксирован!\n\nЧто дальше?",
        "leaderboard_empty": "🏆 *Таблица лидеров пуста*\n\nБудь первым — нажми 💩!",
        "leaderboard_title": "🏆 *ТАБЛИЦА ЛИДЕРОВ*\n_(кто больше — тот чемпион)_\n",
        "reviews_empty": "📖 *Отзывов пока нет*\n\nПокакай и оставь первый!",
        "reviews_title": "📖 *ОТЗЫВЫ ТВОИХ ДРУЗЕЙ*\n",
        "all_events_empty": "📜 *Событий пока нет*\n\nНажми 💩, чтобы добавить первое.",
        "all_events_title": "📜 *ВСЕ СОБЫТИЯ* ({start}-{end} из {total})\n",
        "my_stats_title": "📊 *Твоя статистика*",
        "my_stats_total": "💩 Всего раз: *{total}*",
        "my_stats_with_review": "📝 С отзывом: *{with_review}*",
        "my_stats_rank": "🏆 Место в рейтинге: *{rank}*",
        "my_events_title": "🕒 *Твои события* ({start}-{end} из {total}):",
        "menu_title": "💩 *Poop Tracker*\n\nЧто хочешь сделать?",
        "cancel": "Окей, отменено.",
    },
    "en": {
        "btn_poop": "💩  I pooped!",
        "btn_leaderboard": "🏆 Leaderboard",
        "btn_reviews": "📖 Friends' reviews",
        "btn_my_stats": "📊 My stats",
        "btn_all_events": "📜 All events",
        "btn_skip": "⏭  Skip",
        "btn_back": "◀️ Back",
        "btn_prev": "⬅️ Earlier",
        "btn_next": "➡️ Later",
        "start": (
            "👋 Hi, {name}!\n\n"
            "Welcome to 💩 *Poop Tracker* —\n"
            "the most honest activity log for your crew!\n\n"
            "Tap a button when nature calls 👇"
        ),
        "ask_review": "📝 Tell us how it went:\n",
        "review_saved": "📝 *Saved!* Future generations will appreciate it.\n\n",
        "what_next": "What next?",
        "skip_review_done": "👌 Ok, no review. The important part is logged!\n\nWhat next?",
        "leaderboard_empty": "🏆 *Leaderboard is empty*\n\nBe the first — tap 💩!",
        "leaderboard_title": "🏆 *LEADERBOARD*\n_(most poops wins)_\n",
        "reviews_empty": "📖 *No reviews yet*\n\nPoop and leave the first one!",
        "reviews_title": "📖 *YOUR FRIENDS' REVIEWS*\n",
        "all_events_empty": "📜 *No events yet*\n\nTap 💩 to add the first one.",
        "all_events_title": "📜 *ALL EVENTS* ({start}-{end} of {total})\n",
        "my_stats_title": "📊 *Your stats*",
        "my_stats_total": "💩 Total: *{total}*",
        "my_stats_with_review": "📝 With review: *{with_review}*",
        "my_stats_rank": "🏆 Rank: *{rank}*",
        "my_events_title": "🕒 *Your events* ({start}-{end} of {total}):",
        "menu_title": "💩 *Poop Tracker*\n\nWhat do you want to do?",
        "cancel": "Okay, cancelled.",
    },
}


def get_lang(update: Update | None) -> str:
    try:
        code = (update.effective_user.language_code or "").lower() if update and update.effective_user else ""
    except Exception:
        code = ""
    return "en" if code.startswith("en") else "ru"


def tr(update: Update | None, key: str, **kwargs) -> str:
    lang = get_lang(update)
    template = TEXT.get(lang, TEXT["ru"]).get(key) or TEXT["ru"].get(key) or key
    try:
        return template.format(**kwargs)
    except Exception:
        return str(template)


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

async def get_user_events(user_id: int, limit: int = 50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, timestamp, review
            FROM poops
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ) as cursor:
            return await cursor.fetchall()


async def get_user_events_page(user_id: int, limit: int, offset: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, timestamp, review
            FROM poops
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        ) as cursor:
            return await cursor.fetchall()


async def get_user_events_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM poops WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return int(row[0] if row else 0)


async def get_all_events_page(limit: int, offset: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, user_id, username, timestamp, review
            FROM poops
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ) as cursor:
            return await cursor.fetchall()

async def get_all_events_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM poops") as cursor:
            row = await cursor.fetchone()
            return int(row[0] if row else 0)


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
    return dt.strftime("%d.%m %H:%M:%S")


def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(TEXT["ru"]["btn_poop"], callback_data="poop")],
        [
            InlineKeyboardButton(TEXT["ru"]["btn_leaderboard"], callback_data="leaderboard"),
            InlineKeyboardButton(TEXT["ru"]["btn_reviews"],   callback_data="reviews"),
        ],
        [InlineKeyboardButton(TEXT["ru"]["btn_my_stats"], callback_data="my_stats:0")],
        [InlineKeyboardButton(TEXT["ru"]["btn_all_events"], callback_data="all_events:0")],
    ])


def main_keyboard_for(update: Update):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(tr(update, "btn_poop"), callback_data="poop")],
        [
            InlineKeyboardButton(tr(update, "btn_leaderboard"), callback_data="leaderboard"),
            InlineKeyboardButton(tr(update, "btn_reviews"), callback_data="reviews"),
        ],
        [InlineKeyboardButton(tr(update, "btn_my_stats"), callback_data="my_stats:0")],
        [InlineKeyboardButton(tr(update, "btn_all_events"), callback_data="all_events:0")],
    ])


# ─── ХЭНДЛЕРЫ ─────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "friend"
    await update.message.reply_text(
        tr(update, "start", name=name),
        parse_mode="Markdown",
        reply_markup=main_keyboard_for(update)
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Пагинация
    if query.data.startswith("all_events"):
        offset = 0
        if ":" in query.data:
            try:
                offset = max(0, int(query.data.split(":", 1)[1]))
            except ValueError:
                offset = 0
        return await show_all_events(update, context, offset=offset)

    if query.data.startswith("my_stats"):
        offset = 0
        if ":" in query.data:
            try:
                offset = max(0, int(query.data.split(":", 1)[1]))
            except ValueError:
                offset = 0
        return await show_my_stats(update, context, offset=offset)

    dispatch = {
        "poop":        handle_poop,
        "leaderboard": show_leaderboard,
        "reviews":     show_reviews,
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
        [InlineKeyboardButton(tr(update, "btn_skip"), callback_data="skip_review")]
    ])
    await query.edit_message_text(
        tr(update, "ask_review"),
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    return WAITING_REVIEW


async def receive_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    review = update.message.text.strip()
    poop_id = context.user_data.get("last_poop_id")

    if poop_id and review:
        await update_review(poop_id, review)
        msg = tr(update, "review_saved")
    else:
        msg = ""

    await update.message.reply_text(
        msg + tr(update, "what_next"),
        parse_mode="Markdown",
        reply_markup=main_keyboard_for(update)
    )
    return ConversationHandler.END


async def skip_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text(
        tr(update, "skip_review_done"),
        reply_markup=main_keyboard_for(update)
    )
    return ConversationHandler.END


async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    rows = await get_leaderboard()

    if not rows:
        text = tr(update, "leaderboard_empty")
    else:
        lines = [tr(update, "leaderboard_title")]
        for i, row in enumerate(rows):
            lines.append(f"{medal(i)} {row['username']} — *{row['cnt']}* раз")
        text = "\n".join(lines)

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(tr(update, "btn_back"), callback_data="back")]])
    )


async def show_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    rows = await get_reviews()

    if not rows:
        text = tr(update, "reviews_empty")
    else:
        lines = [tr(update, "reviews_title")]
        for row in rows:
            lines.append(f"*{row['username']}* [{format_time(row['timestamp'])}]")
            lines.append(f"_{row['review']}_\n")
        text = "\n".join(lines)

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(tr(update, "btn_back"), callback_data="back")]])
    )

async def show_all_events(update: Update, context: ContextTypes.DEFAULT_TYPE, offset: int = 0):
    query = update.callback_query
    limit = 25
    total = await get_all_events_count()
    if offset >= total and total > 0:
        offset = max(0, total - (total % limit or limit))
    rows = await get_all_events_page(limit=limit, offset=offset)

    if not rows:
        text = tr(update, "all_events_empty")
    else:
        start_n = offset + 1
        end_n = min(offset + limit, total)
        lines = [tr(update, "all_events_title", start=start_n, end=end_n, total=total)]
        for row in rows:
            username = escape_markdown(str(row["username"]), version=1)
            ts = format_time(row["timestamp"])
            review = (row["review"] or "").strip()
            if review:
                review = escape_markdown(review, version=1)
                lines.append(f"• {ts} — *{username}*: _{review}_")
            else:
                lines.append(f"• {ts} — *{username}*")
        text = "\n".join(lines)

    nav = []
    prev_offset = offset - limit
    next_offset = offset + limit
    if prev_offset >= 0:
        nav.append(InlineKeyboardButton(tr(update, "btn_prev"), callback_data=f"all_events:{prev_offset}"))
    if next_offset < total:
        nav.append(InlineKeyboardButton(tr(update, "btn_next"), callback_data=f"all_events:{next_offset}"))
    kb_rows = []
    if nav:
        kb_rows.append(nav)
    kb_rows.append([InlineKeyboardButton(tr(update, "btn_back"), callback_data="back")])

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb_rows),
    )


async def show_my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, offset: int = 0):
    query = update.callback_query
    user = query.from_user
    username = get_username(user)
    stats = await get_user_stats(user.id)
    total       = stats["total"]       if stats else 0
    with_review = stats["with_review"] if stats else 0

    board = await get_leaderboard()
    rank = next((i + 1 for i, r in enumerate(board) if r["username"] == username), "—")

    events_limit = 15
    user_total = await get_user_events_count(user.id)
    if offset >= user_total and user_total > 0:
        offset = max(0, user_total - (user_total % events_limit or events_limit))
    events = await get_user_events_page(user.id, limit=events_limit, offset=offset)
    event_lines = []
    for row in events:
        ts = format_time(row["timestamp"])
        review = (row["review"] or "").strip()
        if review:
            review = escape_markdown(review, version=1)
            event_lines.append(f"• {ts} — _{review}_")
        else:
            event_lines.append(f"• {ts}")
    events_block = "\n".join(event_lines) if event_lines else "—"
    start_n = offset + 1 if user_total else 0
    end_n = min(offset + events_limit, user_total) if user_total else 0

    nav = []
    prev_offset = offset - events_limit
    next_offset = offset + events_limit
    if prev_offset >= 0 and user_total:
        nav.append(InlineKeyboardButton("⬅️ Ранее", callback_data=f"my_stats:{prev_offset}"))
    if next_offset < user_total:
        nav.append(InlineKeyboardButton("➡️ Позже", callback_data=f"my_stats:{next_offset}"))
    kb_rows = []
    if nav:
        kb_rows.append(nav)
    kb_rows.append([InlineKeyboardButton("◀️ Назад", callback_data="back")])

    await query.edit_message_text(
        f"{tr(update, 'my_stats_title')}\n\n"
        f"👤 {username}\n"
        f"{tr(update, 'my_stats_total', total=total)}\n"
        f"{tr(update, 'my_stats_with_review', with_review=with_review)}\n"
        f"{tr(update, 'my_stats_rank', rank=rank)}\n\n"
        f"{tr(update, 'my_events_title', start=start_n, end=end_n, total=user_total)}\n{events_block}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb_rows)
    )


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text(
        tr(update, "menu_title"),
        parse_mode="Markdown",
        reply_markup=main_keyboard_for(update)
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(tr(update, "cancel"), reply_markup=main_keyboard_for(update))
    return ConversationHandler.END


# ─── ЗАПУСК ───────────────────────────────────────────────────
def main():
    if not BOT_TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN. Установи переменную окружения BOT_TOKEN и перезапусти бота.")

    # Инициализируем БД в отдельном (коротком) event loop,
    # чтобы не мешать loop'у, который создаст python-telegram-bot.
    asyncio.run(init_db())

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
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
