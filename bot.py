import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from playwright.sync_api import sync_playwright
import pandas as pd

TOKEN = os.getenv("BOT_TOKEN")

PEDIR_FECHA = 1


# -------- FUNCION BUSCAR PEDIDOS --------

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


# -------- CONVERSACION BOT --------


async def iniciar_pedidos(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📅 ¿De qué fecha deseas obtener los pedidos?\n\nEjemplo:\n2026-03-05"
    )

    return PEDIR_FECHA


async def recibir_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):

    fecha = update.message.text.strip()

    await update.message.reply_text("🔎 Buscando pedidos...")

    archivo = buscar_pedidos(fecha)

    if archivo is None:
        await update.message.reply_text(
            "❌ No se encontraron pedidos o ocurrió un error."
        )
        return ConversationHandler.END

    with open(archivo, "rb") as f:
        await update.message.reply_document(document=f)

    return ConversationHandler.END


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("Operación cancelada.")

    return ConversationHandler.END


# -------- INICIAR BOT --------


def main():

    print("BOT INICIADO")

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("pedidos", iniciar_pedidos)],
        states={
            PEDIR_FECHA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_fecha)
            ]
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(conv_handler)

    # eliminar webhook si existía
    app.bot.delete_webhook(drop_pending_updates=True)

    app.run_polling()


if __name__ == "__main__":
    main()