"""
Autenticação do cliente (site) — login com Google.
"""
import logging
import secrets
from datetime import date

import bcrypt
import requests as http_requests
from flask import Blueprint, jsonify, request, session
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_IDS, FLASK_DEBUG

bp = Blueprint('client_auth', __name__)

_google_id_column = None


def _get_db():
    from app import get_db_connection
    return get_db_connection()


def _has_google_id_column(conn):
    global _google_id_column
    if _google_id_column is not None:
        return _google_id_column
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'usuarios'
              AND COLUMN_NAME = 'google_id'
        """)
        row = cursor.fetchone()
        _google_id_column = bool(row and row[0] > 0)
    finally:
        cursor.close()
    return _google_id_column


def _ensure_google_id_column(conn):
    global _google_id_column
    if _has_google_id_column(conn):
        return
    cursor = conn.cursor()
    try:
        cursor.execute("""
            ALTER TABLE usuarios
            ADD COLUMN google_id VARCHAR(255) NULL UNIQUE AFTER email
        """)
        conn.commit()
        _google_id_column = True
        logging.info("[auth] Coluna google_id criada em usuarios")
    except Exception as e:
        logging.warning("[auth] Não foi possível criar coluna google_id: %s", e)
    finally:
        cursor.close()


def _criar_sessao(user):
    session['user_id'] = user['id']
    session['user_nome'] = user['nome']
    session['user_email'] = user['email']


def _user_response(user):
    return {
        'id': user['id'],
        'nome': user['nome'],
        'email': user['email'],
    }


def _email_verificado(idinfo: dict) -> bool:
    ev = idinfo.get('email_verified')
    return ev is True or str(ev).lower() in ('true', '1', 'yes')


def _fetch_google_birthday(access_token: str):
    """
    Busca aniversário na conta Google (People API).
    Requer escopo user.birthday.read e People API ativa no Google Cloud.
    """
    if not access_token:
        return None
    try:
        resp = http_requests.get(
            'https://people.googleapis.com/v1/people/me',
            params={'personFields': 'birthdays'},
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=15,
        )
        if resp.status_code != 200:
            logging.warning('[auth] People API birthdays: %s %s', resp.status_code, resp.text[:200])
            return None
        birthdays = (resp.json() or {}).get('birthdays') or []
        for entry in birthdays:
            d = entry.get('date') or {}
            month, day = d.get('month'), d.get('day')
            if not month or not day:
                continue
            year = d.get('year') or 1900
            try:
                return date(int(year), int(month), int(day))
            except (TypeError, ValueError):
                continue
    except Exception as e:
        logging.warning('[auth] Erro ao buscar aniversário Google: %s', e)
    return None


def _salvar_data_nascimento(user_id: int, data_nasc: date) -> bool:
    conn = _get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE usuarios
            SET data_nascimento = %s
            WHERE id = %s AND data_nascimento IS NULL
            """,
            (data_nasc, user_id),
        )
        conn.commit()
        updated = cursor.rowcount > 0
        cursor.close()
        conn.close()
        return updated
    except Exception:
        logging.exception('[auth] Erro ao salvar data_nascimento')
        return False


def _verify_via_google_tokeninfo(credential: str, client_ids: list) -> dict:
    """
    Valida o token nos servidores do Google (evita falso 'expirado' por relógio do PC errado).
    """
    resp = http_requests.get(
        'https://oauth2.googleapis.com/tokeninfo',
        params={'id_token': credential},
        timeout=15,
    )
    if resp.status_code != 200:
        try:
            err_body = resp.json()
            err_msg = err_body.get('error_description') or err_body.get('error') or resp.text
        except Exception:
            err_msg = resp.text
        raise ValueError(err_msg or 'Token rejeitado pelo Google')

    data = resp.json()
    token_aud = data.get('aud') or data.get('azp')
    if token_aud not in client_ids:
        raise ValueError(
            f"Token aud={token_aud!r} não corresponde ao GOOGLE_CLIENT_ID do servidor"
        )
    return data


def _verify_google_credential(credential: str) -> dict:
    """Valida JWT do Google Sign-In."""
    client_ids = GOOGLE_CLIENT_IDS or ([GOOGLE_CLIENT_ID] if GOOGLE_CLIENT_ID else [])
    if not client_ids:
        raise ValueError('GOOGLE_CLIENT_ID não configurado no servidor')

    # 1) Preferir validação no Google (relógio correto, menos falso positivo de expiração)
    try:
        return _verify_via_google_tokeninfo(credential, client_ids)
    except ValueError as e:
        logging.warning("[auth] tokeninfo falhou: %s", e)

    # 2) Fallback local
    req = google_requests.Request()
    last_error = None
    for client_id in client_ids:
        try:
            return id_token.verify_oauth2_token(
                credential,
                req,
                client_id,
                clock_skew_in_seconds=600,
            )
        except ValueError as e:
            last_error = e
            logging.warning("[auth] verify local (%s...): %s", client_id[:16], e)

    raise last_error or ValueError('Token inválido')


@bp.route('/api/auth/config', methods=['GET'])
def auth_config():
    """Config pública para o frontend (ex.: Client ID do Google)."""
    return jsonify({
        'success': True,
        'google_client_id': GOOGLE_CLIENT_ID or None,
        'google_enabled': bool(GOOGLE_CLIENT_ID),
    }), 200


@bp.route('/api/auth/google', methods=['POST'])
def auth_google():
    """Valida o JWT do Google Sign-In e cria sessão do cliente."""
    if not GOOGLE_CLIENT_ID:
        return jsonify({
            'success': False,
            'error': 'Login com Google não configurado no servidor',
        }), 503

    data = request.get_json(silent=True) or {}
    credential = (data.get('credential') or '').strip()
    if not credential:
        return jsonify({'success': False, 'error': 'Token do Google ausente'}), 400

    try:
        idinfo = _verify_google_credential(credential)
    except ValueError as e:
        err = str(e).lower()
        logging.warning("[auth] Token Google inválido: %s", e)
        if 'expired' in err or 'token expired' in err or 'expirado' in err:
            msg = 'Sessão do Google expirou. Feche o modal e clique em Continuar com Google novamente.'
        elif 'audience' in err or 'aud=' in err or 'wrong audience' in err:
            msg = (
                'Client ID do Google não confere entre site e servidor. '
                'Verifique GOOGLE_CLIENT_ID no .env / Coolify.'
            )
        else:
            msg = 'Token do Google inválido ou expirado'
        if FLASK_DEBUG:
            msg = f'{msg} ({e})'
        return jsonify({'success': False, 'error': msg}), 401

    iss = idinfo.get('iss', '')
    if iss not in ('accounts.google.com', 'https://accounts.google.com'):
        return jsonify({'success': False, 'error': 'Emissor do token inválido'}), 401

    email = (idinfo.get('email') or '').strip().lower()
    nome = (idinfo.get('name') or idinfo.get('given_name') or email.split('@')[0] or 'Cliente').strip()
    google_sub = idinfo.get('sub', '')

    if not email or not _email_verificado(idinfo):
        return jsonify({'success': False, 'error': 'Email do Google não verificado'}), 400

    conn = _get_db()
    if not conn:
        return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500

    try:
        _ensure_google_id_column(conn)
        has_google_col = _has_google_id_column(conn)
        cursor = conn.cursor(dictionary=True)

        user = None
        if has_google_col and google_sub:
            cursor.execute(
                "SELECT id, nome, email, is_admin FROM usuarios WHERE google_id = %s",
                (google_sub,),
            )
            user = cursor.fetchone()

        if not user:
            cursor.execute(
                "SELECT id, nome, email, is_admin FROM usuarios WHERE email = %s",
                (email,),
            )
            user = cursor.fetchone()

        if user and user.get('is_admin'):
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Use o painel administrativo para esta conta',
            }), 403

        if user:
            if has_google_col and google_sub:
                cursor.execute(
                    "UPDATE usuarios SET google_id = %s, nome = %s WHERE id = %s",
                    (google_sub, nome, user['id']),
                )
                conn.commit()
                user['nome'] = nome
        else:
            senha_aleatoria = secrets.token_urlsafe(32)
            senha_hash = bcrypt.hashpw(
                senha_aleatoria.encode('utf-8'),
                bcrypt.gensalt(),
            ).decode('utf-8')

            if has_google_col and google_sub:
                cursor.execute("""
                    INSERT INTO usuarios (nome, email, senha, google_id, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (nome, email, senha_hash, google_sub))
            else:
                cursor.execute("""
                    INSERT INTO usuarios (nome, email, senha, created_at)
                    VALUES (%s, %s, %s, NOW())
                """, (nome, email, senha_hash))

            conn.commit()
            user = {
                'id': cursor.lastrowid,
                'nome': nome,
                'email': email,
            }

        cursor.close()
        conn.close()

        _criar_sessao(user)
        return jsonify({
            'success': True,
            'user': _user_response(user),
            'sync_birthday': True,
        }), 200

    except Exception:
        logging.exception("[auth] Erro no login Google")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@bp.route('/api/auth/google/birthday', methods=['POST'])
def auth_google_birthday():
    """Salva data de nascimento do cliente a partir do token OAuth (escopo birthday)."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401

    data = request.get_json(silent=True) or {}
    access_token = (data.get('access_token') or '').strip()
    if not access_token:
        return jsonify({'success': False, 'error': 'Token de acesso ausente'}), 400

    data_nasc = _fetch_google_birthday(access_token)
    if not data_nasc:
        return jsonify({
            'success': False,
            'error': 'Aniversário não encontrado na conta Google ou permissão negada',
        }), 404

    saved = _salvar_data_nascimento(user_id, data_nasc)
    return jsonify({
        'success': True,
        'data_nascimento': data_nasc.isoformat(),
        'saved': saved,
    }), 200
