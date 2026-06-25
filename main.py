import logging
import asyncio
import json
import os

import nest_asyncio
nest_asyncio.apply()

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
)
from telegram.ext import (
    Application, CommandHandler, ContextTypes, CallbackQueryHandler
)
from telegram.error import TelegramError

# ── CẤU HÌNH ──────────────────────────────────────────────
BOT_TOKEN    = "BOT_TOKEN_HERE"
MINI_APP_URL = "https://YOUR_HOSTED_URL_HERE"   # ← Thay bằng URL host HTML
ADMIN_ID     = 8766063561

REQUIRED_CHATS = [
    {"username": "@LQGIFTCHAT",     "label": "LQGift Chat",      "url": "https://t.me/LQGIFTCHAT"},
    {"username": "@LQGIFTTHONGBAO", "label": "LQGift Thông Báo", "url": "https://t.me/LQGIFTTHONGBAO"},
]

USERS_FILE = "bot_users.json"
# ──────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ── USER STORAGE ──────────────────────────────────────────
def load_users() -> dict:
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_users(data: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def register_user(user):
    data = load_users()
    uid  = str(user.id)
    data[uid] = {
        "id":         user.id,
        "first_name": user.first_name or "",
        "last_name":  user.last_name  or "",
        "username":   user.username   or "",
    }
    save_users(data)


# ── CHECK JOIN ────────────────────────────────────────────
async def check_joined(bot, user_id: int) -> list:
    not_joined = []
    for chat in REQUIRED_CHATS:
        try:
            member = await bot.get_chat_member(chat["username"], user_id)
            if member.status in ("left", "kicked", "banned"):
                not_joined.append(chat)
        except TelegramError:
            not_joined.append(chat)
    return not_joined

def join_keyboard(not_joined: list):
    buttons = [
        [InlineKeyboardButton(f"➕ Tham gia {c['label']}", url=c["url"])]
        for c in not_joined
    ]
    buttons.append([
        InlineKeyboardButton("✅ Tôi đã tham gia — Kiểm tra lại", callback_data="check_join")
    ])
    return InlineKeyboardMarkup(buttons)

def open_app_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🎮  Mở LQGift", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])


# ── HANDLERS ──────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "bạn"
    register_user(user)

    not_joined = await check_joined(ctx.bot, user.id)
    if not_joined:
        text = (
            f"👋 Chào <b>{name}</b>!\n\n"
            f"⚠️ Để sử dụng <b>LQGift</b>, bạn cần tham gia <b>{len(not_joined)}</b> kênh sau:\n\n"
            + "\n".join(f"  • {c['label']}" for c in not_joined) +
            "\n\n📌 Tham gia xong nhấn nút <b>Kiểm tra lại</b> bên dưới nhé!"
        )
        await update.message.reply_html(text, reply_markup=join_keyboard(not_joined))
    else:
        await send_welcome(update.message, name)


async def send_welcome(message, name: str):
    text = (
        f"⚔️ Chào mừng <b>{name}</b> đến với <b>LQGift</b>!\n\n"
        f"🎁 Nơi phát <b>acc Liên Quân miễn phí</b> dành cho cộng đồng.\n\n"
        f"📌 <b>Cách nhận acc:</b>\n"
        f"  • Liên hệ <a href='https://t.me/Moew_Lover'>@Moew_Lover</a> để được cấp lượt\n"
        f"  • Mở Mini App và nhấn <b>Nhận Acc Ngay</b>\n"
        f"  • Đăng nhập Liên Quân và tận hưởng! 🎮\n\n"
        f"👇 Nhấn nút bên dưới để mở app:"
    )
    await message.reply_html(text, reply_markup=open_app_keyboard())


async def on_check_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Đang kiểm tra...")

    user = query.from_user
    name = user.first_name or "bạn"
    not_joined = await check_joined(ctx.bot, user.id)

    if not_joined:
        text = (
            f"❌ Bạn vẫn chưa tham gia đủ kênh!\n\n"
            f"Còn <b>{len(not_joined)}</b> kênh chưa join:\n"
            + "\n".join(f"  • {c['label']}" for c in not_joined) +
            "\n\nTham gia xong nhấn <b>Kiểm tra lại</b> nhé!"
        )
        await query.edit_message_text(
            text, parse_mode="HTML", reply_markup=join_keyboard(not_joined)
        )
    else:
        await query.delete_message()
        await send_welcome(query.message, name)


async def broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Bạn không có quyền dùng lệnh này.")
        return

    text = " ".join(ctx.args)
    if not text:
        await update.message.reply_html(
            "📢 <b>Cách dùng:</b>\n"
            "<code>/broadcast Nội dung thông báo</code>\n\n"
            "Hỗ trợ HTML: <b>bold</b>, <i>italic</i>, <code>code</code>"
        )
        return

    data  = load_users()
    total = len(data)
    ok = fail = 0

    status_msg = await update.message.reply_text(
        f"📤 Đang gửi tới {total} người dùng..."
    )

    broadcast_text = (
        f"📢 <b>Thông báo từ LQGift</b>\n"
        f"{'─' * 28}\n\n{text}"
    )

    for uid in data:
        try:
            await ctx.bot.send_message(
                chat_id=int(uid),
                text=broadcast_text,
                parse_mode="HTML",
                reply_markup=open_app_keyboard()
            )
            ok += 1
            await asyncio.sleep(0.05)
        except TelegramError as e:
            logger.warning(f"Không gửi được cho {uid}: {e}")
            fail += 1

    await status_msg.edit_text(
        f"✅ <b>Gửi xong!</b>\n\n"
        f"👥 Tổng: {total}\n"
        f"✔️ Thành công: {ok}\n"
        f"❌ Thất bại: {fail}",
        parse_mode="HTML"
    )


async def stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    data = load_users()
    await update.message.reply_html(
        f"📊 <b>Thống kê Bot</b>\n\n"
        f"👥 Tổng user đã dùng bot: <b>{len(data)}</b>"
    )


# ── MAIN ──────────────────────────────────────────────────
async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",     start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats",     stats))
    app.add_handler(CallbackQueryHandler(on_check_join, pattern="^check_join$"))
    logger.info("✅ Bot đang chạy...")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    asyncio.run(main())
