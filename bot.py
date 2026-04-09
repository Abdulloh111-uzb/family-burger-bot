import json
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MenuButtonWebApp
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_ID, MINI_APP_URL, ADMIN_APP_URL, JSONBIN_ID, JSONBIN_KEY

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

async def start(update, ctx):
    kb = [[InlineKeyboardButton("🍔 Family Burger — Buyurtma berish", web_app=WebAppInfo(url=MINI_APP_URL))]]
    await update.message.reply_text(
        "🍔 *Family Burger*ga xush kelibsiz!\n\nMazali burgerlar, toza ingredients, tez yetkazib berish.\n\n👇 Tugmani bosib buyurtma bering!",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
    )
    await ctx.bot.set_chat_menu_button(
        chat_id=update.effective_chat.id,
        menu_button=MenuButtonWebApp(text="🍔 Menu", web_app=WebAppInfo(url=MINI_APP_URL))
    )

async def admin_cmd(update, ctx):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ Siz admin emassiz!")
        return
    kb = [[InlineKeyboardButton("👨‍💼 Admin Panel — Mahsulotlarni boshqarish", web_app=WebAppInfo(url=ADMIN_APP_URL))]]
    await update.message.reply_text(
        "👨‍💼 *Family Burger Admin*\n\nMahsulotlarni qo'shish, tahrirlash va o'chirish uchun tugmani bosing:",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
    )

async def handle_order(update, ctx):
    try:
        order = json.loads(update.message.web_app_data.data)
    except:
        return
    user = update.effective_user
    items = order.get("items", {})
    total = order.get("total", 0)
    items_text = "\n".join(f"  • {v.get('em','')} {v['name']} x{v['qty']} = {v['price']*v['qty']:,.0f} so'm" for v in items.values())
    await update.message.reply_text(
        f"✅ *Buyurtmangiz qabul qilindi!*\n\n👤 {order.get('name')}\n📞 {order.get('phone')}\n🏠 {order.get('address')}\n\n🛒 *Mahsulotlar:*\n{items_text}\n\n💰 *Jami: {total:,.0f} so'm*\n\nTez orada yetkazib beramiz! 🚀",
        parse_mode="Markdown"
    )
    try:
        await ctx.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 *YANGI BUYURTMA!*\n\n👤 {order.get('name')}\n📞 {order.get('phone')}\n🏠 {order.get('address')}\n💬 @{user.username or 'yoq'}\n\n🛒 *Mahsulotlar:*\n{items_text}\n\n💰 *Jami: {total:,.0f} so'm*",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Admin xabar xato: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_order))
    print("✅ Family Burger bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
