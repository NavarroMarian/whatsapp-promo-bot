from dotenv import load_dotenv
import os
import logging
from flask import Flask, request
import requests
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

load_dotenv() 

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
ADVISOR_PHONE = os.getenv("ADVISOR_PHONE")

# Logging setup
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("bot-whatsapp-promo.json", scopes=SCOPE)
client = gspread.authorize(creds)

SHEET = client.open_by_key(SHEET_ID).sheet1

@app.get("/health")
def health():
    logger.debug("Health check")
    return "ok", 200

@app.get("/test-send")
def test_send():
    to = request.args.get("to")
    enviar_mensaje(to, "Test OK (backend)")
    return {"code": 200, "resp": "sent"}, 200


@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return challenge
    logger.warning("Webhook verification failed: invalid token")
    return "Error de verificación", 403


@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json(silent=True) or {}
    try:
        logger.info("Webhook received")
        logger.info(f"JSON parsed: {data}")

        value = (
            (data.get("entry") or [{}])[0]
            .get("changes", [{}])[0]
            .get("value", {})
        )
        messages = value.get("messages") or []
        if not messages:
            logger.warning("Webhook sin mensajes; nada que procesar")
            return "ok", 200

        message = messages[0]
        phone = message.get("from") 
        logger.info(f"Mensaje de: {phone}")

        text = (message.get("text", {}).get("body") or "").strip().lower()
        logger.info(f"Texto recibido: {text}")

        # Si el usuario pide la promo
        if "promo" in text or "1" in text:
            promo = buscar_promo(phone)
            logger.info("Respondiendo con promo y derivación a asesor")
            enviar_mensaje(phone, promo)
            enviar_mensaje(phone, "🧑‍💼 Te voy a comunicar con un asesor para ayudarte con tu compra.")
            derivar_a_asesor(phone, promo)
        elif "asesor" in text or "2" in text:
            logger.info("Usuario solicitó hablar con asesor")
            enviar_mensaje(phone, "🧑‍💼 Te voy a comunicar con un asesor ahora mismo.")
            derivar_a_asesor(phone)
        else:
            logger.info("Mostrando opciones iniciales")
            enviar_mensaje(
                phone,
                "👋 Hola! Escribí *1* o *promo* para consultar tu promoción disponible.\nEscribí *2* o *asesor* para hablar con un asesor."
            )

    except Exception:
        logger.exception("Error procesando webhook")
    return "ok", 200


def buscar_promo(phone):
    logger.debug(f"Buscando promo para: {phone}")
    filas = SHEET.get_all_records()
    for fila in filas:
        if str(fila["Telefono"]) == str(phone):
            logger.info("Promo encontrada para cliente")
            return f"🎉 Tu promoción es: {fila['Promo']}"
    logger.info("Cliente sin promo activa")
    return "⚠️ Tu número no figura en la lista de promociones activas."


def enviar_mensaje(to, text):
    # Normalizar formato: si viene como 54911xxxxxxxx, enviar como 541115xxxxxxxx
    try:
        to_str = str(to)
        if to_str.startswith("54911") and len(to_str) > 5:
            to_norm = "541115" + to_str[5:]
        else:
            to_norm = to_str
    except Exception:
        to_norm = to
    logger.info(f"Enviando mensaje a: {to_norm}")
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to_norm,
        "type": "text",
        "text": {"body": text}
    }
    r = requests.post(url, headers=headers, json=data)
    logger.info(f"WhatsApp API respuesta: {r.status_code}")
    logger.info(f"WhatsApp API body: {r.text}")


def derivar_a_asesor(cliente_phone, promo_text=None):
    if not ADVISOR_PHONE:
        logger.info("ADVISOR_PHONE no configurado; no se puede derivar al asesor.")
        return
    aviso = (
        f"🔔 Nuevo cliente solicita asesoramiento\n"
        f"📱 Cliente: {cliente_phone}\n"
        + (f"🎉 Promo informada: {promo_text}\n" if promo_text else "")
        + "Por favor, contactá al cliente para continuar."
    )
    try:
        logger.info(f"Notificando al asesor {ADVISOR_PHONE} para cliente {cliente_phone}")
        enviar_mensaje(ADVISOR_PHONE, aviso)
    except Exception:
        logger.exception("Error al notificar al asesor")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port)