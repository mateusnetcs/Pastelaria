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

WAHA_API_URL = os.getenv('WAHA_API_URL', 'http://localhost:3001/api')
WAHA_API_KEY = os.getenv('WAHA_API_KEY', '')
WAHA_SESSION = os.getenv('WAHA_SESSION', 'padrão')

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

MERCADOPAGO_ACCESS_TOKEN = os.getenv('MERCADOPAGO_ACCESS_TOKEN', '')

WEBHOOK_PUBLIC_URL = os.getenv('WEBHOOK_PUBLIC_URL', '')
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', '') or secrets.token_hex(32)

ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:8001,http://localhost:5000').split(',')
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
