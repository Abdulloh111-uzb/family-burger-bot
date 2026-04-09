import json
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MenuButtonWebApp
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_ID, MINI_APP_URL, JSONBIN_ID, JSONBIN_KEY

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

ADD_NAME, ADD_PRICE, ADD_CAT, ADD_DESC, ADD_IMG, EDIT_CHOOSE, EDIT_FIELD, EDIT_VALUE = range(8)

JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"
HEADERS = {"X-Master-Key": JSONBIN_KEY, "Content-Type": "application/json"}

async def get_products():
    async with httpx.AsyncClient() as client:
        r = await client.get(JSONBIN_URL, headers={"X-Master-Key": JSONBIN_KEY})
        return r.json().get("record", {}).get("products", [])

async def save_products(products):
    async with httpx.AsyncClient() as client:
        await client.put(JSONBIN_URL, headers=HEADERS, json={"products": products})

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

async def handle_order(update, ctx):
    try:
        order = json.loads(update.message.web_app_data.data)
    except:
        return
    user = update.effective_user
    items = order.get("items", {})
    total = order.get("total", 0)
    items_text = "\n".join(f"  • {v['em']} {v['name']} x{v['qty']} = {v['price']*v['qty']:,.0f} so'm" for v in items.values())
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

async def admin_cmd(update, ctx):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz!")
        return
    kb = [
        [InlineKeyboardButton("➕ Mahsulot qo'shish", callback_data="adm_add")],
        [InlineKeyboardButton("📋 Mahsulotlar ro'yxati", callback_data="adm_list")],
    ]
    await update.message.reply_text("👨‍💼 *Family Burger — Admin Panel*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def adm_cb(update, ctx):
    q = update.callback_query
    await q.answer()
    if q.from_user.id != ADMIN_ID:
        return

    if q.data == "adm_add":
        await q.edit_message_text("📝 Mahsulot nomini kiriting:\n\n/cancel — bekor qilish")
        return ADD_NAME

    elif q.data == "adm_list":
        products = await get_products()
        if not products:
            await q.edit_message_text("Hozircha mahsulotlar yo'q.")
            return
        txt = "📋 *Mahsulotlar:*\n\n"
        kb = []
        for p in products:
            txt += f"{p.get('em','🍽')} *{p['name']}* — {p['price']:,.0f} so'm ({p['cat']})\n"
            kb.append([
                InlineKeyboardButton(f"✏️ {p['name']}", callback_data=f"edit_{p['id']}"),
                InlineKeyboardButton("🗑", callback_data=f"del_{p['id']}")
            ])
        kb.append([InlineKeyboardButton("➕ Yangi qo'shish", callback_data="adm_add")])
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("del_"):
        pid = int(q.data.replace("del_", ""))
        products = await get_products()
        products = [p for p in products if p["id"] != pid]
        await save_products(products)
        await q.edit_message_text("✅ Mahsulot o'chirildi!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 Ro'yxat", callback_data="adm_list")]]))

    elif q.data.startswith("edit_"):
        pid = int(q.data.replace("edit_", ""))
        ctx.user_data["edit_id"] = pid
        kb = [
            [InlineKeyboardButton("📝 Nom", callback_data="ef_name"), InlineKeyboardButton("💰 Narx", callback_data="ef_price")],
            [InlineKeyboardButton("📂 Kategoriya", callback_data="ef_cat"), InlineKeyboardButton("🖼 Rasm", callback_data="ef_img")],
        ]
        await q.edit_message_text("Nimani o'zgartirmoqchisiz?", reply_markup=InlineKeyboardMarkup(kb))
        return EDIT_FIELD

    elif q.data.startswith("ef_"):
        field = q.data.replace("ef_", "")
        ctx.user_data["edit_field"] = field
        hints = {"name": "Yangi nomni kiriting:", "price": "Yangi narxni kiriting (so'mda):", "cat": "Yangi kategoriyani kiriting:\nBurgerlar / Ichimliklar / Shirinliklar", "img": "Rasm URL ni kiriting (https://...):"}
        await q.edit_message_text(hints.get(field, "Yangi qiymatni kiriting:"))
        return EDIT_VALUE

async def add_name(update, ctx):
    ctx.user_data["pname"] = update.message.text
    await update.message.reply_text("💰 Narxini kiriting (faqat raqam, so'mda):")
    return ADD_PRICE

async def add_price(update, ctx):
    try:
        ctx.user_data["pprice"] = float(update.message.text.replace(" ", "").replace(",", ""))
        kb = [[InlineKeyboardButton(c, callback_data=f"cat_{c}")] for c in ["Burgerlar", "Ichimliklar", "Shirinliklar"]]
        await update.message.reply_text("📂 Kategoriyani tanlang:", reply_markup=InlineKeyboardMarkup(kb))
        return ADD_CAT
    except:
        await update.message.reply_text("Xato! Faqat raqam kiriting:")
        return ADD_PRICE

async def add_cat_cb(update, ctx):
    q = update.callback_query
    await q.answer()
    cat = q.data.replace("cat_", "")
    ctx.user_data["pcat"] = cat
    await q.edit_message_text("📝 Qisqa tavsif kiriting:")
    return ADD_DESC

async def add_desc(update, ctx):
    ctx.user_data["pdesc"] = update.message.text
    await update.message.reply_text("🖼 Rasm URL ni kiriting (https://...)\n\nRasm yo'q bo'lsa /skip yozing:")
    return ADD_IMG

async def add_img(update, ctx):
    cats_em = {"Burgerlar": "🍔", "Ichimliklar": "🥤", "Shirinliklar": "🍰"}
    cat = ctx.user_data["pcat"]
    img_url = None
    if update.message.text and update.message.text.lower() != "/skip":
        img_url = update.message.text.strip()
    products = await get_products()
    new_id = max([p["id"] for p in products], default=0) + 1
    new_p = {
        "id": new_id,
        "name": ctx.user_data["pname"],
        "price": ctx.user_data["pprice"],
        "cat": cat,
        "em": cats_em.get(cat, "🍽️"),
        "desc": ctx.user_data["pdesc"],
        "img": img_url
    }
    products.append(new_p)
    await save_products(products)
    await update.message.reply_text(
        f"✅ *{new_p['name']}* muvaffaqiyatli qo'shildi!\n💰 {new_p['price']:,.0f} so'm | {new_p['cat']}",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def edit_value(update, ctx):
    val = update.message.text.strip()
    pid = ctx.user_data.get("edit_id")
    field = ctx.user_data.get("edit_field")
    products = await get_products()
    for p in products:
        if p["id"] == pid:
            if field == "price":
                try: p["price"] = float(val.replace(" ", "").replace(",", ""))
                except: await update.message.reply_text("Xato narx!"); return EDIT_VALUE
            elif field == "img":
                p["img"] = val if val.lower() != "/skip" else None
            else:
                p[field] = val
            break
    await save_products(products)
    await update.message.reply_text("✅ Muvaffaqiyatli yangilandi!")
    return ConversationHandler.END

async def cancel(update, ctx):
    await update.message.reply_text("Bekor qilindi.")
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_cb, pattern="^adm_add$")],
        states={
            ADD_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_price)],
            ADD_CAT:   [CallbackQueryHandler(add_cat_cb, pattern="^cat_")],
            ADD_DESC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_desc)],
            ADD_IMG:   [MessageHandler(filters.TEXT & ~filters.COMMAND, add_img)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_cb, pattern="^edit_")],
        states={
            EDIT_FIELD: [CallbackQueryHandler(adm_cb, pattern="^ef_")],
            EDIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(add_conv)
    app.add_handler(edit_conv)
    app.add_handler(CallbackQueryHandler(adm_cb))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_order))

    print("✅ Family Burger bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
