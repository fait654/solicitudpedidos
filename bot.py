import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, filters
from telegram.ext import CommandHandler, ConversationHandler, ContextTypes
from playwright.sync_api import sync_playwright
import pandas as pd

# ---------- CONFIG ----------

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
app = Flask(__name__)

PEDIR_FECHA = 1

# ---------- FUNCION BUSCAR PEDIDOS ----------

def buscar_pedidos(fecha):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            print("Abriendo login...")
            page.goto("https://myeforce.ecom.com.co/ecomltda/")

            page.fill('input[name="cta"]', "ebrandy@esparta")
            page.fill('input[name="ingr"]', "Pedidosesparta2026.")
            page.click('button[type="submit"]')
            page.wait_for_timeout(5000)

            print("Login correcto")
            page.goto("https://myeforce.ecom.com.co/eforce/modulos/pedidosNew/index.php")
            page.wait_for_timeout(4000)

            page.fill('input[name="fecha_ini"]', fecha)
            page.fill('input[name="fecha_fin"]', fecha)
            page.fill('input[name="cantidad"]', "99999")
            page.click('button:has-text("Buscar")')
            page.wait_for_timeout(6000)

            html = page.content()
            browser.close()

        tablas = pd.read_html(html)
        if len(tablas) == 0:
            return None

        df = tablas[0]
        archivo = f"pedidos_{fecha}.xlsx"
        df.to_excel(archivo, index=False)
        return archivo

    except Exception as e:
        print("ERROR:", e)
        return None

# ---------- HANDLERS ----------

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hola 👋, envíame cualquier fecha para obtener los pedidos.\nEjemplo: 2026-03-05"
    )
    return PEDIR_FECHA

async def recibir_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fecha = update.message.text.strip()
    await update.message.reply_text("🔎 Buscando pedidos...")
    archivo = buscar_pedidos(fecha)
    if archivo is None:
        await update.message.reply_text("❌ No se encontraron pedidos o ocurrió un error.")
        return ConversationHandler.END
    with open(archivo, "rb") as f:
        await update.message.reply_document(document=f)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

# ---------- DISPACHER ----------

dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_fecha)],
    states={
        PEDIR_FECHA: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_fecha)
        ]
    },
    fallbacks=[CommandHandler("cancelar", cancel)],
)

dispatcher.add_handler(CommandHandler("start", start_handler))
dispatcher.add_handler(conv_handler)

# ---------- FLASK WEBHOOK ----------

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "Bot activo!"

# ---------- RUN ----------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))