from dotenv import load_dotenv
import os
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

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("bot-whatsapp-promo.json", scopes=SCOPE)
client = gspread.authorize(creds)

SHEET = client.open_by_key(SHEET_ID).sheet1

@app.get("/health")
def health():
    return "ok", 200

@app.get("/test-send")
def test_send():
    to = request.args.get("to")
    r = requests.post(
        f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_ID}/messages",
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}",
                 "Content-Type": "application/json"},
        json={"messaging_product":"whatsapp","to":to,"type":"text",
              "text":{"body":"Test OK (backend)"}})
    return {"code": r.status_code, "resp": r.json()}, r.status_code


@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if token == VERIFY_TOKEN:
        return challenge
    return "Error de verificación", 403


@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()
    try:
        message = data["messages"][0]
        phone = message["from"]  # número del cliente

        print("Mensaje de:", phone)
        
        text = message["text"]["body"].strip().lower()

        # Si el usuario pide la promo
        if "promo" in text or "1" in text:
            promo = buscar_promo(phone)
            enviar_mensaje(phone, promo)
            enviar_mensaje(phone, "🧑‍💼 Te voy a comunicar con un asesor para ayudarte con tu compra.")
            derivar_a_asesor(phone, promo)
        elif "asesor" in text or "2" in text:
            enviar_mensaje(phone, "🧑‍💼 Te voy a comunicar con un asesor ahora mismo.")
            derivar_a_asesor(phone)
        else:
            enviar_mensaje(
                phone,
                "👋 Hola! Escribí *1* o *promo* para consultar tu promoción disponible.\nEscribí *2* o *asesor* para hablar con un asesor."
            )

    except Exception as e:
        print("Error:", e)
    return "ok", 200


def buscar_promo(phone):
    filas = SHEET.get_all_records()
    for fila in filas:
        if str(fila["Telefono"]) == str(phone):
            return f"🎉 Tu promoción es: {fila['Promo']}"
    return "⚠️ Tu número no figura en la lista de promociones activas."


def enviar_mensaje(to, text):
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    r = requests.post(url, headers=headers, json=data)
    print("Enviado:", r.status_code, r.text)


def derivar_a_asesor(cliente_phone, promo_text=None):
    if not ADVISOR_PHONE:
        print("ADVISOR_PHONE no configurado; no se puede derivar al asesor.")
        return
    aviso = (
        f"🔔 Nuevo cliente solicita asesoramiento\n"
        f"📱 Cliente: {cliente_phone}\n"
        + (f"🎉 Promo informada: {promo_text}\n" if promo_text else "")
        + "Por favor, contactá al cliente para continuar."
    )
    try:
        enviar_mensaje(ADVISOR_PHONE, aviso)
    except Exception as e:
        print("Error al notificar al asesor:", e)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port)