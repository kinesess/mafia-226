"""
MAFIA ROLE BOT
──────────────
Группа: /newgame — создать игру, кнопка «Присоединиться» для всех
Личка:  бот автоматически выдаёт роль при переходе из группы
"""

import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ══════════════════════════════════════════════════════════════════════════════
#  НАСТРОЙКИ
# ══════════════════════════════════════════════════════════════════════════════

BOT_TOKEN    = "8677717733:AAHzvcEG1VZHE6Hwpzg_eO6keeUpOhl3Vtg"
BOT_USERNAME = "mafia_226group_bot"   # без @, например: mymafia_bot

# Лимиты ролей
ROLE_LIMITS = {
    "💣 Террорист":     6,
    "🏥 Медик":         3,
    "🔧 Специалист":    2,
    "👤 Мирный житель": None,   # None = без лимита
}

ROLE_DESC = {
    "💣 Террорист":     "Ваша цель — устранить мирных жителей. Действуйте скрытно и не раскрывайте себя.",
    "🏥 Медик":         "Каждую ночь вы можете защитить одного игрока от устранения. Выбирайте мудро.",
    "🔧 Специалист":    "У вас есть особые навыки. Используйте их в нужный момент, чтобы изменить ход игры.",
    "👤 Мирный житель": "Найдите и разоблачите террористов путём голосования. Доверяйте своей интуиции.",
}

ROLE_COLOR = {
    "💣 Террорист":     "🔴",
    "🏥 Медик":         "🟢",
    "🔧 Специалист":    "🔵",
    "👤 Мирный житель": "⚪",
}

# ══════════════════════════════════════════════════════════════════════════════
#  ХРАНИЛИЩЕ (в памяти)
#
#  games[group_chat_id] = {
#      "players":       { user_id: role_str },
#      "joined":        { user_id: first_name },
#      "role_counts":   { role_str: int },
#      "active":        bool,
#      "group_msg_id":  int,
#      "group_chat_id": int,
#  }
# ══════════════════════════════════════════════════════════════════════════════

games: dict[int, dict] = {}

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════════════════════════

def new_game(group_chat_id: int) -> dict:
    return {
        "players":       {},
        "joined":        {},
        "role_counts":   {r: 0 for r in ROLE_LIMITS},
        "active":        True,
        "group_msg_id":  None,
        "group_chat_id": group_chat_id,
    }


def assign_role(game: dict) -> str:
    """Случайно выбирает роль с учётом лимитов."""
    available, weights = [], []
    for role, limit in ROLE_LIMITS.items():
        if limit is None:
            available.append(role)
            weights.append(8)
        elif game["role_counts"][role] < limit:
            available.append(role)
            weights.append(limit - game["role_counts"][role])
    if not available:
        return "👤 Мирный житель"
    chosen = random.choices(available, weights=weights, k=1)[0]
    game["role_counts"][chosen] += 1
    return chosen


def group_message_text(game: dict) -> str:
    """Текст сообщения в группе с актуальным списком участников."""
    names = list(game["joined"].values())
    count = len(names)

    if names:
        players_list = "\n".join(f"  • {n}" for n in names[:25])
        if len(names) > 25:
            players_list += f"\n  ...и ещё {len(names)-25}"
    else:
        players_list = "  _пока никого нет_"

    return (
        "🎯 *ИГРА НАЧАЛАСЬ — ПРИСОЕДИНЯЙТЕСЬ!*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Нажмите кнопку ниже, бот выдаст вам\n"
        "роль в личном сообщении.\n\n"
        f"👥 *Участники ({count}):*\n"
        f"{players_list}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💣 Террористы — 6 мест\n"
        "🏥 Медики — 3 места\n"
        "🔧 Специалисты — 2 места\n"
        "👤 Мирные жители — ∞"
    )


def group_keyboard(gid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🎲 Присоединиться к игре",
            url=f"https://t.me/{BOT_USERNAME}?start=join_{gid}"
        )],
        [
            InlineKeyboardButton("📊 Статус", callback_data=f"gstats_{gid}"),
            InlineKeyboardButton("🔚 Завершить", callback_data=f"endgame_{gid}"),
        ],
    ])


# ══════════════════════════════════════════════════════════════════════════════
#  ХЭНДЛЕРЫ — ГРУППА
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_newgame(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/newgame в группе."""
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("⚠️ Команда работает только в группах.")
        return

    gid = chat.id
    if gid in games and games[gid]["active"]:
        await update.message.reply_text(
            "⚠️ Игра уже идёт! Завершите её кнопкой «Завершить» или командой /endgame."
        )
        return

    games[gid] = new_game(gid)
    game = games[gid]

    msg = await update.message.reply_text(
        group_message_text(game),
        reply_markup=group_keyboard(gid),
        parse_mode="Markdown",
    )
    game["group_msg_id"] = msg.message_id
    logger.info(f"Новая игра создана в группе {gid}")


async def cmd_endgame(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/endgame в группе."""
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return
    gid = chat.id
    if gid not in games:
        await update.message.reply_text("⚠️ Нет активной игры.")
        return
    games.pop(gid)
    await update.message.reply_text("🔚 Игра завершена. Новая игра: /newgame")


# ══════════════════════════════════════════════════════════════════════════════
#  ХЭНДЛЕРЫ — ЛИЧКА
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — либо приветствие, либо join_<gid> из группы."""
    user = update.effective_user
    args = context.args

    # ── Переход из группы ───────────────────────────────────────────────────
    if args and args[0].startswith("join_"):
        try:
            gid = int(args[0].split("_", 1)[1])
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Неверная ссылка.")
            return

        if gid not in games or not games[gid]["active"]:
            await update.message.reply_text(
                "⚠️ Эта игра уже завершена или не существует.\n"
                "Попросите организатора создать новую игру: /newgame"
            )
            return

        game = games[gid]
        name = user.first_name or "Игрок"

        # Уже получил роль?
        if user.id in game["players"]:
            role  = game["players"][user.id]
            color = ROLE_COLOR[role]
            await update.message.reply_text(
                f"ℹ️ Вы уже участвуете в этой игре!\n\n"
                f"{color} Ваша роль: *{role}*\n\n"
                f"_{ROLE_DESC[role]}_",
                parse_mode="Markdown",
            )
            return

        # Добавляем и выдаём роль
        game["joined"][user.id] = name
        role  = assign_role(game)
        game["players"][user.id] = role
        color = ROLE_COLOR[role]

        await update.message.reply_text(
            f"🎴 *РОЛЬ НАЗНАЧЕНА!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Игрок: *{name}*\n\n"
            f"{color}  *{role}*\n\n"
            f"_{ROLE_DESC[role]}_\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🤫 *Никому не говорите свою роль!*",
            parse_mode="Markdown",
        )
        logger.info(f"Игрок {user.id} ({name}) → роль «{role}» в игре {gid}")

        # Обновляем сообщение в группе
        if game["group_msg_id"]:
            try:
                await context.bot.edit_message_text(
                    chat_id=gid,
                    message_id=game["group_msg_id"],
                    text=group_message_text(game),
                    reply_markup=group_keyboard(gid),
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.warning(f"Не удалось обновить сообщение группы: {e}")
        return

    # ── Обычный старт ───────────────────────────────────────────────────────
    await update.message.reply_text(
        "👋 *Привет!* Я бот для распределения ролей.\n\n"
        "📌 *Как использовать:*\n"
        "1. Добавьте меня в группу\n"
        "2. Напишите `/newgame` в группе\n"
        "3. Участники нажимают *«Присоединиться»*\n"
        "4. Каждый получает роль здесь, в личке\n\n"
        "🎭 *Роли в игре:*\n"
        "💣 Террорист — 6 мест\n"
        "🏥 Медик — 3 места\n"
        "🔧 Специалист — 2 места\n"
        "👤 Мирный житель — без ограничений",
        parse_mode="Markdown",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ХЭНДЛЕРЫ — CALLBACK КНОПКИ
# ══════════════════════════════════════════════════════════════════════════════

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data  = query.data

    # ── Статус ──────────────────────────────────────────────────────────────
    if data.startswith("gstats_"):
        gid = int(data.split("_", 1)[1])
        if gid not in games:
            await query.answer("⚠️ Игра не найдена.", show_alert=True)
            return
        game  = games[gid]
        total = len(game["players"])
        lines = [f"📊 СТАТУС ИГРЫ\n{'─'*22}\nПолучили роль: {total}\n"]
        for role, limit in ROLE_LIMITS.items():
            count   = game["role_counts"][role]
            lim_str = str(limit) if limit else "∞"
            filled  = "█" * count
            empty   = "░" * (limit - count) if limit else ""
            lines.append(f"{ROLE_COLOR[role]} {role}: {count}/{lim_str} [{filled}{empty}]")
        await query.answer("\n".join(lines), show_alert=True)

    # ── Завершить игру ───────────────────────────────────────────────────────
    elif data.startswith("endgame_"):
        gid = int(data.split("_", 1)[1])
        if gid not in games:
            await query.answer("⚠️ Игра не найдена.", show_alert=True)
            return
        game = games.pop(gid)
        total = len(game["players"])
        summary = "\n".join(
            f"{ROLE_COLOR[r]} {r}: {game['role_counts'][r]}" for r in ROLE_LIMITS
        )
        await query.edit_message_text(
            f"🏁 *ИГРА ЗАВЕРШЕНА*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Всего участников: *{total}*\n\n"
            f"{summary}\n\n"
            f"_Для новой игры: /newgame_",
            parse_mode="Markdown",
        )


# ══════════════════════════════════════════════════════════════════════════════
#  ЗАПУСК
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("newgame", cmd_newgame))
    app.add_handler(CommandHandler("endgame", cmd_endgame))
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("✅ Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()