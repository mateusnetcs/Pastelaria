"""
Confirmação de pagamento Mercado Pago + notificação WhatsApp.
"""
import json
import os
import re
import subprocess
import sys


def extrair_payment_id_mercadopago(data, query_args):
    """Extrai ID do pagamento de webhooks MP (vários formatos)."""
    data = data or {}
    if hasattr(query_args, 'get'):
        q = query_args
    else:
        q = {}

    pid = q.get('data.id') or q.get('id')
    if not pid:
        inner = data.get('data')
        if isinstance(inner, dict):
            pid = inner.get('id')
        elif inner is not None:
            pid = inner
    if not pid:
        pid = data.get('id')
    if not pid and data.get('resource'):
        # Formato antigo: resource = /v1/payments/123
        m = re.search(r'/payments/(\d+)', str(data.get('resource', '')))
        if m:
            pid = m.group(1)
    return str(pid).strip() if pid else None


def eh_notificacao_pagamento(data, query_args):
    data = data or {}
    tipo = ''
    if hasattr(query_args, 'get'):
        tipo = (query_args.get('type') or query_args.get('topic') or '').lower()
        if query_args.get('id') and 'payment' in tipo:
            return True
    if not tipo:
        tipo = (data.get('type') or data.get('topic') or data.get('action') or '').lower()
    return (
        'payment' in tipo
        or str(data.get('action', '')).startswith('payment.')
        or bool(data.get('data'))
    )


def resolver_chat_id_para_envio(pedido, chat_id_fallback=None):
    """Resolve JID do WhatsApp para enviar mensagem."""
    if not pedido:
        return chat_id_fallback
    try:
        obs = json.loads(pedido.get('observacoes') or '{}')
        wid = obs.get('whatsapp_id_envio') or obs.get('whatsapp_id')
        if wid and '@' in str(wid):
            return wid
    except (json.JSONDecodeError, TypeError):
        pass

    tel = pedido.get('cliente_whatsapp') or ''
    if not tel and pedido.get('cliente_telefone'):
        tel = pedido.get('cliente_telefone')
    tel = ''.join(filter(str.isdigit, str(tel)))
    if tel:
        if not tel.startswith('55') and len(tel) <= 11:
            tel = '55' + tel
        return f"{tel}@c.us"
    return chat_id_fallback


def _consultar_status_mp(payment_id):
    script_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'Mercado pago', 'api-mercadopago.py'
    )
    result = subprocess.run(
        [sys.executable, script_path],
        input=json.dumps({"action": "verificar_status", "payment_id": str(payment_id)}),
        text=True,
        capture_output=True,
        timeout=15,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    lines = result.stdout.strip().split('\n')
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return None


def buscar_pedido_por_pagamento(cursor, payment_id, external_ref=None):
    pedido = None
    if payment_id:
        cursor.execute(
            """
            SELECT id, cliente_id, cliente_nome, total, status, observacoes,
                   preference_id, cliente_whatsapp, cliente_telefone
            FROM pedidos WHERE preference_id = %s ORDER BY id DESC LIMIT 1
            """,
            (str(payment_id),),
        )
        pedido = cursor.fetchone()

    if not pedido and external_ref:
        match = re.match(r'PEDIDO_(\d+)_', external_ref or '')
        if match:
            ref_pedido_id = int(match.group(1))
            cursor.execute(
                """
                SELECT id, cliente_id, cliente_nome, total, status, observacoes,
                       preference_id, cliente_whatsapp, cliente_telefone
                FROM pedidos WHERE id = %s LIMIT 1
                """,
                (ref_pedido_id,),
            )
            pedido = cursor.fetchone()
    return pedido


def buscar_pedido_pendente_chat(cursor, chat_id):
    """Último pedido pendente associado ao chat WhatsApp."""
    if not chat_id:
        return None
    numero = chat_id.split('@')[0] if '@' in chat_id else chat_id
    numero = ''.join(filter(str.isdigit, numero))
    sufixo = numero[-9:] if len(numero) >= 9 else numero
    patterns = [f'%{chat_id}%']
    if numero:
        patterns.append(f'%{numero}%')
    if sufixo:
        patterns.append(f'%{sufixo}%')

    for pat in patterns:
        cursor.execute(
            """
            SELECT id, cliente_id, cliente_nome, total, status, observacoes,
                   preference_id, cliente_whatsapp, cliente_telefone
            FROM pedidos
            WHERE status = 'pendente' AND preference_id IS NOT NULL
              AND (observacoes LIKE %s OR cliente_whatsapp LIKE %s OR cliente_telefone LIKE %s)
            ORDER BY id DESC LIMIT 1
            """,
            (pat, pat, pat),
        )
        row = cursor.fetchone()
        if row:
            return row
    return None


def mensagem_confirmacao_pagamento(pedido, nome_cliente=None):
    nome = nome_cliente or pedido.get('cliente_nome') or 'cliente'
    tipo = 'entrega'
    try:
        obs = json.loads(pedido.get('observacoes') or '{}')
        if obs.get('retirada_local') or obs.get('tipo_entrega') == 'retirada':
            tipo = 'retirada'
    except (json.JSONDecodeError, TypeError):
        pass

    if tipo == 'retirada':
        extra = "Assim que estiver pronto, avisamos para você retirar no local! 🏪"
    else:
        extra = "Seu pedido já está sendo preparado e será entregue no endereço informado! 🛵"

    return (
        f"✅ *Pagamento confirmado!*\n\n"
        f"Pedido *#{pedido['id']}* recebido com sucesso.\n"
        f"Obrigado(a), *{nome}*! 💛\n\n"
        f"{extra}"
    )


def confirmar_pedido_pago(conn, pedido, chat_id_envio=None, payment_id=None):
    """
    Marca pedido como pago e envia WhatsApp.
    Retorna dict com success, message, ja_estava_pago, etc.
    """
    if not pedido:
        return {"success": False, "error": "Pedido não encontrado"}

    status_finais = ('pago', 'preparando', 'pronto', 'entregue', 'retirado', 'confirmado')
    if pedido.get('status') in status_finais:
        return {
            "success": True,
            "ja_estava_pago": True,
            "pedido_id": pedido['id'],
            "message": f"Pedido #{pedido['id']} já estava confirmado.",
        }

    cursor = conn.cursor(dictionary=True)
    if payment_id and not pedido.get('preference_id'):
        cursor.execute(
            "UPDATE pedidos SET preference_id = %s WHERE id = %s",
            (str(payment_id), pedido['id']),
        )

    cursor.execute("UPDATE pedidos SET status = 'pago' WHERE id = %s", (pedido['id'],))
    conn.commit()

    nome = pedido.get('cliente_nome')
    if pedido.get('cliente_id'):
        cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (pedido['cliente_id'],))
        row = cursor.fetchone()
        if row and row.get('nome'):
            nome = row['nome']

    jid = resolver_chat_id_para_envio(pedido, chat_id_envio)
    msg = mensagem_confirmacao_pagamento(pedido, nome)
    enviado = False
    if jid:
        from utils.whatsapp_sender import enviar_mensagem_texto
        r = enviar_mensagem_texto(jid, msg)
        enviado = r.get('success', False)
        print(f"[pagamento] Confirmação pedido #{pedido['id']} → {jid} enviado={enviado}", file=sys.stderr)
    else:
        print(f"[pagamento] Sem JID WhatsApp para pedido #{pedido['id']}", file=sys.stderr)

    return {
        "success": True,
        "pedido_id": pedido['id'],
        "whatsapp_enviado": enviado,
        "message": msg,
    }


def verificar_e_confirmar_pagamento_chat(chat_id, db_config, chat_id_envio=None):
    """
    Consulta Mercado Pago para o último pedido pendente do chat.
    Usado no webhook MP e quando o cliente diz 'Já paguei'.
    """
    conn = _connect(db_config)
    if not conn:
        return {"success": False, "error": "Erro DB"}

    try:
        cursor = conn.cursor(dictionary=True)
        pedido = buscar_pedido_pendente_chat(cursor, chat_id)
        if not pedido:
            cursor.close()
            conn.close()
            return {
                "success": False,
                "error": "Nenhum pedido pendente com PIX encontrado para este chat.",
            }

        payment_id = pedido.get('preference_id')
        if not payment_id:
            cursor.close()
            conn.close()
            return {"success": False, "error": "Pedido sem ID de pagamento Mercado Pago."}

        mp = _consultar_status_mp(payment_id)
        if not mp or not mp.get('success'):
            cursor.close()
            conn.close()
            return {
                "success": False,
                "error": "Não foi possível consultar o pagamento no Mercado Pago.",
            }

        status = (mp.get('status') or '').lower()
        if status in ('approved', 'aprovado', 'authorized'):
            result = confirmar_pedido_pago(conn, pedido, chat_id_envio, payment_id)
            cursor.close()
            conn.close()
            result['status_mp'] = status
            result['confirmado'] = True
            return result

        cursor.close()
        conn.close()
        return {
            "success": True,
            "confirmado": False,
            "status_mp": status,
            "pedido_id": pedido['id'],
            "message": (
                f"Ainda não localizei o pagamento do pedido #{pedido['id']} no sistema. "
                "Se você acabou de pagar, aguarde alguns segundos e envie *Já paguei* novamente. 😊"
            ),
        }
    except Exception as e:
        print(f"[pagamento] Erro verificar chat: {e}", file=sys.stderr)
        return {"success": False, "error": str(e)}


def _connect(db_config):
    import mysql.connector
    return mysql.connector.connect(**db_config)


def processar_webhook_mercadopago(data, query_args, get_db_connection_fn):
    """Processa notificação do Mercado Pago e confirma pedido se aprovado."""
    if not eh_notificacao_pagamento(data, query_args):
        return {"handled": False, "reason": "not payment notification"}

    payment_id = extrair_payment_id_mercadopago(data, query_args)
    if not payment_id:
        return {"handled": False, "reason": "no payment id"}

    mp = _consultar_status_mp(payment_id)
    if not mp or not mp.get('success'):
        return {"handled": True, "error": "mp consult failed"}

    status = (mp.get('status') or '').lower()
    if status not in ('approved', 'aprovado', 'authorized'):
        return {"handled": True, "status": status, "approved": False}

    external_ref = mp.get('external_reference', '')
    conn = get_db_connection_fn()
    if not conn:
        return {"handled": True, "error": "db"}

    cursor = conn.cursor(dictionary=True)
    pedido = buscar_pedido_por_pagamento(cursor, payment_id, external_ref)
    cursor.close()

    if not pedido:
        print(
            f"[mercadopago] Pedido não encontrado payment_id={payment_id} ref={external_ref}",
            file=sys.stderr,
        )
        conn.close()
        return {"handled": True, "approved": True, "pedido": None}

    result = confirmar_pedido_pago(conn, pedido, payment_id=payment_id)
    conn.close()
    result['handled'] = True
    result['approved'] = True
    return result
