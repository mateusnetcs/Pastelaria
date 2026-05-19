"""
Configurações centralizadas do projeto.
Carrega variáveis de ambiente do arquivo .env (sem fallbacks de credenciais sensíveis).
"""
import os
import secrets
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'pastelaria'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', '3306'))
}

WAHA_API_URL = (os.getenv('WAHA_API_URL') or 'http://localhost:3001/api').strip()
# Valor do header X-Api-Key para o WAHA: tem de ser a chave em TEXTO PLANO.
# NÃO use o valor "sha512:..." que aparece nas env vars do Docker — esse é só o hash guardado no servidor.
WAHA_API_KEY = (os.getenv('WAHA_API_KEY') or '').strip()
WAHA_SESSION = (os.getenv('WAHA_SESSION') or 'default').strip()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

MERCADOPAGO_ACCESS_TOKEN = os.getenv('MERCADOPAGO_ACCESS_TOKEN', '')

WEBHOOK_PUBLIC_URL = os.getenv('WEBHOOK_PUBLIC_URL', '')
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', '') or secrets.token_hex(32)

_allowed_raw = os.getenv('ALLOWED_ORIGINS', 'http://localhost:8001,http://localhost:5000')
ALLOWED_ORIGINS = [o.strip() for o in _allowed_raw.split(',') if o.strip()]
# Dev: navegador em 127.0.0.1 é origem diferente de localhost — incluir para CORS em chamadas à API
for _o in ('http://127.0.0.1:8001', 'http://127.0.0.1:5000'):
    if _o not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(_o)
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

# Google Sign-In (OAuth 2.0 — tipo "Aplicativo da Web" no Google Cloud Console)
GOOGLE_CLIENT_ID = (os.getenv('GOOGLE_CLIENT_ID') or '').strip()
GOOGLE_CLIENT_SECRET = (os.getenv('GOOGLE_CLIENT_SECRET') or '').strip()
# Suporta vários IDs separados por vírgula (ex.: dev + produção)
GOOGLE_CLIENT_IDS = [
    x.strip() for x in GOOGLE_CLIENT_ID.split(',') if x.strip()
]
