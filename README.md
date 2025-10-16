# whatsapp-promo-bot

Webhook en **Flask** para **WhatsApp Cloud API** que valida el teléfono del cliente en **Google Sheets** y devuelve su **promoción**. Preparado para despliegue en **Render**.

---

## 🚀 Características

* Recepción de mensajes vía **Webhook** de WhatsApp Cloud API.
* Lookup en **Google Sheets** (Service Account) por número de teléfono.
* Respuesta automática con la **promo** correspondiente.
* Configuración por **variables de entorno** (sin secretos en código).
* Listo para **Render** (gunicorn, healthcheck, secret file para credentials).

---

## 📁 Estructura sugerida

```
.
├─ app.py
├─ requirements.txt
├─ render.yaml           # opcional pero recomendado
├─ Procfile              # alternativo si no usas render.yaml
├─ .env.example          # ejemplo de variables
└─ README.md
```

> **Nota:** el archivo `credentials.json` (Service Account de Google) **no** debe estar en el repo. En Render se sube como **Secret File**.

---

## 🔧 Requisitos

* Python 3.9+
* Cuenta en **Meta for Developers** con producto **WhatsApp** habilitado.
* **Google Cloud** con **Service Account** y **Google Sheets API** habilitada.
* Un **Google Sheet** con columnas mínimas: `Telefono`, `Promo`.

---

## ⚙️ Variables de entorno

Crea un `.env` (o configura en Render) con:

```
WHATSAPP_TOKEN= # Token largo (Usuarios del sistema en Business Manager)
WHATSAPP_PHONE_ID= # Phone Number ID (WhatsApp → Inicio rápido)
VERIFY_TOKEN= # Token de verificación para el webhook (lo defines tú)
GOOGLE_SHEET_ID= # ID de la hoja (URL entre /d/ y /edit)
```

Archivos sensibles:

* `credentials.json` → súbelo como **Secret File** en Render (path `credentials.json`).

---

## 📦 Instalación local

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # completa tus valores
python app.py                   # inicia en http://localhost:3000
```

> Para exponer localmente usa **ngrok**: `ngrok http 3000`.

---

## 🔌 Endpoints

* `GET /webhook` → verificación de Meta (usa `VERIFY_TOKEN`).
* `POST /webhook` → recepción de mensajes (extrae `from`, busca promo y responde).
* `GET /health` → healthcheck para Render.

---

## 🧠 Formato de Google Sheet

Ejemplo de contenido:

| Telefono      | Nombre       | Promo                                 |
| ------------- | ------------ | ------------------------------------- |
| 5491123456789 | Ana Martínez | 20% de descuento en tu próxima compra |
| 5491198765432 | Luis Gómez   | Envío gratis en tu siguiente pedido   |

> Los teléfonos deben venir **sin +** y en el mismo formato que entrega WhatsApp Cloud API.

---

## 🛠️ Despliegue en Render

1. Subir el repo a GitHub/GitLab.
2. En Render: **New → Web Service**.
3. Si usas `render.yaml`, Render lo detecta automáticamente. Si no, usa `Procfile`.
4. Variables de entorno: `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `VERIFY_TOKEN`, `GOOGLE_SHEET_ID`.
5. **Secret File**: agregar `credentials.json` (pegar el JSON del Service Account).
6. Deploy. Verifica `GET /health`.

### `render.yaml` de ejemplo

```yaml
services:
  - type: web
    name: whatsapp-webhook
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn app:app --workers=2 --threads=4 --timeout=120 --bind 0.0.0.0:$PORT"
    envVars:
      - key: WHATSAPP_TOKEN
        sync: false
      - key: WHATSAPP_PHONE_ID
        sync: false
      - key: VERIFY_TOKEN
        sync: false
      - key: GOOGLE_SHEET_ID
        sync: false
    healthCheckPath: /health
```

### `Procfile` alternativo

```
web: gunicorn app:app --workers=2 --threads=4 --timeout=120 --bind 0.0.0.0:$PORT
```

---


## 🧪 Pruebas sin consumir cuota

* En developers.facebook.com → **Webhooks** → **Enviar carga de prueba** (`messages`).
* Agregar flag **DRY_RUN** (opcional) para simular sin enviar a Graph.

---

## ❓ Troubleshooting rápido

* **403 al verificar webhook** → `VERIFY_TOKEN` no coincide.
* **400 al enviar mensaje** → token inválido/expirado o Phone ID incorrecto.
* **No encuentra promo** → revisar formato de `Telefono` y `GOOGLE_SHEET_ID`.
* **Render se cae** → revisar logs y `PORT`; usar `gunicorn`.

---

## 📄 Licencia

MIT .
