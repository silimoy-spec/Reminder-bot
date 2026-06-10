import os, json, time, threading
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))
DATA_FILE = "tasks.json"

def load(): 
    try: return json.load(open(DATA_FILE))
    except: return []

def save(tasks): json.dump(tasks, open(DATA_FILE,"w"), ensure_ascii=False)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 שלום! אני בוט התזכורות שלך.\n\n/add שם_משימה שעה (לדוגמה: /add לשלם ארנונה 18:00)\n/list לרשימת המשימות")

async def add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("❌ שימוש: /add שם_משימה שעה\nלדוגמה: /add לשלם ארנונה 18:00")
        return
    time_str = args[-1]
    name = " ".join(args[:-1])
    try:
        t = datetime.strptime(time_str, "%H:%M").replace(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
        if t < datetime.now(): t = t.replace(day=t.day+1)
    except:
        await update.message.reply_text("❌ פורמט שעה שגוי. השתמשי בHH:MM לדוגמה 18:00")
        return
    tasks = load()
    task = {"id": int(time.time()), "name": name, "due": t.isoformat(), "done": False, "interval": 5}
    tasks.append(task)
    save(tasks)
    await update.message.reply_text(f"✅ נוסף: {name} בשעה {time_str}\n🔔 אתזכר אותך כל 5 דקות עד שתאשרי ביצוע")

async def list_tasks(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tasks = [t for t in load() if not t["done"]]
    if not tasks:
        await update.message.reply_text("✨ אין משימות פעילות!")
        return
    for t in tasks:
        due = datetime.fromisoformat(t["due"]).strftime("%d/%m %H:%M")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ בוצע!", callback_data=f"done_{t['id']}")]])
        await update.message.reply_text(f"📌 {t['name']}\n🕐 {due}", reply_markup=kb)

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_id = int(query.data.split("_")[1])
    tasks = load()
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = True
    save(tasks)
    await query.edit_message_text(f"🎉 כל הכבוד! משימה הושלמה!")

async def reminder_loop(app):
    while True:
        await asyncio.sleep(60)
        tasks = [t for t in load() if not t["done"]]
        now = datetime.now()
        for t in tasks:
            due = datetime.fromisoformat(t["due"])
            last = t.get("last_notified")
            last_dt = datetime.fromisoformat(last) if last else None
            should = not last_dt or (now - last_dt).seconds >= t["interval"] * 60
            if now >= due and should:
                t["last_notified"] = now.isoformat()
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ בוצע!", callback_data=f"done_{t['id']}")]])
                await app.bot.send_message(chat_id=CHAT_ID, text=f"⏰ תזכורת: {t['name']}", reply_markup=kb)
        save(tasks)

import asyncio

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CallbackQueryHandler(button))
    asyncio.create_task(reminder_loop(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
