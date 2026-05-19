"""
Proxy do QR do WAHA — Blueprint registado no app antes dos outros, para evitar
conflito com regras estáticas / catch-all em alguns deploys.
"""
import base64
import logging
import os

import jwt
import requests
from flask import Blueprint, jsonify, request
from functools import wraps

from config import FLASK_SECRET_KEY, WAHA_API_KEY, WAHA_API_URL, WAHA_SESSION

bp = Blueprint('waha_qr', __name__)
ADMIN_JWT_ALGORITHM = 'HS256'


def _admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
        if not token:
            return jsonify({'success': False, 'error': 'Não autenticado'}), 401
        try:
            payload = jwt.decode(token, FLASK_SECRET_KEY, algorithms=[ADMIN_JWT_ALGORITHM])
            request.admin_user_id = payload.get('user_id') or int(payload.get('sub', 0))
            if not request.admin_user_id:
                return jsonify({'success': False, 'error': 'Token inválido'}), 401
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'error': 'Sessão expirada'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    return decorated


@bp.route('/api/diag', methods=['GET'])
def api_diag():
    """Público: confirma que este código Flask está a correr (sem isto, outro processo ocupa a porta)."""
    return jsonify({
        'ok': True,
        'service': 'pastelaria',
        'waha_qr_blueprint': True,
        'app_file': os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py')),
    }), 200


@bp.route('/api/admin/waha/qr', methods=['GET'])
@bp.route('/api/waha/qr', methods=['GET'])
@_admin_required
def admin_waha_qr():
    """Retorna o QR da sessão WAHA em base64 (proxy seguro — chave fica no servidor)."""
    try:
        if not WAHA_API_URL or not WAHA_API_KEY:
            return jsonify({'success': False, 'error': 'WAHA não configurado no servidor'}), 500
        if WAHA_API_KEY.lower().startswith('sha512:'):
            return jsonify({
                'success': False,
                'error': 'No .env, WAHA_API_KEY não pode ser o hash "sha512:..." do Docker/Coolify. O WAHA exige no header X-Api-Key a chave em texto plano (a password que definiu). No painel WAHA (Swagger ou Keys) use a mesma chave — ou defina no Coolify WAHA_API_KEY=MinhaChaveSecreta e aqui no .env ponha MinhaChaveSecreta (sem sha512:).',
            }), 400
        session_name = (request.args.get('session') or WAHA_SESSION or 'default').strip() or 'default'
        base = WAHA_API_URL.rstrip('/')
        url = f'{base}/{session_name}/auth/qr'
        headers = {
            'X-Api-Key': WAHA_API_KEY,
            'Accept': 'application/json',
        }
        r = requests.get(url, params={'format': 'image'}, headers=headers, timeout=45)
        if r.status_code == 405:
            r = requests.post(url, json={'format': 'image'}, headers=headers, timeout=45)
        ct = (r.headers.get('Content-Type') or '').lower()
        if r.status_code == 200 and 'application/json' in ct:
            try:
                payload = r.json()
            except Exception:
                payload = {}
            b64 = payload.get('data')
            mime = payload.get('mimetype') or 'image/png'
            if b64:
                return jsonify({'success': True, 'mimetype': mime, 'data': b64, 'session': session_name}), 200
        if r.status_code == 200 and ct.startswith('image/'):
            b64 = base64.b64encode(r.content).decode('ascii')
            mime = ct.split(';')[0].strip() or 'image/png'
            return jsonify({'success': True, 'mimetype': mime, 'data': b64, 'session': session_name}), 200
        detail = (r.text or '')[:800]
        if r.status_code == 401:
            return jsonify({
                'success': False,
                'error': 'WAHA recusou a chave (401). WAHA_API_KEY no .env tem de ser a chave em texto plano enviada no X-Api-Key (não o "sha512:..." do Docker). Teste no Swagger do WAHA com o mesmo valor. Reinicie o Flask após alterar o .env.',
                'status': 401,
                'detail': detail,
            }), 502
        if r.status_code == 403:
            return jsonify({
                'success': False,
                'error': 'WAHA negou o acesso (403). Verifique WAHA_API_KEY e permissões no painel.',
                'status': 403,
                'detail': detail,
            }), 502
        return jsonify({
            'success': False,
            'error': 'Não foi possível obter o QR (sessão já conectada ou WAHA indisponível)',
            'status': r.status_code,
            'detail': detail,
        }), 502
    except requests.RequestException as e:
        logging.exception('admin_waha_qr')
        return jsonify({'success': False, 'error': f'Falha ao contatar o WAHA: {e}'}), 502
    except Exception as e:
        logging.exception('admin_waha_qr')
        return jsonify({'success': False, 'error': str(e)}), 500
