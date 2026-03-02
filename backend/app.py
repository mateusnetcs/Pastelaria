from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import bcrypt
import json
import subprocess
import os
import sys
import logging
from datetime import datetime, timedelta
import uuid
from functools import wraps

from config import DB_CONFIG, FLASK_SECRET_KEY, ALLOWED_ORIGINS, FLASK_DEBUG
from routes.whatsapp import whatsapp_bp
from routes.vapi import vapi_bp

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

admin_tokens = {}

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
UPLOAD_DIR = os.path.join(FRONTEND_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
app.secret_key = FLASK_SECRET_KEY
CORS(app, 
     supports_credentials=True,
     resources={r"/api/*": {"origins": ALLOWED_ORIGINS}},
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

app.register_blueprint(whatsapp_bp)
app.register_blueprint(vapi_bp)


@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/<path:filename>')
def serve_frontend(filename):
    filepath = os.path.join(FRONTEND_DIR, filename)
    if os.path.isfile(filepath):
        return send_from_directory(FRONTEND_DIR, filename)
    return send_from_directory(FRONTEND_DIR, 'index.html')


def get_db_connection():
    """Cria conexão com o banco de dados"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
        return None

# ==================== AUTENTICAÇÃO ====================

@app.route('/api/register', methods=['POST'])
def register():
    """Registra novo usuário"""
    try:
        data = request.json
        nome = data.get('nome')
        email = data.get('email')
        senha = data.get('senha')
        telefone = data.get('telefone', '')
        
        if not nome or not email or not senha:
            return jsonify({'success': False, 'error': 'Campos obrigatórios faltando'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor()
        
        # Verificar se email já existe
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Email já cadastrado'}), 400
        
        # Hash da senha
        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Inserir usuário
        cursor.execute("""
            INSERT INTO usuarios (nome, email, senha, telefone, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (nome, email, senha_hash, telefone))
        
        conn.commit()
        user_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        # Criar sessão
        session['user_id'] = user_id
        session['user_nome'] = nome
        session['user_email'] = email
        
        return jsonify({
            'success': True,
            'user': {
                'id': user_id,
                'nome': nome,
                'email': email
            }
        }), 201
        
    except Exception as e:
        logging.exception("Erro no registro")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Login do usuário"""
    try:
        data = request.json
        email = data.get('email')
        senha = data.get('senha')
        
        if not email or not senha:
            return jsonify({'success': False, 'error': 'Email e senha são obrigatórios'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nome, email, senha FROM usuarios WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not user:
            return jsonify({'success': False, 'error': 'Email ou senha incorretos'}), 401
        
        # Verificar senha
        if not bcrypt.checkpw(senha.encode('utf-8'), user['senha'].encode('utf-8')):
            return jsonify({'success': False, 'error': 'Email ou senha incorretos'}), 401
        
        # Criar sessão
        session['user_id'] = user['id']
        session['user_nome'] = user['nome']
        session['user_email'] = user['email']
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'nome': user['nome'],
                'email': user['email']
            }
        }), 200
        
    except Exception as e:
        logging.exception("Erro no login")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout do usuário"""
    session.clear()
    return jsonify({'success': True}), 200

@app.route('/api/user', methods=['GET'])
def get_user():
    """Retorna dados do usuário logado"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    return jsonify({
        'success': True,
        'user': {
            'id': session['user_id'],
            'nome': session['user_nome'],
            'email': session['user_email']
        }
    }), 200

@app.route('/api/me', methods=['GET'])
def get_me():
    if 'user_id' not in session:
        return jsonify({'success': False}), 401
    return jsonify({
        'success': True,
        'user': {
            'id': session['user_id'],
            'nome': session.get('user_nome', ''),
            'email': session.get('user_email', '')
        }
    }), 200






# ==================== PRODUTOS ====================

@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    """Retorna todos os produtos ativos"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nome, descricao, preco, quantidade, categoria, tipo, imagem_url
            FROM produtos
            WHERE ativo = TRUE
            ORDER BY categoria, nome
        """)
        
        produtos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'produtos': produtos}), 200
        
    except Exception as e:
        logging.exception("Erro ao buscar produtos")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

# ==================== PEDIDOS ====================

@app.route('/api/pedido', methods=['POST'])
def criar_pedido():
    """Cria um novo pedido e gera link de pagamento"""
    try:
        # Pegar dados da requisição
        data = request.json
        
        # Verificar autenticação - se não tiver sessão, tentar criar usuário temporário
        user_id = None
        cliente_email = None
        cliente_nome = None
        
        if 'user_id' in session:
            user_id = session['user_id']
        else:
            # Se não tem sessão, verificar se veio dados do cliente
            cliente_email = data.get('cliente_email') or data.get('email')
            cliente_nome = data.get('cliente_nome') or data.get('nome', 'Cliente')
            
            # Tentar criar ou buscar usuário temporário
            if cliente_email:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor(dictionary=True)
                    # Buscar usuário existente
                    cursor.execute("SELECT id FROM usuarios WHERE email = %s", (cliente_email,))
                    usuario = cursor.fetchone()
                    
                    if usuario:
                        user_id = usuario['id']
                        session['user_id'] = user_id
                    else:
                        # Criar usuário temporário
                        cursor.execute("""
                            INSERT INTO usuarios (nome, email, telefone, created_at)
                            VALUES (%s, %s, %s, NOW())
                        """, (cliente_nome, cliente_email, data.get('telefone', '')))
                        conn.commit()
                        user_id = cursor.lastrowid
                        session['user_id'] = user_id
                        session['user_nome'] = cliente_nome
                        session['user_email'] = cliente_email
                    
                    cursor.close()
                    conn.close()
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Não autenticado. Faça login ou forneça email.'}), 401
        itens = data.get('itens', [])
        endereco_entrega = data.get('endereco_entrega', {}) or {}
        metodo_pagamento = data.get('metodo_pagamento', 'pix')  # pix, dinheiro, cartao
        valor_recebido = data.get('valor_recebido')  # Para dinheiro
        
        if not itens:
            return jsonify({'success': False, 'error': 'Carrinho vazio'}), 400
        
        # Garantir que endereco_entrega é um dicionário
        if not isinstance(endereco_entrega, dict):
            endereco_entrega = {}
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Calcular total
        total = 0
        items_descricao = []
        
        for item in itens:
            produto_id = item.get('produto_id')
            quantidade = item.get('quantidade', 1)
            
            cursor.execute("SELECT nome, preco FROM produtos WHERE id = %s", (produto_id,))
            produto = cursor.fetchone()
            
            if not produto:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': f'Produto {produto_id} não encontrado'}), 400
            
            subtotal = float(produto['preco']) * quantidade
            total += subtotal
            items_descricao.append(f"{produto['nome']} x{quantidade}")
        
        # Determinar status inicial baseado no método de pagamento
        status_inicial = 'pendente'
        # Garantir que observacoes_dict é um dicionário válido
        observacoes_dict = dict(endereco_entrega) if endereco_entrega else {}
        
        # Buscar WhatsApp ID do cliente (se disponível)
        whatsapp_id = data.get('whatsapp_id')
        if not whatsapp_id:
            # Tentar buscar do telefone do cliente
            cursor.execute("SELECT telefone FROM usuarios WHERE id = %s", (user_id,))
            cliente_telefone = cursor.fetchone()
            if cliente_telefone and cliente_telefone.get('telefone'):
                telefone_limpo = ''.join(filter(str.isdigit, cliente_telefone['telefone']))
                if telefone_limpo:
                    if telefone_limpo.startswith('55'):
                        whatsapp_id = f"{telefone_limpo}@c.us"
                    else:
                        whatsapp_id = f"55{telefone_limpo}@c.us"
        
        # Adicionar WhatsApp ID nas observações
        if whatsapp_id:
            observacoes_dict['whatsapp_id'] = whatsapp_id
        
        if metodo_pagamento == 'dinheiro':
            status_inicial = 'pago'  # Pagamento em dinheiro é considerado pago
            if valor_recebido:
                observacoes_dict['metodo_pagamento'] = 'dinheiro'
                observacoes_dict['valor_recebido'] = valor_recebido
                observacoes_dict['troco'] = valor_recebido - total
        
        # Criar pedido no banco
        cursor.execute("""
            INSERT INTO pedidos (cliente_id, total, status, observacoes, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (user_id, total, status_inicial, json.dumps(observacoes_dict)))
        
        pedido_id = cursor.lastrowid
        
        # Inserir itens do pedido
        for item in itens:
            produto_id = item.get('produto_id')
            quantidade = item.get('quantidade', 1)
            
            cursor.execute("SELECT preco FROM produtos WHERE id = %s", (produto_id,))
            produto = cursor.fetchone()
            preco_unitario = float(produto['preco'])
            subtotal = preco_unitario * quantidade
            
            cursor.execute("""
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (pedido_id, produto_id, quantidade, preco_unitario, subtotal))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Enviar notificação no WhatsApp (se tiver WhatsApp ID)
        if whatsapp_id:
            try:
                from utils.whatsapp_sender import enviar_notificacao_pedido_criado
                enviar_notificacao_pedido_criado(whatsapp_id, pedido_id, total, items_descricao)
            except Exception as e:
                print(f"Erro ao enviar notificação WhatsApp: {e}", file=sys.stderr)
                # Não falhar o pedido se WhatsApp falhar
        
        # Se pagamento em dinheiro, retornar sucesso direto
        if metodo_pagamento == 'dinheiro':
            return jsonify({
                'success': True,
                'pedido_id': pedido_id,
                'total': total,
                'metodo_pagamento': 'dinheiro',
                'status': 'pago'
            }), 200
        
        # Construir endereço completo para exibição
        endereco_completo = endereco_entrega.get('rua', '')
        if endereco_entrega.get('numero'):
            endereco_completo += f", {endereco_entrega.get('numero')}"
        if endereco_entrega.get('complemento'):
            endereco_completo += f" - {endereco_entrega.get('complemento')}"
        if endereco_entrega.get('bairro'):
            endereco_completo += f", {endereco_entrega.get('bairro')}"
        if endereco_entrega.get('outro'):
            endereco_completo += f" ({endereco_entrega.get('outro')})"
        
        # Gerar link de pagamento via Mercado Pago
        # Pegar dados do cliente (da sessão ou dos dados recebidos)
        cliente_nome_final = session.get('user_nome') or cliente_nome or 'Cliente'
        cliente_email_final = session.get('user_email') or cliente_email or ''
        
        dados_cliente = {
            'nome': cliente_nome_final,
            'email': cliente_email_final,
            'telefone': endereco_entrega.get('telefone', ''),
            'endereco': endereco_completo,
            'rua': endereco_entrega.get('rua', ''),
            'numero': endereco_entrega.get('numero', ''),
            'complemento': endereco_entrega.get('complemento', ''),
            'bairro': endereco_entrega.get('bairro', ''),
            'outro': endereco_entrega.get('outro', '')
        }
        
        # Se for cartão, forçar preferência (não Pix direto)
        if metodo_pagamento == 'cartao':
            dados_cliente['forcar_preferencia'] = True
        
        # Chamar script Python do Mercado Pago
        script_path = os.path.join(os.path.dirname(__file__), 'Mercado pago', 'api-mercadopago.py')
        
        dados_pagamento = {
            'action': 'criar_pedido',
            'pedido_id': pedido_id,
            'valor_total': total,
            'itens': items_descricao,
            'dados_cliente': dados_cliente
        }
        
        try:
            result = subprocess.run(
                ['python', script_path],
                input=json.dumps(dados_pagamento),
                text=True,
                capture_output=True,
                timeout=30
            )
            
            # Log de debug
            if result.stderr:
                print(f"DEBUG Mercado Pago stderr: {result.stderr}", file=sys.stderr)
            
            if result.returncode == 0:
                # Tentar parsear o JSON da resposta
                try:
                    # Remover linhas vazias e pegar apenas a última linha (JSON)
                    stdout_lines = result.stdout.strip().split('\n')
                    json_line = stdout_lines[-1] if stdout_lines else result.stdout.strip()
                    
                    if not json_line:
                        raise ValueError("Resposta vazia do script Mercado Pago")
                    
                    resultado_mp = json.loads(json_line)
                    
                    if resultado_mp.get('success'):
                        resposta = {
                            'success': True,
                            'pedido_id': pedido_id,
                            'total': total
                        }
                        
                        # Se for cartão, sempre retornar link de pagamento
                        if metodo_pagamento == 'cartao':
                            resposta['link_pagamento'] = resultado_mp.get('init_point') or resultado_mp.get('link_pagamento')
                            resposta['preference_id'] = resultado_mp.get('id')
                            
                            # Salvar preference_id no banco
                            if resultado_mp.get('id'):
                                conn = get_db_connection()
                                if conn:
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        UPDATE pedidos 
                                        SET preference_id = %s
                                        WHERE id = %s
                                    """, (str(resultado_mp.get('id')), pedido_id))
                                    conn.commit()
                                    cursor.close()
                                    conn.close()
                            
                            return jsonify(resposta), 200
                        
                        # Se for pagamento Pix direto
                        if resultado_mp.get('payment_id'):
                            resposta['payment_id'] = resultado_mp.get('payment_id')
                            resposta['qr_code'] = resultado_mp.get('qr_code')
                            resposta['qr_code_base64'] = resultado_mp.get('qr_code_base64')
                            
                            # Salvar payment_id no banco
                            conn = get_db_connection()
                            if conn:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    UPDATE pedidos 
                                    SET preference_id = %s
                                    WHERE id = %s
                                """, (str(resultado_mp.get('payment_id')), pedido_id))
                                conn.commit()
                                cursor.close()
                                conn.close()
                            
                            # Enviar QR Code PIX no WhatsApp (se tiver WhatsApp ID)
                            if whatsapp_id and resultado_mp.get('qr_code_base64'):
                                try:
                                    from utils.whatsapp_sender import enviar_qr_code_pix
                                    enviar_qr_code_pix(
                                        whatsapp_id,
                                        resultado_mp.get('qr_code_base64'),
                                        total,
                                        pedido_id
                                    )
                                except Exception as e:
                                    print(f"Erro ao enviar QR Code WhatsApp: {e}", file=sys.stderr)
                                    # Não falhar o pedido se WhatsApp falhar
                        # Se for preferência (fallback)
                        else:
                            resposta['link_pagamento'] = resultado_mp.get('init_point')
                            resposta['preference_id'] = resultado_mp.get('id')
                            # Adicionar QR code se disponível na preferência
                            if resultado_mp.get('qr_code'):
                                resposta['qr_code'] = resultado_mp.get('qr_code')
                            if resultado_mp.get('qr_code_base64'):
                                resposta['qr_code_base64'] = resultado_mp.get('qr_code_base64')
                            
                            # Salvar preference_id no banco
                            if resultado_mp.get('id'):
                                conn = get_db_connection()
                                if conn:
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        UPDATE pedidos 
                                        SET preference_id = %s
                                        WHERE id = %s
                                    """, (str(resultado_mp.get('id')), pedido_id))
                                    conn.commit()
                                    cursor.close()
                                    conn.close()
                            
                            # Enviar QR Code PIX no WhatsApp (se tiver WhatsApp ID e QR Code)
                            if whatsapp_id and resultado_mp.get('qr_code_base64'):
                                try:
                                    from utils.whatsapp_sender import enviar_qr_code_pix
                                    enviar_qr_code_pix(
                                        whatsapp_id,
                                        resultado_mp.get('qr_code_base64'),
                                        total,
                                        pedido_id
                                    )
                                except Exception as e:
                                    print(f"Erro ao enviar QR Code WhatsApp: {e}", file=sys.stderr)
                                    # Não falhar o pedido se WhatsApp falhar
                        
                        return jsonify(resposta), 200
                    else:
                        error_msg = resultado_mp.get('error', 'Erro ao gerar link de pagamento')
                        # Adicionar detalhes se disponíveis
                        if resultado_mp.get('details'):
                            error_msg += f" - Detalhes: {str(resultado_mp.get('details'))}"
                        
                        print(f"ERRO Mercado Pago: {error_msg}", file=sys.stderr)
                        return jsonify({
                            'success': False,
                            'error': error_msg
                        }), 500
                except json.JSONDecodeError as e:
                    print(f"ERRO ao parsear JSON do Mercado Pago: {e}", file=sys.stderr)
                    print(f"STDOUT recebido: {result.stdout}", file=sys.stderr)
                    return jsonify({
                        'success': False,
                        'error': f'Erro ao processar resposta do pagamento: {str(e)}'
                    }), 500
            else:
                error_msg = f'Erro ao executar script de pagamento (código {result.returncode})'
                if result.stderr:
                    error_msg += f': {result.stderr[:200]}'
                print(f"ERRO subprocess: {error_msg}", file=sys.stderr)
                return jsonify({
                    'success': False,
                    'error': error_msg
                }), 500
                
        except subprocess.TimeoutExpired:
            return jsonify({
                'success': False,
                'error': 'Timeout ao gerar link de pagamento. Tente novamente.'
            }), 500
        except Exception as e:
            print(f"ERRO exceção ao gerar pagamento: {str(e)}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Erro ao gerar pagamento: {str(e)}'
            }), 500
        
    except Exception as e:
        logging.exception("Erro ao criar pedido")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@app.route('/api/pedidos', methods=['GET'])
def get_pedidos():
    """Retorna todos os pedidos do usuário logado"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Não autenticado'}), 401
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, total, status, observacoes, created_at, updated_at
            FROM pedidos
            WHERE cliente_id = %s
            ORDER BY created_at DESC
            LIMIT 20
        """, (session['user_id'],))
        
        pedidos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'pedidos': pedidos
        }), 200
        
    except Exception as e:
        logging.exception("Erro ao buscar pedidos")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@app.route('/api/pedido/<int:pedido_id>/pagar', methods=['POST'])
def reativar_pagamento_pedido(pedido_id):
    """Reativa pagamento de um pedido pendente, gerando novo QR code"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Não autenticado'}), 401
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Verificar se pedido existe e pertence ao usuário
        cursor.execute("""
            SELECT p.*, u.nome, u.email, u.telefone
            FROM pedidos p
            JOIN usuarios u ON p.cliente_id = u.id
            WHERE p.id = %s AND p.cliente_id = %s AND p.status = 'pendente'
        """, (pedido_id, session['user_id']))
        
        pedido = cursor.fetchone()
        
        if not pedido:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Pedido não encontrado ou já foi pago'}), 404
        
        # Buscar itens do pedido
        cursor.execute("""
            SELECT pi.*, pr.nome as produto_nome
            FROM pedido_itens pi
            JOIN produtos pr ON pi.produto_id = pr.id
            WHERE pi.pedido_id = %s
        """, (pedido_id,))
        
        itens_db = cursor.fetchall()
        items_descricao = [f"{item['produto_nome']} x{item['quantidade']}" for item in itens_db]
        
        # Construir dados do cliente
        endereco_entrega = {}
        try:
            if pedido.get('observacoes'):
                endereco_entrega = json.loads(pedido['observacoes']) if isinstance(pedido['observacoes'], str) else pedido['observacoes']
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        
        dados_cliente = {
            'nome': pedido['nome'],
            'email': pedido['email'],
            'telefone': pedido.get('telefone', ''),
            'rua': endereco_entrega.get('rua', ''),
            'numero': endereco_entrega.get('numero', ''),
            'complemento': endereco_entrega.get('complemento', ''),
            'bairro': endereco_entrega.get('bairro', ''),
            'outro': endereco_entrega.get('outro', '')
        }
        
        cursor.close()
        conn.close()
        
        # Gerar novo pagamento
        script_path = os.path.join(os.path.dirname(__file__), 'Mercado pago', 'api-mercadopago.py')
        dados_pagamento = {
            'action': 'criar_pedido',
            'pedido_id': pedido_id,
            'valor_total': float(pedido['total']),
            'itens': items_descricao,
            'dados_cliente': dados_cliente
        }
        
        result = subprocess.run(
            [sys.executable, script_path],
            input=json.dumps(dados_pagamento),
            text=True,
            capture_output=True,
            timeout=30
        )
        
        if result.returncode == 0:
            stdout_lines = result.stdout.strip().split('\n')
            json_line = stdout_lines[-1] if stdout_lines else result.stdout.strip()
            
            if json_line:
                resultado_mp = json.loads(json_line)
                
                if resultado_mp.get('success'):
                    resposta = {
                        'success': True,
                        'pedido_id': pedido_id,
                        'total': pedido['total']
                    }
                    
                    # Se for pagamento Pix direto
                    if resultado_mp.get('payment_id'):
                        resposta['payment_id'] = resultado_mp.get('payment_id')
                        resposta['qr_code'] = resultado_mp.get('qr_code')
                        resposta['qr_code_base64'] = resultado_mp.get('qr_code_base64')
                        
                        # Atualizar preference_id no banco
                        conn = get_db_connection()
                        if conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE pedidos 
                                SET preference_id = %s
                                WHERE id = %s
                            """, (str(resultado_mp.get('payment_id')), pedido_id))
                            conn.commit()
                            cursor.close()
                            conn.close()
                    else:
                        resposta['link_pagamento'] = resultado_mp.get('init_point')
                        resposta['preference_id'] = resultado_mp.get('id')
                        if resultado_mp.get('qr_code'):
                            resposta['qr_code'] = resultado_mp.get('qr_code')
                        if resultado_mp.get('qr_code_base64'):
                            resposta['qr_code_base64'] = resultado_mp.get('qr_code_base64')
                        
                        # Atualizar preference_id no banco
                        if resultado_mp.get('id'):
                            conn = get_db_connection()
                            if conn:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    UPDATE pedidos 
                                    SET preference_id = %s
                                    WHERE id = %s
                                """, (str(resultado_mp.get('id')), pedido_id))
                                conn.commit()
                                cursor.close()
                                conn.close()
                    
                    return jsonify(resposta), 200
                else:
                    return jsonify({
                        'success': False,
                        'error': resultado_mp.get('error', 'Erro ao gerar pagamento')
                    }), 500
        
        return jsonify({
            'success': False,
            'error': 'Erro ao gerar pagamento'
        }), 500
        
    except Exception as e:
        logging.exception("Erro ao reativar pagamento")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@app.route('/api/pedido/<int:pedido_id>/cancelar', methods=['POST'])
def cancelar_pedido(pedido_id):
    """Exclui um pedido do banco de dados"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Não autenticado'}), 401
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Verificar se pedido existe e pertence ao usuário
        cursor.execute("""
            SELECT id, status
            FROM pedidos
            WHERE id = %s AND cliente_id = %s
        """, (pedido_id, session['user_id']))
        
        pedido = cursor.fetchone()
        
        if not pedido:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Pedido não encontrado'}), 404
        
        # Excluir itens do pedido primeiro (devido à foreign key)
        cursor.execute("""
            DELETE FROM pedido_itens 
            WHERE pedido_id = %s
        """, (pedido_id,))
        
        # Excluir o pedido
        cursor.execute("""
            DELETE FROM pedidos 
            WHERE id = %s
        """, (pedido_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Pedido excluído com sucesso'
        }), 200
        
    except Exception as e:
        logging.exception("Erro ao excluir pedido")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@app.route('/api/pedido/<int:pedido_id>/status', methods=['GET'])
def get_pedido_status(pedido_id):
    """Verifica status do pagamento de um pedido"""
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Não autenticado'}), 401
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT status, observacoes, preference_id
            FROM pedidos
            WHERE id = %s AND cliente_id = %s
        """, (pedido_id, session['user_id']))
        
        pedido = cursor.fetchone()
        
        if not pedido:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Pedido não encontrado'}), 404
        
        # Se já está pago, retornar direto
        if pedido['status'] == 'pago' or pedido['status'] == 'aprovado':
            cursor.close()
            conn.close()
            return jsonify({
                'success': True,
                'status': 'pago',
                'aprovado': True
            }), 200
        
        # Se tem preference_id (payment_id), verificar no Mercado Pago
        if pedido.get('preference_id'):
            try:
                import subprocess
                import json as json_lib
                
                script_path = os.path.join(os.path.dirname(__file__), 'Mercado pago', 'api-mercadopago.py')
                dados = {
                    'action': 'verificar_status',
                    'payment_id': pedido['preference_id']
                }
                
                result = subprocess.run(
                    [sys.executable, script_path],
                    input=json_lib.dumps(dados),
                    text=True,
                    capture_output=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    stdout_lines = result.stdout.strip().split('\n')
                    json_line = stdout_lines[-1] if stdout_lines else result.stdout.strip()
                    if json_line:
                        mp_status = json_lib.loads(json_line)
                        if mp_status.get('success'):
                            novo_status_mp = mp_status.get('status', '').lower()
                            
                            # Se pagamento foi aprovado, atualizar no banco
                            if novo_status_mp == 'approved' or novo_status_mp == 'aprovado':
                                cursor.execute("""
                                    UPDATE pedidos 
                                    SET status = 'pago' 
                                    WHERE id = %s
                                """, (pedido_id,))
                                conn.commit()
                                
                                cursor.close()
                                conn.close()
                                return jsonify({
                                    'success': True,
                                    'status': 'pago',
                                    'aprovado': True,
                                    'message': 'Pagamento aprovado!'
                                }), 200
                            elif novo_status_mp == 'pending' or novo_status_mp == 'pendente':
                                cursor.close()
                                conn.close()
                                return jsonify({
                                    'success': True,
                                    'status': 'pendente',
                                    'aprovado': False,
                                    'message': 'Aguardando pagamento...'
                                }), 200
                            elif novo_status_mp == 'rejected' or novo_status_mp == 'rejeitado':
                                cursor.close()
                                conn.close()
                                return jsonify({
                                    'success': True,
                                    'status': 'rejeitado',
                                    'aprovado': False,
                                    'message': 'Pagamento rejeitado'
                                }), 200
            except Exception as e:
                print(f"Erro ao verificar status no MP: {e}", file=sys.stderr)
                # Continuar e retornar status do banco
        
        # Retornar status do banco
        cursor.close()
        conn.close()
        return jsonify({
            'success': True,
            'status': pedido['status'],
            'aprovado': pedido['status'] == 'pago',
            'observacoes': pedido.get('observacoes', '')
        }), 200
        
    except Exception as e:
        logging.exception("Erro ao verificar status do pedido")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

# ==================== ADMIN AUTH ====================

def gerar_token_admin(user_id):
    """Gera um token simples para autenticação admin."""
    token = uuid.uuid4().hex + uuid.uuid4().hex
    admin_tokens[token] = {
        'user_id': user_id,
        'criado_em': datetime.now(),
        'expira_em': datetime.now() + timedelta(hours=12)
    }
    for t in list(admin_tokens.keys()):
        if admin_tokens[t]['expira_em'] < datetime.now():
            del admin_tokens[t]
    return token


def admin_required(f):
    """Decorador que exige autenticação admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''

        if not token or token not in admin_tokens:
            return jsonify({'success': False, 'error': 'Não autenticado'}), 401

        info = admin_tokens[token]
        if info['expira_em'] < datetime.now():
            del admin_tokens[token]
            return jsonify({'success': False, 'error': 'Sessão expirada'}), 401

        request.admin_user_id = info['user_id']
        return f(*args, **kwargs)
    return decorated


@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Login do administrador."""
    try:
        data = request.json
        email = (data.get('email') or '').strip().lower()
        senha = data.get('senha') or ''

        if not email or not senha:
            return jsonify({'success': False, 'error': 'Email e senha são obrigatórios'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, nome, email, senha, is_admin FROM usuarios WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            return jsonify({'success': False, 'error': 'Email ou senha incorretos'}), 401

        if not user.get('is_admin'):
            return jsonify({'success': False, 'error': 'Acesso restrito a administradores'}), 403

        if not user.get('senha'):
            return jsonify({'success': False, 'error': 'Usuário sem senha configurada'}), 401

        if not bcrypt.checkpw(senha.encode('utf-8'), user['senha'].encode('utf-8')):
            return jsonify({'success': False, 'error': 'Email ou senha incorretos'}), 401

        token = gerar_token_admin(user['id'])

        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': user['id'],
                'nome': user['nome'],
                'email': user['email']
            }
        }), 200

    except Exception as e:
        print(f"[admin] Erro no login: {e}", file=sys.stderr)
        return jsonify({'success': False, 'error': 'Erro interno'}), 500


@app.route('/api/admin/me', methods=['GET'])
@admin_required
def admin_me():
    """Retorna dados do admin autenticado."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nome, email FROM usuarios WHERE id = %s", (request.admin_user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            return jsonify({'success': False, 'error': 'Usuário não encontrado'}), 404

        return jsonify({'success': True, 'user': user}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    """Logout do admin."""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    if token in admin_tokens:
        del admin_tokens[token]
    return jsonify({'success': True}), 200


# ==================== ADMIN ====================

# --- CRUD CLIENTES ---

@app.route('/api/admin/clientes', methods=['GET'])
@admin_required
def admin_listar_clientes():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro DB'}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.id, u.nome, u.email, u.telefone, u.data_nascimento, u.created_at,
                   COUNT(p.id) as total_pedidos,
                   COALESCE(SUM(p.total), 0) as total_gasto
            FROM usuarios u
            LEFT JOIN pedidos p ON u.id = p.cliente_id
            WHERE u.is_admin = FALSE OR u.is_admin IS NULL
            GROUP BY u.id
            ORDER BY u.nome ASC
        """)
        clientes = cursor.fetchall()
        for c in clientes:
            c['total_gasto'] = float(c['total_gasto'])
            if c.get('data_nascimento') and hasattr(c['data_nascimento'], 'isoformat'):
                c['data_nascimento'] = c['data_nascimento'].isoformat()
            if c.get('created_at') and hasattr(c['created_at'], 'isoformat'):
                c['created_at'] = c['created_at'].isoformat()
        cursor.close(); conn.close()
        return jsonify({'success': True, 'clientes': clientes}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/admin/cliente', methods=['POST'])
@admin_required
def admin_criar_cliente():
    try:
        data = request.json
        nome = data.get('nome', '').strip()
        email = data.get('email', '').strip()
        telefone = data.get('telefone', '').strip()
        data_nascimento = data.get('data_nascimento', '').strip() or None
        senha = data.get('senha', '').strip()

        if not nome or not email:
            return jsonify({'success': False, 'error': 'Nome e email são obrigatórios'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro DB'}), 500
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close(); conn.close()
            return jsonify({'success': False, 'error': 'Email já cadastrado'}), 400

        if not senha:
            import random, string
            senha = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        telefone_limpo = ''.join(filter(str.isdigit, telefone)) if telefone else ''

        cursor.execute("""
            INSERT INTO usuarios (nome, email, senha, telefone, data_nascimento, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (nome, email, senha_hash, telefone_limpo, data_nascimento))
        conn.commit()
        cliente_id = cursor.lastrowid
        cursor.close(); conn.close()

        return jsonify({'success': True, 'id': cliente_id, 'senha_gerada': senha}), 201
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/admin/cliente/<int:cliente_id>', methods=['GET'])
@admin_required
def admin_detalhe_cliente(cliente_id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro DB'}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nome, email, telefone, data_nascimento, created_at
            FROM usuarios WHERE id = %s
        """, (cliente_id,))
        cliente = cursor.fetchone()
        if not cliente:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'error': 'Cliente não encontrado'}), 404
        if cliente.get('data_nascimento') and hasattr(cliente['data_nascimento'], 'isoformat'):
            cliente['data_nascimento'] = cliente['data_nascimento'].isoformat()
        if cliente.get('created_at') and hasattr(cliente['created_at'], 'isoformat'):
            cliente['created_at'] = cliente['created_at'].isoformat()
        cursor.close(); conn.close()
        return jsonify({'success': True, 'cliente': cliente}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/admin/cliente/<int:cliente_id>', methods=['PUT'])
@admin_required
def admin_atualizar_cliente(cliente_id):
    try:
        data = request.json
        nome = data.get('nome', '').strip()
        email = data.get('email', '').strip()
        telefone = data.get('telefone', '').strip()
        data_nascimento = data.get('data_nascimento', '').strip() or None
        nova_senha = data.get('senha', '').strip()

        if not nome or not email:
            return jsonify({'success': False, 'error': 'Nome e email são obrigatórios'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro DB'}), 500
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM usuarios WHERE email = %s AND id != %s", (email, cliente_id))
        if cursor.fetchone():
            cursor.close(); conn.close()
            return jsonify({'success': False, 'error': 'Email já em uso por outro cliente'}), 400

        telefone_limpo = ''.join(filter(str.isdigit, telefone)) if telefone else ''

        if nova_senha:
            senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("""
                UPDATE usuarios SET nome=%s, email=%s, telefone=%s, data_nascimento=%s, senha=%s
                WHERE id=%s
            """, (nome, email, telefone_limpo, data_nascimento, senha_hash, cliente_id))
        else:
            cursor.execute("""
                UPDATE usuarios SET nome=%s, email=%s, telefone=%s, data_nascimento=%s
                WHERE id=%s
            """, (nome, email, telefone_limpo, data_nascimento, cliente_id))

        conn.commit()
        cursor.close(); conn.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/admin/cliente/<int:cliente_id>', methods=['DELETE'])
@admin_required
def admin_excluir_cliente(cliente_id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro DB'}), 500
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, is_admin FROM usuarios WHERE id = %s", (cliente_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'error': 'Cliente não encontrado'}), 404
        if user.get('is_admin'):
            cursor.close(); conn.close()
            return jsonify({'success': False, 'error': 'Não é possível excluir um admin'}), 403

        cursor.execute("DELETE FROM pedido_itens WHERE pedido_id IN (SELECT id FROM pedidos WHERE cliente_id = %s)", (cliente_id,))
        cursor.execute("DELETE FROM pedidos WHERE cliente_id = %s", (cliente_id,))
        cursor.execute("DELETE FROM conversas WHERE usuario_id = %s", (cliente_id,))
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (cliente_id,))
        conn.commit()
        cursor.close(); conn.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


# --- CRUD PRODUTOS ---

@app.route('/api/admin/produtos', methods=['GET'])
@admin_required
def admin_listar_produtos():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nome, descricao, preco, custo, quantidade, categoria, tipo, imagem_url, ativo, created_at, updated_at
            FROM produtos ORDER BY categoria, nome
        """)
        produtos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'produtos': produtos}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/admin/produto', methods=['POST'])
@admin_required
def admin_criar_produto():
    try:
        data = request.json
        nome = data.get('nome', '').strip()
        descricao = data.get('descricao', '').strip()
        preco = data.get('preco')
        custo = data.get('custo', 0)
        quantidade = data.get('quantidade', 0)
        categoria = data.get('categoria', '').strip()
        tipo = data.get('tipo', '').strip()
        imagem_url = data.get('imagem_url', '').strip()

        if not nome or not preco or not categoria or not tipo:
            return jsonify({'success': False, 'error': 'Nome, preço, categoria e tipo são obrigatórios'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO produtos (nome, descricao, preco, custo, quantidade, categoria, tipo, imagem_url, ativo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
        """, (nome, descricao, float(preco), float(custo or 0), int(quantidade), categoria, tipo, imagem_url or None))
        conn.commit()
        produto_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'id': produto_id, 'message': 'Produto criado com sucesso'}), 201
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/admin/produto/<int:produto_id>', methods=['PUT'])
@admin_required
def admin_editar_produto(produto_id):
    try:
        data = request.json
        nome = data.get('nome', '').strip()
        descricao = data.get('descricao', '').strip()
        preco = data.get('preco')
        custo = data.get('custo', 0)
        quantidade = data.get('quantidade', 0)
        categoria = data.get('categoria', '').strip()
        tipo = data.get('tipo', '').strip()
        imagem_url = data.get('imagem_url', '').strip()
        ativo = data.get('ativo', True)

        if not nome or not preco or not categoria or not tipo:
            return jsonify({'success': False, 'error': 'Nome, preço, categoria e tipo são obrigatórios'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE produtos SET nome=%s, descricao=%s, preco=%s, custo=%s, quantidade=%s, categoria=%s, tipo=%s, imagem_url=%s, ativo=%s
            WHERE id=%s
        """, (nome, descricao, float(preco), float(custo or 0), int(quantidade), categoria, tipo, imagem_url or None, bool(ativo), produto_id))
        conn.commit()
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Produto não encontrado'}), 404
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Produto atualizado com sucesso'}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/admin/produto/<int:produto_id>', methods=['DELETE'])
@admin_required
def admin_excluir_produto(produto_id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute("UPDATE produtos SET ativo = FALSE WHERE id = %s", (produto_id,))
        conn.commit()
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Produto não encontrado'}), 404
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Produto desativado com sucesso'}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/admin/produto/<int:produto_id>/restaurar', methods=['POST'])
@admin_required
def admin_restaurar_produto(produto_id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500
        cursor = conn.cursor()
        cursor.execute("UPDATE produtos SET ativo = TRUE WHERE id = %s", (produto_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Produto restaurado com sucesso'}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/admin/upload-imagem', methods=['POST'])
@admin_required
def admin_upload_imagem():
    try:
        if 'imagem' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhuma imagem enviada'}), 400

        arquivo = request.files['imagem']
        if not arquivo.filename:
            return jsonify({'success': False, 'error': 'Arquivo sem nome'}), 400

        ext = os.path.splitext(arquivo.filename)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
            return jsonify({'success': False, 'error': 'Formato inválido. Use JPG, PNG, WEBP ou GIF'}), 400

        nome_arquivo = f"{uuid.uuid4().hex}{ext}"
        caminho = os.path.join(UPLOAD_DIR, nome_arquivo)
        arquivo.save(caminho)

        url_imagem = f"/uploads/{nome_arquivo}"

        return jsonify({'success': True, 'url': url_imagem, 'filename': nome_arquivo}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


# --- PEDIDOS ADMIN ---

@app.route('/api/admin/pedidos', methods=['GET'])
@admin_required
def admin_listar_pedidos():
    """Lista todos os pedidos para o admin"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar todos os pedidos com informações do cliente
        cursor.execute("""
            SELECT 
                p.id,
                p.cliente_id,
                p.total,
                p.status,
                p.observacoes,
                p.created_at,
                u.nome as cliente_nome
            FROM pedidos p
            LEFT JOIN usuarios u ON p.cliente_id = u.id
            WHERE p.status != 'cancelado'
            ORDER BY p.created_at DESC
        """)
        
        pedidos = cursor.fetchall()
        
        print(f"[ADMIN] Total de pedidos encontrados: {len(pedidos)}", file=sys.stderr)
        
        # Buscar itens de cada pedido
        for pedido in pedidos:
            cursor.execute("""
                SELECT 
                    pi.quantidade,
                    pr.nome,
                    pi.preco_unitario
                FROM pedido_itens pi
                JOIN produtos pr ON pi.produto_id = pr.id
                WHERE pi.pedido_id = %s
            """, (pedido['id'],))
            
            itens = cursor.fetchall()
            itens_descricao = ', '.join([f"{item['nome']} x{item['quantidade']}" for item in itens])
            pedido['itens_descricao'] = itens_descricao
            print(f"[ADMIN] Pedido {pedido['id']}: Status={pedido['status']}, Cliente={pedido['cliente_nome']}", file=sys.stderr)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'pedidos': pedidos
        }), 200
        
    except Exception as e:
        logging.exception("Erro ao listar pedidos admin")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@app.route('/api/n8n/gerar-pix', methods=['POST'])
def n8n_gerar_pix():
    """Endpoint para n8n gerar Pix para um pedido já criado (protegido por API key)"""
    try:
        auth = request.headers.get('Authorization', '')
        expected_key = os.getenv('N8N_API_KEY', '')
        if not expected_key or auth != f'Bearer {expected_key}':
            return jsonify({'success': False, 'error': 'Não autorizado'}), 401

        data = request.json
        pedido_id = data.get('pedido_id')
        valor_total = data.get('valor_total')
        itens = data.get('itens', [])
        dados_cliente = data.get('dados_cliente', {})
        
        if not pedido_id or not valor_total:
            return jsonify({'success': False, 'error': 'pedido_id e valor_total são obrigatórios'}), 400
        
        # Criar descrição dos itens
        items_descricao = []
        if isinstance(itens, list):
            for item in itens:
                if isinstance(item, dict):
                    nome = item.get('nome', 'Produto')
                    quantidade = item.get('quantidade', 1)
                    items_descricao.append(f"{nome} x{quantidade}")
                else:
                    items_descricao.append(str(item))
        else:
            items_descricao = [str(itens)]
        
        # Chamar script Python do Mercado Pago
        script_path = os.path.join(os.path.dirname(__file__), 'Mercado pago', 'api-mercadopago.py')
        
        dados_pagamento = {
            'action': 'criar_pedido',
            'pedido_id': pedido_id,
            'valor_total': float(valor_total),
            'itens': items_descricao,
            'dados_cliente': dados_cliente
        }
        
        try:
            result = subprocess.run(
                ['python', script_path],
                input=json.dumps(dados_pagamento),
                text=True,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                stdout_lines = result.stdout.strip().split('\n')
                json_line = stdout_lines[-1] if stdout_lines else result.stdout.strip()
                
                if json_line:
                    resultado_mp = json.loads(json_line)
                    
                    if resultado_mp.get('success'):
                        resposta = {
                            'success': True,
                            'pedido_id': pedido_id,
                            'total': valor_total
                        }
                        
                        # Adicionar QR code se disponível
                        if resultado_mp.get('qr_code'):
                            resposta['qr_code'] = resultado_mp.get('qr_code')
                        if resultado_mp.get('qr_code_base64'):
                            resposta['qr_code_base64'] = resultado_mp.get('qr_code_base64')
                        if resultado_mp.get('payment_id'):
                            resposta['payment_id'] = resultado_mp.get('payment_id')
                        
                        # Adicionar link de pagamento (init_point) se disponível
                        if resultado_mp.get('init_point'):
                            resposta['link_pagamento'] = resultado_mp.get('init_point')
                        if resultado_mp.get('id'):
                            resposta['preference_id'] = resultado_mp.get('id')
                        
                        # Salvar payment_id no banco
                        if resultado_mp.get('payment_id'):
                            conn = get_db_connection()
                            if conn:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    UPDATE pedidos 
                                    SET preference_id = %s
                                    WHERE id = %s
                                """, (str(resultado_mp.get('payment_id')), pedido_id))
                                conn.commit()
                                cursor.close()
                                conn.close()
                        
                        return jsonify(resposta), 200
                    else:
                        return jsonify({
                            'success': False,
                            'error': resultado_mp.get('error', 'Erro ao gerar Pix')
                        }), 500
                else:
                    return jsonify({'success': False, 'error': 'Resposta vazia do Mercado Pago'}), 500
            else:
                error_msg = result.stderr or 'Erro desconhecido'
                print(f"Erro ao executar script Mercado Pago: {error_msg}", file=sys.stderr)
                return jsonify({'success': False, 'error': f'Erro ao gerar Pix: {error_msg}'}), 500
                
        except Exception as e:
            logging.exception("Erro interno")
            return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500
            
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@app.route('/api/admin/pedido/<int:pedido_id>/detalhes', methods=['GET'])
@admin_required
def admin_detalhes_pedido(pedido_id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro DB'}), 500
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT p.id, p.cliente_id, p.total, p.status, p.observacoes, p.created_at, p.updated_at,
                   u.nome as cliente_nome, u.email as cliente_email, u.telefone as cliente_telefone
            FROM pedidos p LEFT JOIN usuarios u ON p.cliente_id = u.id
            WHERE p.id = %s
        """, (pedido_id,))
        pedido = cursor.fetchone()
        if not pedido:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'error': 'Pedido não encontrado'}), 404

        cursor.execute("""
            SELECT pi.quantidade, pi.preco_unitario, pi.subtotal, pr.nome as produto_nome, pr.categoria
            FROM pedido_itens pi JOIN produtos pr ON pi.produto_id = pr.id
            WHERE pi.pedido_id = %s
        """, (pedido_id,))
        itens = cursor.fetchall()
        for it in itens:
            it['preco_unitario'] = float(it['preco_unitario'])
            it['subtotal'] = float(it['subtotal'])

        pedido['total'] = float(pedido['total'])
        if pedido.get('created_at') and hasattr(pedido['created_at'], 'isoformat'):
            pedido['created_at'] = pedido['created_at'].isoformat()
        if pedido.get('updated_at') and hasattr(pedido['updated_at'], 'isoformat'):
            pedido['updated_at'] = pedido['updated_at'].isoformat()

        cursor.close(); conn.close()
        return jsonify({'success': True, 'pedido': pedido, 'itens': itens}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/admin/pedido/<int:pedido_id>/imprimir', methods=['POST'])
@admin_required
def admin_imprimir_cupom(pedido_id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro DB'}), 500
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT p.id, p.total, p.status, p.observacoes, p.created_at,
                   u.nome as cliente_nome, u.telefone as cliente_telefone
            FROM pedidos p LEFT JOIN usuarios u ON p.cliente_id = u.id
            WHERE p.id = %s
        """, (pedido_id,))
        pedido = cursor.fetchone()
        if not pedido:
            cursor.close(); conn.close()
            return jsonify({'success': False, 'error': 'Pedido não encontrado'}), 404

        cursor.execute("""
            SELECT pi.quantidade, pi.preco_unitario, pi.subtotal, pr.nome as produto_nome
            FROM pedido_itens pi JOIN produtos pr ON pi.produto_id = pr.id
            WHERE pi.pedido_id = %s
        """, (pedido_id,))
        itens = cursor.fetchall()
        cursor.close(); conn.close()

        data_pedido = pedido['created_at'].strftime('%d/%m/%Y %H:%M') if pedido.get('created_at') else '-'

        obs_texto = ''
        if pedido.get('observacoes'):
            try:
                obs = json.loads(pedido['observacoes']) if isinstance(pedido['observacoes'], str) else pedido['observacoes']
                if isinstance(obs, dict):
                    tipo = obs.get('tipo_entrega', '')
                    if tipo == 'entrega' or obs.get('rua'):
                        rua = obs.get('rua', '')
                        numero = obs.get('numero', '')
                        bairro = obs.get('bairro', '')
                        compl = obs.get('complemento', '')
                        partes = ['ENTREGA']
                        if rua:
                            end_line = rua
                            if numero:
                                end_line += f', {numero}'
                            partes.append(end_line)
                        if bairro:
                            partes.append(bairro)
                        if compl:
                            partes.append(compl)
                        obs_texto = '\n'.join(partes)
                    elif tipo == 'retirada' or obs.get('retirada_local'):
                        obs_texto = 'RETIRADA NO LOCAL'
                else:
                    obs_texto = str(obs)
            except Exception:
                obs_texto = str(pedido['observacoes'])

        largura = 42
        linha = '-' * largura

        cupom = []
        cupom.append('PASTELAO BROTHERS'.center(largura))
        cupom.append('Cupom Nao Fiscal'.center(largura))
        cupom.append(linha)
        cupom.append(f'Data: {data_pedido}')
        cupom.append(f'Pedido: #{pedido["id"]}')
        cupom.append(f'Cliente: {pedido.get("cliente_nome", "N/A")}')
        tel = pedido.get('cliente_telefone', 'N/A') or 'N/A'
        tel_limpo = ''.join(filter(str.isdigit, tel))
        if len(tel_limpo) >= 12 and tel_limpo.startswith('55'):
            tel_limpo = tel_limpo[2:]
        if len(tel_limpo) == 11:
            tel = f'({tel_limpo[:2]}) {tel_limpo[2:7]}-{tel_limpo[7:]}'
        elif len(tel_limpo) == 10:
            tel = f'({tel_limpo[:2]}) {tel_limpo[2:6]}-{tel_limpo[6:]}'
        cupom.append(f'Tel: {tel}')
        cupom.append(linha)

        cupom.append(f'{"Item":<22} {"Qtd":>3} {"Unit":>7} {"Subt":>7}')
        cupom.append(linha)
        for it in itens:
            nome = it['produto_nome'][:22].ljust(22)
            qtd = str(it['quantidade']).rjust(3)
            unit = f"{float(it['preco_unitario']):.2f}".rjust(7)
            sub = f"{float(it['subtotal']):.2f}".rjust(7)
            cupom.append(f'{nome} {qtd} {unit} {sub}')
        cupom.append(linha)
        cupom.append(f'TOTAL: R$ {float(pedido["total"]):.2f}'.center(largura))
        cupom.append(linha)

        if obs_texto:
            for obs_line in obs_texto.split('\n'):
                if len(obs_line) <= largura:
                    cupom.append(obs_line)
                else:
                    palavras = obs_line.split(' ')
                    linha_atual = ''
                    for palavra in palavras:
                        if len(linha_atual) + len(palavra) + 1 <= largura:
                            linha_atual = f'{linha_atual} {palavra}'.strip()
                        else:
                            cupom.append(linha_atual)
                            linha_atual = palavra
                    if linha_atual:
                        cupom.append(linha_atual)
            cupom.append(linha)

        cupom.append('Obrigado pela preferencia!'.center(largura))
        cupom.append('Pastelao Brothers'.center(largura))
        cupom.append('')

        texto_cupom = '\n'.join(cupom)

        import tempfile
        temp_file = tempfile.NamedTemporaryFile(
            suffix='.txt', delete=False, mode='w', encoding='utf-8', prefix='cupom_'
        )
        temp_file.write(texto_cupom)
        temp_path = temp_file.name
        temp_file.close()

        nome_impressora = request.json.get('impressora', '') if request.is_json else ''

        if nome_impressora:
            ps_cmd = f'Get-Content -Encoding UTF8 "{temp_path}" | Out-Printer -Name "{nome_impressora}"'
        else:
            ps_cmd = f'Get-Content -Encoding UTF8 "{temp_path}" | Out-Printer'

        import subprocess as sp
        sp.Popen(
            ['powershell', '-WindowStyle', 'Hidden', '-Command', ps_cmd],
            creationflags=0x08000000
        )

        return jsonify({'success': True, 'message': f'Cupom do pedido #{pedido_id} enviado para impressora'}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/admin/pedido/<int:pedido_id>/status', methods=['PUT'])
@admin_required
def admin_atualizar_status_pedido(pedido_id):
    """Atualiza o status de um pedido"""
    try:
        data = request.json
        novo_status = data.get('status')
        
        if not novo_status:
            return jsonify({'success': False, 'error': 'Status não fornecido'}), 400
        
        # Validar status
        status_validos = ['pendente', 'pago', 'preparando', 'pronto', 'entregue', 'retirado', 'cancelado']
        if novo_status not in status_validos:
            return jsonify({'success': False, 'error': 'Status inválido'}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro ao conectar ao banco'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(
            "SELECT p.id, p.cliente_id, p.total, p.status, p.observacoes, u.nome as cliente_nome "
            "FROM pedidos p LEFT JOIN usuarios u ON p.cliente_id = u.id WHERE p.id = %s",
            (pedido_id,)
        )
        pedido = cursor.fetchone()

        if not pedido:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Pedido não encontrado'}), 404

        cursor.execute("""
            UPDATE pedidos SET status = %s WHERE id = %s
        """, (novo_status, pedido_id))
        conn.commit()

        obs = {}
        whatsapp_id = None
        try:
            obs = json.loads(pedido['observacoes']) if pedido.get('observacoes') else {}
            whatsapp_id = obs.get('whatsapp_id')
        except (json.JSONDecodeError, TypeError):
            pass

        if whatsapp_id and novo_status in ('preparando', 'pronto', 'entregue', 'retirado'):
            nome = pedido.get('cliente_nome') or 'cliente'
            is_retirada = obs.get('retirada_local') or obs.get('tipo_entrega') == 'retirada'

            if novo_status == 'preparando':
                msg = (
                    f"*Pedido #{pedido_id}* em preparo!\n\n"
                    f"Estamos preparando seu pedido com carinho, *{nome}*.\n"
                    f"Te avisamos assim que ficar pronto!"
                )
            elif novo_status == 'pronto' and is_retirada:
                msg = (
                    f"*Pedido #{pedido_id}* pronto!\n\n"
                    f"*{nome}*, seu pedido está pronto para retirada!\n"
                    f"Pode vir buscar no *Pastelão Brothers*.\n"
                    f"Estamos te esperando!"
                )
            elif novo_status == 'pronto':
                msg = (
                    f"*Pedido #{pedido_id}* pronto!\n\n"
                    f"Seu pedido está saindo para entrega, *{nome}*!\n"
                    f"Fique atento, logo chegará até você."
                )
            elif novo_status == 'entregue':
                msg = (
                    f"*Pedido #{pedido_id}* entregue!\n\n"
                    f"Seu pedido foi entregue com sucesso.\n"
                    f"Aproveite sua refeição, *{nome}*!\n\n"
                    f"Obrigado pela preferência! Volte sempre!"
                )
            elif novo_status == 'retirado':
                msg = (
                    f"*Pedido #{pedido_id}* retirado!\n\n"
                    f"Obrigado por retirar seu pedido, *{nome}*!\n"
                    f"Aproveite sua refeição! Volte sempre!"
                )
            else:
                msg = None

            if msg:
                try:
                    from utils.whatsapp_sender import enviar_mensagem_texto
                    enviar_mensagem_texto(whatsapp_id, msg)
                    print(f"[admin] Notificação '{novo_status}' enviada para {whatsapp_id}", file=sys.stderr)
                except Exception as e:
                    print(f"[admin] Erro ao enviar notificação WhatsApp: {e}", file=sys.stderr)

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Status atualizado com sucesso'
        }), 200

    except Exception as e:
        logging.exception("Erro ao atualizar status pedido")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

# ==================== RELATÓRIOS ====================

@app.route('/api/admin/relatorios/resumo', methods=['GET'])
@admin_required
def relatorio_resumo():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro DB'}), 500
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) as total FROM pedidos WHERE status NOT IN ('cancelado')")
        total_pedidos = cursor.fetchone()['total']

        cursor.execute("SELECT COALESCE(SUM(total),0) as receita FROM pedidos WHERE status IN ('pago','preparando','pronto','entregue','retirado')")
        receita_total = float(cursor.fetchone()['receita'])

        cursor.execute("SELECT COUNT(DISTINCT cliente_id) as total FROM pedidos WHERE status NOT IN ('cancelado')")
        total_clientes = cursor.fetchone()['total']

        cursor.execute("""
            SELECT COALESCE(SUM(total),0) as receita FROM pedidos 
            WHERE status IN ('pago','preparando','pronto','entregue','retirado') AND DATE(created_at) = CURDATE()
        """)
        receita_hoje = float(cursor.fetchone()['receita'])

        cursor.execute("""
            SELECT COALESCE(SUM(total),0) as receita FROM pedidos 
            WHERE status IN ('pago','preparando','pronto','entregue','retirado') 
            AND YEARWEEK(created_at, 1) = YEARWEEK(CURDATE(), 1)
        """)
        receita_semana = float(cursor.fetchone()['receita'])

        cursor.execute("""
            SELECT COALESCE(SUM(total),0) as receita FROM pedidos 
            WHERE status IN ('pago','preparando','pronto','entregue','retirado') 
            AND MONTH(created_at) = MONTH(CURDATE()) AND YEAR(created_at) = YEAR(CURDATE())
        """)
        receita_mes = float(cursor.fetchone()['receita'])

        cursor.execute("SELECT COUNT(*) as total FROM pedidos WHERE status = 'pendente'")
        pedidos_pendentes = cursor.fetchone()['total']

        cursor.execute("""
            SELECT COALESCE(AVG(total),0) as ticket FROM pedidos 
            WHERE status IN ('pago','preparando','pronto','entregue','retirado')
        """)
        ticket_medio = float(cursor.fetchone()['ticket'])

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'resumo': {
            'total_pedidos': total_pedidos,
            'receita_total': receita_total,
            'total_clientes': total_clientes,
            'receita_hoje': receita_hoje,
            'receita_semana': receita_semana,
            'receita_mes': receita_mes,
            'pedidos_pendentes': pedidos_pendentes,
            'ticket_medio': ticket_medio
        }}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/admin/relatorios/faturamento', methods=['GET'])
@admin_required
def relatorio_faturamento():
    try:
        periodo = request.args.get('periodo', 'dia')
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro DB'}), 500
        cursor = conn.cursor(dictionary=True)

        if periodo == 'dia':
            cursor.execute("""
                SELECT DATE(created_at) as data, COUNT(*) as qtd_pedidos, COALESCE(SUM(total),0) as faturamento
                FROM pedidos WHERE status IN ('pago','preparando','pronto','entregue','retirado')
                GROUP BY DATE(created_at) ORDER BY data DESC LIMIT 30
            """)
        elif periodo == 'semana':
            cursor.execute("""
                SELECT YEARWEEK(created_at, 1) as semana,
                    MIN(DATE(created_at)) as data_inicio,
                    MAX(DATE(created_at)) as data_fim,
                    COUNT(*) as qtd_pedidos, COALESCE(SUM(total),0) as faturamento
                FROM pedidos WHERE status IN ('pago','preparando','pronto','entregue','retirado')
                GROUP BY YEARWEEK(created_at, 1) ORDER BY semana DESC LIMIT 12
            """)
        else:
            cursor.execute("""
                SELECT DATE_FORMAT(created_at, '%%Y-%%m') as mes, COUNT(*) as qtd_pedidos, COALESCE(SUM(total),0) as faturamento
                FROM pedidos WHERE status IN ('pago','preparando','pronto','entregue','retirado')
                GROUP BY DATE_FORMAT(created_at, '%%Y-%%m') ORDER BY mes DESC LIMIT 12
            """)

        dados = cursor.fetchall()
        for d in dados:
            for k, v in d.items():
                if hasattr(v, 'isoformat'):
                    d[k] = v.isoformat()
                elif isinstance(v, (int, float)):
                    d[k] = float(v) if '.' in str(v) else v

        cursor.close()
        conn.close()
        return jsonify({'success': True, 'dados': list(reversed(dados))}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/admin/relatorios/top-clientes', methods=['GET'])
@admin_required
def relatorio_top_clientes():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro DB'}), 500
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT u.id, u.nome, u.email, u.telefone,
                COUNT(p.id) as total_pedidos,
                COALESCE(SUM(p.total),0) as total_gasto,
                MAX(p.created_at) as ultimo_pedido
            FROM usuarios u
            JOIN pedidos p ON u.id = p.cliente_id
            WHERE p.status IN ('pago','preparando','pronto','entregue','retirado')
            GROUP BY u.id, u.nome, u.email, u.telefone
            ORDER BY total_gasto DESC
            LIMIT 20
        """)
        clientes = cursor.fetchall()
        for c in clientes:
            c['total_gasto'] = float(c['total_gasto'])
            if c.get('ultimo_pedido') and hasattr(c['ultimo_pedido'], 'isoformat'):
                c['ultimo_pedido'] = c['ultimo_pedido'].isoformat()

        cursor.close()
        conn.close()
        return jsonify({'success': True, 'clientes': clientes}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/admin/relatorios/produtos-vendidos', methods=['GET'])
@admin_required
def relatorio_produtos_vendidos():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro DB'}), 500
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT pr.id, pr.nome, pr.categoria, pr.preco,
                COALESCE(SUM(pi.quantidade),0) as qtd_vendida,
                COALESCE(SUM(pi.subtotal),0) as faturamento
            FROM produtos pr
            LEFT JOIN pedido_itens pi ON pr.id = pi.produto_id
            LEFT JOIN pedidos p ON pi.pedido_id = p.id AND p.status IN ('pago','preparando','pronto','entregue','retirado')
            WHERE pr.ativo = TRUE
            GROUP BY pr.id, pr.nome, pr.categoria, pr.preco
            ORDER BY qtd_vendida DESC
        """)
        produtos = cursor.fetchall()
        for p in produtos:
            p['preco'] = float(p['preco'])
            p['faturamento'] = float(p['faturamento'])

        cursor.close()
        conn.close()
        return jsonify({'success': True, 'produtos': produtos}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


@app.route('/api/admin/relatorios/dre', methods=['GET'])
@admin_required
def relatorio_dre():
    try:
        periodo = request.args.get('periodo', 'mes')
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': 'Erro DB'}), 500
        cursor = conn.cursor(dictionary=True)

        if periodo == 'hoje':
            filtro = "AND DATE(p.created_at) = CURDATE()"
            label = "Hoje"
        elif periodo == 'semana':
            filtro = "AND YEARWEEK(p.created_at, 1) = YEARWEEK(CURDATE(), 1)"
            label = "Esta Semana"
        elif periodo == 'mes':
            filtro = "AND MONTH(p.created_at) = MONTH(CURDATE()) AND YEAR(p.created_at) = YEAR(CURDATE())"
            label = "Este Mês"
        else:
            filtro = ""
            label = "Todo Período"

        cursor.execute(f"""
            SELECT COALESCE(SUM(p.total),0) as receita_bruta,
                COUNT(p.id) as qtd_pedidos
            FROM pedidos p
            WHERE p.status IN ('pago','preparando','pronto','entregue','retirado') {filtro}
        """)
        row = cursor.fetchone()
        receita_bruta = float(row['receita_bruta'])
        qtd_pedidos = row['qtd_pedidos']

        cursor.execute(f"""
            SELECT COALESCE(SUM(p.total),0) as cancelados
            FROM pedidos p
            WHERE p.status = 'cancelado' {filtro}
        """)
        cancelados = float(cursor.fetchone()['cancelados'])

        cursor.execute(f"""
            SELECT pr.categoria, COALESCE(SUM(pi.subtotal),0) as total
            FROM pedido_itens pi
            JOIN pedidos p ON pi.pedido_id = p.id
            JOIN produtos pr ON pi.produto_id = pr.id
            WHERE p.status IN ('pago','preparando','pronto','entregue','retirado') {filtro}
            GROUP BY pr.categoria ORDER BY total DESC
        """)
        por_categoria = cursor.fetchall()
        for c in por_categoria:
            c['total'] = float(c['total'])

        cursor.execute(f"""
            SELECT COALESCE(SUM(pi.quantidade * pr.custo), 0) as custo_real
            FROM pedido_itens pi
            JOIN pedidos p ON pi.pedido_id = p.id
            JOIN produtos pr ON pi.produto_id = pr.id
            WHERE p.status IN ('pago','preparando','pronto','entregue','retirado') {filtro}
        """)
        custo_real = float(cursor.fetchone()['custo_real'])

        cursor.execute(f"""
            SELECT COUNT(*) as total FROM pedidos p WHERE p.status = 'pendente' {filtro}
        """)
        pendentes = cursor.fetchone()['total']

        impostos_est = receita_bruta * 0.06
        cmv = custo_real if custo_real > 0 else receita_bruta * 0.35
        cmv_estimado = custo_real == 0
        lucro_bruto = receita_bruta - cmv
        lucro_liquido = lucro_bruto - impostos_est

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'dre': {
            'periodo': label,
            'receita_bruta': receita_bruta,
            'cancelados': cancelados,
            'receita_liquida': receita_bruta - cancelados,
            'custo_mercadoria': cmv,
            'cmv_estimado': cmv_estimado,
            'lucro_bruto': lucro_bruto,
            'impostos': impostos_est,
            'lucro_liquido': lucro_liquido,
            'qtd_pedidos': qtd_pedidos,
            'pendentes': pendentes,
            'por_categoria': por_categoria,
            'margem_lucro': (lucro_liquido / receita_bruta * 100) if receita_bruta > 0 else 0
        }}), 200
    except Exception as e:
        logging.exception("Erro interno")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500


if __name__ == '__main__':
    import sys
    import socket
    
    # Função para verificar se porta está livre
    def is_port_free(port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result != 0
    
    # Tentar porta 5000, se não conseguir, tentar 5001
    port = 5000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    # Verificar se porta está livre antes de tentar usar
    if not is_port_free(port):
        print(f"\n[AVISO] Porta {port} está em uso. Tentando porta {port + 1}...")
        port = port + 1
    
    try:
        print(f"\n[INFO] Iniciando servidor Flask na porta {port}...")
        print(f"[INFO] Backend API: http://localhost:{port}/api")
        print(f"[INFO] Debug mode: {'ON' if FLASK_DEBUG else 'OFF'}")
        app.run(host='0.0.0.0', port=port, debug=FLASK_DEBUG)
    except OSError as e:
        error_str = str(e).lower()
        if "10048" in str(e) or "permission" in error_str or "acesso" in error_str:
            if port == 5000:
                print(f"\n[AVISO] Porta {port} em uso ou sem permissão. Tentando porta {port + 1}...")
                try:
                    app.run(host='0.0.0.0', port=port + 1, debug=FLASK_DEBUG)
                except Exception as e2:
                    print(f"\n[ERRO] Não foi possível iniciar em nenhuma porta: {e2}")
                    raise
            else:
                print(f"\n[ERRO] Não foi possível iniciar na porta {port}: {e}")
                raise
        else:
            raise
