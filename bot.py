import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from playwright.sync_api import sync_playwright
import pandas as pd

TOKEN = os.getenv("BOT_TOKEN")


def buscar_pedidos(fecha):

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://myeforce.ecom.com.co/ecomltda/")

        # login
        page.fill('input[name="cta"]', "ebrandy@esparta")
        page.fill('input[name="ingr"]', "Pedidosesparta2026.")

        page.click('button[type="submit"]')

        page.wait_for_timeout(5000)

        # ir a pedidos
        page.goto("https://myeforce.ecom.com.co/eforce/modulos/pedidosNew/index.php")

        page.wait_for_timeout(4000)

        # fecha
        page.fill('input[name="fecha_ini"]', fecha)
        page.fill('input[name="fecha_fin"]', fecha)

        page.fill('input[name="cantidad"]', "99999")

        page.click('button:has-text("Buscar")')

        page.wait_for_timeout(6000)

        html = page.content()

        browser.close()

    tablas = pd.read_html(html)

    df = tablas[0]

    archivo = "pedidos.xlsx"

    df.to_excel(archivo, index=False)

    return archivo


async def pedidos(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) == 0:
        await update.message.reply_text("Usa: /pedidos 2026-03-05")
        return

    fecha = context.args[0]

    await update.message.reply_text("Buscando pedidos...")

    archivo = buscar_pedidos(fecha)

    await update.message.reply_document(document=open(archivo, "rb"))


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("pedidos", pedidos))

app.run_polling()