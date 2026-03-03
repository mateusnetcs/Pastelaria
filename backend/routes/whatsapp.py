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
DEDUP_WINDOW_SECONDS = 25

_message_buffers = {}
_buffer_timers = {}
_buffer_lock = threading.Lock()
_message_ids = {}
_processed_ids = set()
_recent_by_content = {}  # hash(chat_id|texto) -> timestamp (dedup por conteúdo)


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

        chat_id = payload.get('from') or payload.get('chatId', '')

        # Filtrar ANTES de qualquer processamento: só atender chat privado
        if not chat_id:
            return jsonify({"status": "ignored", "reason": "no chat_id"}), 200

        # Ignorar grupos, status, newsletters
        if '@g.us' in chat_id:
            return jsonify({"status": "ignored", "reason": "group"}), 200
        if 'status@' in chat_id or '@broadcast' in chat_id:
            return jsonify({"status": "ignored", "reason": "status"}), 200
        if '@newsletter' in chat_id:
            return jsonify({"status": "ignored", "reason": "newsletter"}), 200

        print(f"[webhook] Chat recebido: {chat_id} (event={event})", file=sys.stderr)

        mensagem_texto = payload.get('body', '').strip()
        message_id = payload.get('id', '')

        # Deduplicação 1: ignorar message_id já processado
        if message_id:
            with _buffer_lock:
                all_ids = []
                for ids in _message_ids.values():
                    all_ids.extend(ids)
                if message_id in all_ids or message_id in _processed_ids:
                    print(f"[webhook] Mensagem {message_id} já processada, ignorando duplicata", file=sys.stderr)
                    return jsonify({"status": "ignored", "reason": "duplicate"}), 200

        # Deduplicação 2: ignorar mesmo conteúdo (chat_id + texto) em janela curta
        # WAHA pode enviar message + message.any com IDs diferentes; normalizar para pegar variações
        chat_num = chat_id.split('@')[0] if '@' in chat_id else chat_id
        texto_norm = ' '.join(mensagem_texto.lower().strip().split())[:300]
        content_key = f"{chat_num}|{texto_norm}"
        now = time.time()
        with _buffer_lock:
            # Limpar entradas antigas
            expired = [k for k, ts in _recent_by_content.items() if now - ts > DEDUP_WINDOW_SECONDS]
            for k in expired:
                del _recent_by_content[k]
            if content_key in _recent_by_content:
                print(f"[webhook] Conteúdo duplicado em janela de {DEDUP_WINDOW_SECONDS}s, ignorando", file=sys.stderr)
                return jsonify({"status": "ignored", "reason": "duplicate_content"}), 200
            _recent_by_content[content_key] = now

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
        mensagens = _message_buffers.pop(chat_id, [])
        ids = _message_ids.pop(chat_id, [])
        _buffer_timers.pop(chat_id, None)
        for mid in ids:
            _processed_ids.add(mid)
        if len(_processed_ids) > 500:
            _processed_ids.clear()

    if not mensagens:
        return

    mensagem_combinada = "\n".join(mensagens)
    print(f"[debounce] Processando {len(mensagens)} msg(s) de {chat_id}: {mensagem_combinada[:100]}...", file=sys.stderr)

    try:
        telefone = chat_id.split('@')[0] if '@' in chat_id else chat_id

        # Pedido de cardápio: enviar foto + link ANTES da IA (garante envio)
        txt_lower = mensagem_combinada.lower().strip()
        pediu_cardapio = any(p in txt_lower for p in ('cardapio', 'cardápio', 'menu'))
        if pediu_cardapio:
            from utils.whatsapp_sender import enviar_cardapio_foto, enviar_mensagem_texto
            cardapio_res = enviar_cardapio_foto(chat_id)
            if cardapio_res.get('success'):
                enviar_mensagem_texto(chat_id, "Pronto! Enviei o cardápio para você. 😊 Qualquer dúvida é só perguntar!")
                print(f"[debounce] Cardápio enviado diretamente para {chat_id}", file=sys.stderr)
                return
            else:
                print(f"[debounce] enviar_cardapio_foto falhou: {cardapio_res.get('erro')}", file=sys.stderr)
                # Mesmo falhando, não mandar lista - enviar mensagem de fallback
                from config import WEBHOOK_PUBLIC_URL
                url = (WEBHOOK_PUBLIC_URL or "https://pastelaobhoters.chatboot.cloud").rstrip('/')
                enviar_mensagem_texto(chat_id, f"Desculpe, tive um probleminha ao enviar a foto do cardápio. 😅\n\nVocê pode acessar nosso cardápio online aqui:\n🌐 {url}\n\nQualquer dúvida é só perguntar!")
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

        from utils.whatsapp_sender import enviar_mensagens_separadas

        if pix_data and pix_data.get("qr_code"):
            from utils.whatsapp_sender import enviar_pix_completo
            enviar_pix_completo(
                chat_id,
                pix_data["qr_code"],
                pix_data.get("valor_total", pix_data.get("pedido_id", 0)),
                pix_data.get("pedido_id", 0)
            )
        elif cartao_data and cartao_data.get("link_pagamento"):
            from utils.whatsapp_sender import enviar_link_cartao
            enviar_link_cartao(
                chat_id,
                cartao_data["link_pagamento"],
                cartao_data.get("valor_total", 0),
                cartao_data.get("pedido_id", 0)
            )
        elif resposta:
            enviar_mensagens_separadas(chat_id, resposta)

        print(f"[debounce] Resposta enviada para {chat_id}", file=sys.stderr)

    except Exception as e:
        print(f"[debounce] Erro ao processar buffer de {chat_id}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        try:
            from utils.whatsapp_sender import enviar_mensagem_texto
            enviar_mensagem_texto(chat_id, "Desculpe, tive um probleminha. Pode repetir?")
        except Exception:
            pass


# =====================================================================
# WEBHOOK MERCADO PAGO - Confirmação automática de pagamento
# =====================================================================

@whatsapp_bp.route('/api/mercadopago/webhook', methods=['POST'])
def webhook_mercadopago():
    """
    Recebe notificações do Mercado Pago quando um pagamento muda de status.
    Quando aprovado, atualiza o pedido e envia confirmação no WhatsApp.
    """
    try:
        data = request.json or {}
        query_type = request.args.get('type', data.get('type', ''))
        query_data_id = request.args.get('data.id', '')

        print(f"[mercadopago] Webhook recebido: type={query_type}, data={json.dumps(data)[:200]}", file=sys.stderr)

        if query_type == 'payment' or data.get('action') == 'payment.updated':
            payment_id = query_data_id or data.get('data', {}).get('id')
            if not payment_id:
                return jsonify({"status": "ok"}), 200

            import subprocess, os
            script_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'Mercado pago', 'api-mercadopago.py'
            )

            result = subprocess.run(
                [sys.executable, script_path],
                input=json.dumps({"action": "verificar_status", "payment_id": str(payment_id)}),
                text=True, capture_output=True, timeout=15
            )

            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                mp_data = json.loads(lines[-1])

                if mp_data.get('success') and mp_data.get('status') == 'approved':
                    external_ref = mp_data.get('external_reference', '')
                    print(f"[mercadopago] Pagamento APROVADO! Ref: {external_ref}, PaymentID: {payment_id}", file=sys.stderr)

                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor(dictionary=True)

                        pedido = None

                        cursor.execute(
                            "SELECT id, cliente_id, total, status, observacoes FROM pedidos WHERE preference_id = %s ORDER BY id DESC LIMIT 1",
                            (str(payment_id),)
                        )
                        pedido = cursor.fetchone()
                        if pedido:
                            print(f"[mercadopago] Pedido encontrado por preference_id: #{pedido['id']}", file=sys.stderr)

                        if not pedido and external_ref:
                            match = re.match(r'PEDIDO_(\d+)_', external_ref)
                            if match:
                                ref_pedido_id = int(match.group(1))
                                cursor.execute(
                                    "SELECT id, cliente_id, total, status, observacoes FROM pedidos WHERE id = %s LIMIT 1",
                                    (ref_pedido_id,)
                                )
                                pedido = cursor.fetchone()
                                if pedido:
                                    print(f"[mercadopago] Pedido encontrado por external_reference: #{pedido['id']}", file=sys.stderr)
                                    cursor.execute(
                                        "UPDATE pedidos SET preference_id = %s WHERE id = %s",
                                        (str(payment_id), pedido['id'])
                                    )
                                    conn.commit()

                        if not pedido:
                            print(f"[mercadopago] ERRO: Nenhum pedido encontrado para payment_id={payment_id}, ref={external_ref}", file=sys.stderr)

                        if pedido and pedido['status'] not in ('pago', 'preparando', 'pronto', 'entregue'):
                            cursor.execute(
                                "UPDATE pedidos SET status = 'pago' WHERE id = %s",
                                (pedido['id'],)
                            )
                            conn.commit()
                            print(f"[mercadopago] Pedido #{pedido['id']} atualizado para PAGO", file=sys.stderr)

                            whatsapp_id = None
                            try:
                                obs = json.loads(pedido['observacoes']) if pedido['observacoes'] else {}
                                whatsapp_id = obs.get('whatsapp_id')
                            except (json.JSONDecodeError, TypeError):
                                pass

                            if whatsapp_id:
                                cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (pedido['cliente_id'],))
                                cliente = cursor.fetchone()
                                nome = cliente['nome'] if cliente else 'cliente'

                                from utils.whatsapp_sender import enviar_mensagem_texto
                                msg = (
                                    f"Pagamento confirmado! *Pedido #{pedido['id']}* pago com sucesso.\n\n"
                                    f"Obrigado(a), *{nome}*! Seu pedido já está sendo preparado.\n\n"
                                    f"Assim que ficar pronto, te aviso! "
                                )
                                enviar_mensagem_texto(whatsapp_id, msg)
                                print(f"[mercadopago] Confirmação enviada para {whatsapp_id}", file=sys.stderr)
                            else:
                                print(f"[mercadopago] whatsapp_id não encontrado nas observações do pedido #{pedido['id']}", file=sys.stderr)

                        cursor.close()
                        conn.close()

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
