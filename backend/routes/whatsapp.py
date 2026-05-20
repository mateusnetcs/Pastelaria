"""
Rotas para integração com WhatsApp.
Inclui webhook para receber mensagens do WAHA e endpoints auxiliares.
"""

from flask import Blueprint, request, jsonify
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import json
import sys
import re
import threading
import time

from config import DB_CONFIG, WAHA_API_URL, WAHA_API_KEY, WAHA_SESSION, OPENAI_API_KEY, OPENAI_MODEL, WEBHOOK_PUBLIC_URL

whatsapp_bp = Blueprint('whatsapp', __name__)

DEBOUNCE_SECONDS = 6
DEDUP_WINDOW_SECONDS = 45

_message_buffers = {}
_buffer_timers = {}
_buffer_lock = threading.Lock()
_dedup_lock = threading.Lock()
_message_ids = {}
_processed_ids = set()
_recent_by_content = {}  # hash(chat_id|texto) -> timestamp (dedup por conteúdo)
_chat_id_envio = {}  # chat_id_normalizado -> último chat_id bruto observado
_chats_processando = set()  # evita processar o mesmo chat em paralelo


def _cliente_disse_ja_paguei(texto_lower):
    if not texto_lower:
        return False
    frases = (
        'ja paguei', 'já paguei', 'já pague', 'ja pague',
        'paguei', 'fiz o pix', 'fiz o pagamento', 'pix feito',
        'pagamento feito', 'transferi', 'transferência feita',
    )
    return any(f in texto_lower for f in frases)


def _normalizar_chat_id(chat_id):
    """
    Normaliza IDs do WhatsApp para reduzir duplicidade entre formatos:
    - 5599...@c.us
    - 5599...:32@s.whatsapp.net
    - outros formatos com sufixos de dispositivo.
    """
    cid = (chat_id or "").strip()
    if not cid:
        return ""
    local = cid.split("@")[0]
    local = local.split(":")[0]
    numero = "".join(ch for ch in local if ch.isdigit())
    if not numero:
        return cid
    return f"{numero}@c.us"


def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
        return None


# =====================================================================
# WEBHOOK - Recebe mensagens do WAHA e processa com IA
# =====================================================================

@whatsapp_bp.route('/api/whatsapp/webhook', methods=['GET', 'POST'])
def webhook_waha():
    if request.method == 'GET':
        return jsonify({"status": "ok", "webhook": "pastelaria"}), 200

    """
    Recebe mensagens do WAHA e responde usando a IA.

    O WAHA envia payloads com estrutura:
    {
        "event": "message",
        "session": WAHA_SESSION,
        "payload": {
            "id": "...",
            "from": "5592999999999@c.us",
            "body": "Oi, quero fazer um pedido",
            "fromMe": false,
            ...
        }
    }
    """
    try:
        data = request.json
        if not data:
            print("[webhook] Recebido POST sem JSON", file=sys.stderr)
            return jsonify({"status": "ok"}), 200

        event = data.get('event', '')
        print(f"[webhook] RECEBIDO event={event!r} keys={list(data.keys())}", file=sys.stderr)

        if event == 'call.received':
            payload = data.get('payload', {})
            call_from = payload.get('from', '')
            print(f"[webhook] Chamada recebida de {call_from} - rejeitando", file=sys.stderr)

            try:
                import requests as req
                reject_headers = {"Content-Type": "application/json"}
                if WAHA_API_KEY:
                    reject_headers["X-Api-Key"] = WAHA_API_KEY

                call_id = payload.get('id', '')
                req.post(
                    f"{WAHA_API_URL.replace('/api', '')}/api/{WAHA_SESSION}/calls/reject",
                    headers=reject_headers,
                    json={"callId": call_id},
                    timeout=5
                )
                print(f"[webhook] Chamada {call_id} rejeitada", file=sys.stderr)
            except Exception as e:
                print(f"[webhook] Erro ao rejeitar chamada: {e}", file=sys.stderr)

            if call_from:
                try:
                    from utils.whatsapp_sender import enviar_mensagem_texto as enviar_msg_call
                    msg_rejeicao = (
                        "Oi! Eu sou a *Lia*, atendente virtual da *Pastelão Brothers*! 😊\n\n"
                        "No momento não atendemos por chamada de voz no WhatsApp.\n\n"
                        "Mas você pode:\n"
                        "🎤 *Enviar um áudio* - eu entendo e respondo na hora!\n"
                        "📝 *Enviar uma mensagem de texto* - estou sempre disponível!\n\n"
                        "É só mandar que eu te ajudo!"
                    )
                    enviar_msg_call(call_from, msg_rejeicao)
                    print(f"[webhook] Mensagem de rejeição enviada para {call_from}", file=sys.stderr)
                except Exception as e:
                    print(f"[webhook] Erro ao enviar msg de rejeição: {e}", file=sys.stderr)

            return jsonify({"status": "call_rejected"}), 200

        # WAHA dispara "message" e "message.any" para a mesma mensagem → ignora message.any
        if event == 'message.any':
            print(f"[webhook] Evento message.any ignorado (usa-se apenas message)", file=sys.stderr)
            return jsonify({"status": "ignored", "reason": "message.any duplicate event"}), 200

        if event not in ('message', 'messages.upsert'):
            print(f"[webhook] Evento ignorado: {event!r}", file=sys.stderr)
            return jsonify({"status": "ignored", "reason": "not a message event"}), 200

        payload = data.get('payload', {})
        if event == 'messages.upsert':
            evo_data = data.get('data', {})
            if isinstance(evo_data, list):
                evo_data = evo_data[0] if evo_data else {}
            evo_key = evo_data.get('key', {})
            if evo_key.get('fromMe', False):
                return jsonify({"status": "ignored", "reason": "own message"}), 200
            msg_obj = evo_data.get('message') or {}
            body = msg_obj.get('conversation') or msg_obj.get('extendedTextMessage', {}).get('text') or ''
            payload = {
                'from': evo_key.get('remoteJid', ''),
                'chatId': evo_key.get('remoteJid', ''),
                'id': evo_key.get('id', ''),
                'fromMe': evo_key.get('fromMe', False),
                'body': body
            }
            print(f"[webhook] Evolution API: chat_id={payload['from']} body={body[:50]!r}...", file=sys.stderr)

        # Ignorar mensagens enviadas por nós mesmos
        if payload.get('fromMe', False):
            return jsonify({"status": "ignored", "reason": "own message"}), 200

        chat_id_raw = payload.get('from') or payload.get('chatId', '')
        chat_id = _normalizar_chat_id(chat_id_raw)

        # Filtrar ANTES de qualquer processamento: só atender chat privado
        if not chat_id_raw:
            return jsonify({"status": "ignored", "reason": "no chat_id"}), 200

        # Ignorar grupos, status, newsletters
        if '@g.us' in chat_id_raw:
            return jsonify({"status": "ignored", "reason": "group"}), 200
        if 'status@' in chat_id_raw or '@broadcast' in chat_id_raw:
            return jsonify({"status": "ignored", "reason": "status"}), 200
        if '@newsletter' in chat_id_raw:
            return jsonify({"status": "ignored", "reason": "newsletter"}), 200

        print(f"[webhook] Chat recebido: {chat_id} (event={event})", file=sys.stderr)

        mensagem_texto = payload.get('body', '').strip()
        message_id = payload.get('id', '')

        # Deduplicação (message_id + conteúdo) — lock evita corrida entre message e message.any
        chat_num = chat_id.split('@')[0] if '@' in chat_id else chat_id
        texto_norm = ' '.join(mensagem_texto.lower().strip().split())[:300]
        content_key = f"{chat_num}|{texto_norm}"
        now = time.time()

        with _dedup_lock:
            if message_id and message_id in _processed_ids:
                print(f"[webhook] Mensagem {message_id} já processada, ignorando duplicata", file=sys.stderr)
                return jsonify({"status": "ignored", "reason": "duplicate"}), 200

            expired = [k for k, ts in _recent_by_content.items() if now - ts > DEDUP_WINDOW_SECONDS]
            for k in expired:
                del _recent_by_content[k]

            if texto_norm and content_key in _recent_by_content:
                print(f"[webhook] Conteúdo duplicado em janela de {DEDUP_WINDOW_SECONDS}s, ignorando", file=sys.stderr)
                return jsonify({"status": "ignored", "reason": "duplicate_content"}), 200

            if message_id:
                _processed_ids.add(message_id)
            if texto_norm:
                _recent_by_content[content_key] = now
            if len(_processed_ids) > 2000:
                _processed_ids.clear()

        has_media = payload.get('hasMedia', False)
        media = payload.get('media')
        if has_media and media and media.get('url'):
            media_mimetype = (media.get('mimetype', '') or
                              payload.get('_data', {}).get('mimetype', '') or '')
            is_audio = ('audio' in media_mimetype or 'ogg' in media_mimetype or
                        'voice' in media_mimetype or 'ptt' in str(payload.get('_data', {})))
            if is_audio or (not mensagem_texto and has_media):
                from utils.audio_transcriber import processar_audio_mensagem
                texto_audio = processar_audio_mensagem(media['url'])
                if texto_audio:
                    print(f"[webhook] Áudio transcrito de {chat_id}: {texto_audio[:80]}...", file=sys.stderr)
                    mensagem_texto = texto_audio
                else:
                    print(f"[webhook] Falha ao transcrever áudio de {chat_id}", file=sys.stderr)
                    from utils.whatsapp_sender import enviar_mensagem_texto as enviar_msg
                    enviar_msg(chat_id, "Desculpe, não consegui entender seu áudio. Pode digitar sua mensagem? 😊")
                    return jsonify({"status": "ok", "audio_failed": True}), 200

        if not mensagem_texto:
            return jsonify({"status": "ignored", "reason": "empty message"}), 200

        print(f"[webhook] Mensagem de {chat_id}: {mensagem_texto[:80]}...", file=sys.stderr)

        if message_id:
            from utils.whatsapp_sender import reagir_mensagem
            threading.Thread(target=reagir_mensagem, args=(chat_id, message_id), daemon=True).start()

        with _buffer_lock:
            if chat_id not in _message_buffers:
                _message_buffers[chat_id] = []
                _message_ids[chat_id] = []
            _chat_id_envio[chat_id] = chat_id_raw

            _message_buffers[chat_id].append(mensagem_texto)
            if message_id:
                _message_ids[chat_id].append(message_id)

            if chat_id in _buffer_timers:
                _buffer_timers[chat_id].cancel()

            timer = threading.Timer(
                DEBOUNCE_SECONDS,
                _processar_buffer,
                args=[chat_id]
            )
            timer.daemon = True
            _buffer_timers[chat_id] = timer
            timer.start()

            total_msgs = len(_message_buffers[chat_id])
            print(f"[debounce] {chat_id}: {total_msgs} msg(s) no buffer, aguardando {DEBOUNCE_SECONDS}s...", file=sys.stderr)

        return jsonify({"status": "ok", "buffered": True}), 200

    except Exception as e:
        print(f"[webhook] Erro: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({"status": "error", "error": str(e)}), 200


def _processar_buffer(chat_id):
    """Processa todas as mensagens acumuladas de um chat após o debounce."""
    with _buffer_lock:
        if chat_id in _chats_processando:
            print(f"[debounce] Chat {chat_id} já em processamento, ignorando timer duplicado", file=sys.stderr)
            return
        _chats_processando.add(chat_id)

    try:
        with _buffer_lock:
            mensagens = _message_buffers.pop(chat_id, [])
            ids = _message_ids.pop(chat_id, [])
            _buffer_timers.pop(chat_id, None)
            chat_id_envio = _chat_id_envio.pop(chat_id, chat_id)
            for mid in ids:
                if mid:
                    _processed_ids.add(mid)

        if not mensagens:
            return

        mensagem_combinada = "\n".join(mensagens)
        print(f"[debounce] Processando {len(mensagens)} msg(s) de {chat_id}: {mensagem_combinada[:100]}...", file=sys.stderr)

        try:
            telefone = chat_id.split('@')[0] if '@' in chat_id else chat_id

            txt_lower = mensagem_combinada.lower().strip()
            if _cliente_disse_ja_paguei(txt_lower):
                from utils.pagamento_confirmacao import verificar_e_confirmar_pagamento_chat
                from utils.whatsapp_sender import enviar_mensagem_texto

                conf = verificar_e_confirmar_pagamento_chat(chat_id, DB_CONFIG, chat_id_envio)
                if conf.get('confirmado'):
                    if not conf.get('whatsapp_enviado'):
                        from utils.whatsapp_sender import enviar_mensagem_texto
                        enviar_mensagem_texto(chat_id_envio, conf.get('message', 'Pagamento confirmado!'))
                    print(f"[debounce] Pagamento confirmado via 'Já paguei' pedido #{conf.get('pedido_id')}", file=sys.stderr)
                    return
                msg = conf.get('message') or conf.get('error') or (
                    'Ainda não localizei seu pagamento. Aguarde alguns segundos e envie *Já paguei* novamente.'
                )
                enviar_mensagem_texto(chat_id_envio, msg)
                return

            from ai.chatbot import processar_mensagem

            resultado = processar_mensagem(
                mensagem_texto=mensagem_combinada,
                chat_id=chat_id,
                telefone_cliente=telefone,
                api_key=OPENAI_API_KEY,
                model=OPENAI_MODEL,
                db_config=DB_CONFIG
            )

            resposta = resultado.get("resposta", "")
            pix_data = resultado.get("pix_data")
            cartao_data = resultado.get("cartao_data")
            skip_texto = resultado.get("skip_texto", False)

            from utils.whatsapp_sender import enviar_mensagens_separadas

            if pix_data and (pix_data.get("qr_code") or pix_data.get("qr_code_base64")):
                from utils.whatsapp_sender import enviar_pix_completo
                qr_code = pix_data.get("qr_code")
                if qr_code:
                    enviar_pix_completo(
                        chat_id_envio,
                        qr_code,
                        pix_data.get("valor_total", pix_data.get("pedido_id", 0)),
                        pix_data.get("pedido_id", 0)
                    )
                else:
                    from utils.whatsapp_sender import enviar_qr_code_pix
                    enviar_qr_code_pix(
                        chat_id_envio,
                        pix_data.get("qr_code_base64", ""),
                        float(pix_data.get("valor_total", 0) or 0),
                        pix_data.get("pedido_id", 0)
                    )
            elif cartao_data and cartao_data.get("link_pagamento"):
                from utils.whatsapp_sender import enviar_link_cartao
                enviar_link_cartao(
                    chat_id_envio,
                    cartao_data["link_pagamento"],
                    cartao_data.get("valor_total", 0),
                    cartao_data.get("pedido_id", 0)
                )
            elif resposta and not skip_texto:
                enviar_mensagens_separadas(chat_id_envio, resposta)

            print(f"[debounce] Resposta enviada para {chat_id_envio}", file=sys.stderr)

        except Exception as e:
            print(f"[debounce] Erro ao processar buffer de {chat_id}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            try:
                from utils.whatsapp_sender import enviar_mensagem_texto
                enviar_mensagem_texto(chat_id_envio, "Desculpe, tive um probleminha. Pode repetir?")
            except Exception:
                pass
    finally:
        with _buffer_lock:
            _chats_processando.discard(chat_id)


# =====================================================================
# WEBHOOK MERCADO PAGO - Confirmação automática de pagamento
# =====================================================================

@whatsapp_bp.route('/api/mercadopago/webhook', methods=['GET', 'POST'])
def webhook_mercadopago():
    """
    Recebe notificações do Mercado Pago quando um pagamento muda de status.
    Quando aprovado, atualiza o pedido e envia confirmação no WhatsApp.
    """
    if request.method == 'GET':
        return jsonify({"status": "ok", "webhook": "mercadopago"}), 200

    try:
        data = request.json or {}
        if not data and request.args:
            data = dict(request.args)

        from utils.pagamento_confirmacao import (
            extrair_payment_id_mercadopago,
            processar_webhook_mercadopago,
        )

        payment_id = extrair_payment_id_mercadopago(data, request.args)
        print(
            f"[mercadopago] Webhook payment_id={payment_id!r} "
            f"body={json.dumps(data, ensure_ascii=False)[:300]}",
            file=sys.stderr,
        )

        result = processar_webhook_mercadopago(data, request.args, get_db_connection)
        if result.get('approved') and result.get('success'):
            print(f"[mercadopago] OK pedido #{result.get('pedido_id')}", file=sys.stderr)
        elif result.get('handled'):
            print(f"[mercadopago] Processado: {result}", file=sys.stderr)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"[mercadopago] Erro no webhook: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({"status": "ok"}), 200


# =====================================================================
# ENDPOINTS AUXILIARES (mantidos para compatibilidade)
# =====================================================================

@whatsapp_bp.route('/api/whatsapp/verificar-cliente', methods=['POST'])
def verificar_cliente():
    """Verifica se cliente existe pelo número do WhatsApp."""
    try:
        data = request.json
        whatsapp_id = data.get('whatsapp_id') or data.get('chatId')
        telefone = data.get('telefone')

        if not whatsapp_id:
            return jsonify({
                'success': False,
                'error': 'whatsapp_id ou chatId é obrigatório'
            }), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500

        cursor = conn.cursor(dictionary=True)

        telefone_limpo = None
        if telefone:
            telefone_limpo = ''.join(filter(str.isdigit, telefone))

        cliente = None
        if telefone_limpo:
            cursor.execute("""
                SELECT id, nome, email, telefone, data_nascimento
                FROM usuarios
                WHERE telefone = %s OR telefone LIKE %s
                LIMIT 1
            """, (telefone_limpo, f'%{telefone_limpo[-8:]}'))
            cliente = cursor.fetchone()

        cursor.close()
        conn.close()

        if cliente:
            return jsonify({
                'success': True,
                'cliente_existe': True,
                'cliente': {
                    'id': cliente['id'],
                    'nome': cliente['nome'],
                    'email': cliente['email'],
                    'telefone': cliente['telefone'],
                    'data_nascimento': cliente['data_nascimento'].isoformat() if cliente['data_nascimento'] else None
                }
            }), 200
        else:
            return jsonify({
                'success': True,
                'cliente_existe': False,
                'mensagem': 'Cliente não encontrado. Iniciar cadastro.'
            }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@whatsapp_bp.route('/api/whatsapp/cadastrar-cliente', methods=['POST'])
def cadastrar_cliente():
    """Cadastra novo cliente via WhatsApp."""
    try:
        data = request.json
        nome = data.get('nome')
        email = data.get('email')
        telefone = data.get('telefone')
        data_nascimento = data.get('data_nascimento')

        if not nome:
            return jsonify({'success': False, 'error': 'Nome é obrigatório'}), 400
        if not email:
            return jsonify({'success': False, 'error': 'Email é obrigatório'}), 400
        if not telefone:
            return jsonify({'success': False, 'error': 'Telefone é obrigatório'}), 400

        telefone_limpo = ''.join(filter(str.isdigit, telefone))

        data_nascimento_obj = None
        if data_nascimento:
            try:
                data_nascimento_obj = datetime.strptime(data_nascimento, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'error': 'Formato de data inválido. Use YYYY-MM-DD'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500

        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Email já cadastrado'}), 400

        cursor.execute("SELECT id FROM usuarios WHERE telefone = %s", (telefone_limpo,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Telefone já cadastrado'}), 400

        cursor.execute("""
            INSERT INTO usuarios (nome, email, telefone, data_nascimento, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (nome, email, telefone_limpo, data_nascimento_obj))

        conn.commit()
        cliente_id = cursor.lastrowid
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'mensagem': 'Cliente cadastrado com sucesso!',
            'cliente': {
                'id': cliente_id,
                'nome': nome,
                'email': email,
                'telefone': telefone_limpo,
                'data_nascimento': data_nascimento if data_nascimento else None
            }
        }), 201

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@whatsapp_bp.route('/api/whatsapp/criar-pedido', methods=['POST'])
def criar_pedido_whatsapp():
    """Cria pedido via WhatsApp."""
    try:
        data = request.json
        cliente_id = data.get('cliente_id')
        whatsapp_id = data.get('whatsapp_id')
        itens = data.get('itens', [])
        observacoes = data.get('observacoes', '')
        metodo_pagamento = data.get('metodo_pagamento', 'pix')

        if not cliente_id:
            return jsonify({'success': False, 'error': 'cliente_id é obrigatório'}), 400
        if not itens or len(itens) == 0:
            return jsonify({'success': False, 'error': 'Pedido deve conter pelo menos um item'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500

        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, nome FROM usuarios WHERE id = %s", (cliente_id,))
        cliente = cursor.fetchone()
        if not cliente:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Cliente não encontrado'}), 404

        total = 0
        items_descricao = []

        for item in itens:
            produto_id = item.get('produto_id')
            quantidade = item.get('quantidade', 1)

            cursor.execute("SELECT nome, preco, ativo FROM produtos WHERE id = %s", (produto_id,))
            produto = cursor.fetchone()
            if not produto:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': f'Produto {produto_id} não encontrado'}), 400
            if not produto['ativo']:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': f'Produto {produto["nome"]} não está disponível'}), 400

            subtotal = float(produto['preco']) * quantidade
            total += subtotal
            items_descricao.append(f"{produto['nome']} x{quantidade}")

        observacoes_dict = {
            'metodo_pagamento': metodo_pagamento,
            'whatsapp_id': whatsapp_id,
            'observacoes_cliente': observacoes,
            'origem': 'whatsapp'
        }

        status_inicial = 'pago' if metodo_pagamento == 'dinheiro' else 'pendente'

        cursor.execute("""
            INSERT INTO pedidos (cliente_id, total, status, observacoes, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (cliente_id, total, status_inicial, json.dumps(observacoes_dict)))

        pedido_id = cursor.lastrowid

        for item in itens:
            produto_id = item.get('produto_id')
            quantidade = item.get('quantidade', 1)
            cursor.execute("SELECT preco FROM produtos WHERE id = %s", (produto_id,))
            produto = cursor.fetchone()
            preco_unitario = float(produto['preco'])
            cursor.execute("""
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (pedido_id, produto_id, quantidade, preco_unitario, preco_unitario * quantidade))

        conn.commit()
        cursor.close()
        conn.close()

        if metodo_pagamento == 'dinheiro':
            return jsonify({
                'success': True, 'pedido_id': pedido_id, 'total': total,
                'status': 'pago', 'mensagem': 'Pedido confirmado! Será preparado em breve.'
            }), 200

        return jsonify({
            'success': True, 'pedido_id': pedido_id, 'total': total,
            'status': 'pendente', 'itens': items_descricao,
            'mensagem': 'Pedido criado. Gerando link de pagamento...'
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@whatsapp_bp.route('/api/whatsapp/buscar-produtos', methods=['GET', 'POST'])
def buscar_produtos():
    """Busca produtos disponíveis."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nome, descricao, preco, categoria, tipo
            FROM produtos WHERE ativo = TRUE
            ORDER BY categoria, nome
        """)
        produtos = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'produtos': produtos, 'total': len(produtos)}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
