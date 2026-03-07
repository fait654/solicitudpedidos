import os
import telebot
import threading
import time
from flask import Flask
from playwright.sync_api import sync_playwright
import pandas as pd

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

esperando_fecha = {}

# -------- FUNCION BUSCAR PEDIDOS --------
def buscar_pedidos(fecha):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto("https://myeforce.ecom.com.co/ecomltda/")
            page.fill('input[name="cta"]', "ebrandy@esparta")
            page.fill('input[name="ingr"]', "Pedidosesparta2026.")
            page.click('button[type="submit"]')
            page.wait_for_timeout(5000)

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


# -------- BOT --------
@bot.message_handler(commands=['start'])
def start(message):
    esperando_fecha[message.chat.id] = True

    bot.send_message(
        message.chat.id,
        "Hola 👋\nEnvíame una fecha para buscar pedidos.\nEjemplo: 2026-03-05"
    )


@bot.message_handler(func=lambda message: True)
def recibir_fecha(message):

    if message.chat.id not in esperando_fecha:
        bot.send_message(message.chat.id, "Escribe /start para comenzar.")
        return

    fecha = message.text.strip()

    bot.send_message(message.chat.id, "🔎 Buscando pedidos...")

    archivo = buscar_pedidos(fecha)

    if archivo is None:
        bot.send_message(message.chat.id, "❌ No se encontraron pedidos.")
        return

    with open(archivo, "rb") as f:
        bot.send_document(message.chat.id, f)

    os.remove(archivo)

    esperando_fecha.pop(message.chat.id, None)


# -------- FLASK PARA RENDER --------
@app.route("/")
def home():
    return "Bot activo"


# -------- BOT LOOP SEGURO --------
def run_bot():

    print("Bot iniciado...")

    bot.remove_webhook()

    while True:
        try:
            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60,
                skip_pending=True
            )
        except Exception as e:
            print("Error en polling:", e)
            time.sleep(5)


# -------- MAIN --------
if __name__ == "__main__":

    # iniciar bot en segundo hilo
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))

    app.run(host="0.0.0.0", port=port)