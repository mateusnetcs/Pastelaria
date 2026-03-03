"""
Ferramentas (functions) que a OpenAI pode chamar durante a conversa.
Cada ferramenta executa uma ação no banco de dados ou sistema externo.
"""
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import json
import subprocess
import os
import sys
import random
import string
import bcrypt


def get_db_connection(db_config):
    try:
        return mysql.connector.connect(**db_config)
    except Error as e:
        print(f"[tools] Erro ao conectar ao MySQL: {e}", file=sys.stderr)
        return None


# =====================================================================
# Definições das tools para a API da OpenAI (JSON Schema)
# =====================================================================

TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "verificar_cliente",
            "description": "Verifica se o cliente já está cadastrado no sistema pelo número de telefone. Use sempre no início da conversa.",
            "parameters": {
                "type": "object",
                "properties": {
                    "telefone": {
                        "type": "string",
                        "description": "Número de telefone do cliente (apenas dígitos)"
                    }
                },
                "required": ["telefone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cadastrar_cliente",
            "description": "Cadastra um novo cliente no sistema. Use apenas depois de coletar nome, email e data de nascimento.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {
                        "type": "string",
                        "description": "Nome completo do cliente"
                    },
                    "email": {
                        "type": "string",
                        "description": "Email do cliente"
                    },
                    "telefone": {
                        "type": "string",
                        "description": "Telefone do cliente (apenas dígitos)"
                    },
                    "data_nascimento": {
                        "type": "string",
                        "description": "Data de nascimento no formato YYYY-MM-DD"
                    }
                },
                "required": ["nome", "email", "telefone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "enviar_cardapio_foto",
            "description": "Envia a foto do cardápio e o link para pedir online. Use quando o cliente pedir cardápio, menu ou quiser ver os produtos (ex: 'manda o cardápio', 'qual o cardápio'). NÃO use quando o cliente JÁ disse que quer pedir pelo WhatsApp.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "enviar_lista_produtos_whatsapp",
            "description": "Envia a LISTA de produtos (cardápio em texto) direto no chat. Use quando o cliente disser que quer fazer pedido pelo WhatsApp (ex: 'quero fazer aqui mesmo', 'quero pedir pelo zap', 'aqui pelo whatsapp'). NÃO envia link - só a lista. Depois pergunte o que deseja pedir.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "listar_produtos",
            "description": "Lista produtos por categoria (Salgado, Doce, Bebida). Retorna dados para a IA - use quando precisar consultar produtos. Para ENVIAR a lista ao cliente, use enviar_lista_produtos_whatsapp ou enviar_cardapio_foto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": {
                        "type": "string",
                        "description": "Filtrar por categoria: Salgado, Doce ou Bebida. Se vazio, retorna todos.",
                        "enum": ["Salgado", "Doce", "Bebida"]
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "criar_pedido",
            "description": "Cria um pedido com os itens escolhidos. Use cliente_id quando o cliente está cadastrado. Use nome_cliente (e omita cliente_id) quando o cliente recusou o cadastro e informou só o nome para a comanda.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cliente_id": {
                        "type": "integer",
                        "description": "ID do cliente no sistema (obrigatório se cadastrado). Omitir se pedido de visitante."
                    },
                    "nome_cliente": {
                        "type": "string",
                        "description": "Nome para a comanda - use quando cliente recusou cadastro e informou apenas o nome"
                    },
                    "itens": {
                        "type": "array",
                        "description": "Lista de itens do pedido",
                        "items": {
                            "type": "object",
                            "properties": {
                                "nome_produto": {
                                    "type": "string",
                                    "description": "Nome do produto exatamente como aparece no cardápio (ex: 'Pastel de Camarão')"
                                },
                                "quantidade": {
                                    "type": "integer",
                                    "description": "Quantidade desejada"
                                }
                            },
                            "required": ["nome_produto", "quantidade"]
                        }
                    },
                    "tipo_entrega": {
                        "type": "string",
                        "description": "Se o pedido é para entrega ou retirada no local",
                        "enum": ["entrega", "retirada"]
                    },
                    "endereco": {
                        "type": "object",
                        "description": "Endereço de entrega (obrigatório se tipo_entrega=entrega)",
                        "properties": {
                            "bairro": {"type": "string", "description": "Bairro"},
                            "rua": {"type": "string", "description": "Rua/Avenida"},
                            "numero": {"type": "string", "description": "Número da casa"},
                            "complemento": {"type": "string", "description": "Complemento (apto, bloco, referência)"}
                        }
                    }
                },
                "required": ["itens", "tipo_entrega"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gerar_pagamento_pix",
            "description": "Gera um QR Code PIX para pagamento de um pedido já criado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {
                        "type": "integer",
                        "description": "ID do pedido"
                    },
                    "valor_total": {
                        "type": "number",
                        "description": "Valor total do pedido"
                    },
                    "cliente_nome": {
                        "type": "string",
                        "description": "Nome do cliente"
                    },
                    "cliente_email": {
                        "type": "string",
                        "description": "Email do cliente"
                    }
                },
                "required": ["pedido_id", "valor_total"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "gerar_pagamento_cartao",
            "description": "Gera um link de pagamento do Mercado Pago para pagamento com cartão de crédito/débito. O cliente receberá um link para pagar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {
                        "type": "integer",
                        "description": "ID do pedido"
                    },
                    "valor_total": {
                        "type": "number",
                        "description": "Valor total do pedido"
                    },
                    "cliente_nome": {
                        "type": "string",
                        "description": "Nome do cliente"
                    },
                    "cliente_email": {
                        "type": "string",
                        "description": "Email do cliente"
                    }
                },
                "required": ["pedido_id", "valor_total"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "confirmar_pagamento_dinheiro",
            "description": "Confirma o pedido com pagamento em dinheiro. Use após perguntar sobre troco e o cliente confirmar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {
                        "type": "integer",
                        "description": "ID do pedido"
                    },
                    "precisa_troco": {
                        "type": "boolean",
                        "description": "Se o cliente precisa de troco"
                    },
                    "troco_para": {
                        "type": "number",
                        "description": "Valor da nota para calcular troco (ex: 50.00 se vai pagar com nota de 50)"
                    }
                },
                "required": ["pedido_id"]
            }
        }
    }
]


# =====================================================================
# Implementação das funções
# =====================================================================

def verificar_cliente(telefone, db_config):
    """Busca cliente no banco pelo telefone."""
    conn = get_db_connection(db_config)
    if not conn:
        return {"erro": "Não foi possível conectar ao banco de dados"}

    try:
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        cursor = conn.cursor(dictionary=True)

        if telefone_limpo:
            cursor.execute("""
                SELECT id, nome, email, telefone, data_nascimento
                FROM usuarios
                WHERE telefone = %s OR telefone LIKE %s
                LIMIT 1
            """, (telefone_limpo, f'%{telefone_limpo[-8:]}'))
            cliente = cursor.fetchone()
        else:
            cliente = None

        cursor.close()
        conn.close()

        if cliente:
            dn = cliente['data_nascimento']
            return {
                "cliente_existe": True,
                "cliente_id": cliente['id'],
                "nome": cliente['nome'],
                "email": cliente['email'],
                "telefone": cliente['telefone'],
                "data_nascimento": dn.isoformat() if dn else None
            }
        return {
            "cliente_existe": False,
            "mensagem": "Cliente não encontrado. Precisa coletar nome, email e data de nascimento para cadastrar."
        }
    except Exception as e:
        if conn:
            conn.close()
        return {"erro": str(e)}


def _gerar_senha_cliente(nome, data_nascimento_obj=None):
    """Gera senha usando primeiro nome + data de nascimento (ddmm)."""
    primeiro_nome = nome.strip().split()[0].lower()
    if data_nascimento_obj:
        return f"{primeiro_nome}{data_nascimento_obj.strftime('%d%m')}"
    return f"{primeiro_nome}2025"


def cadastrar_cliente(nome, email, telefone, db_config, data_nascimento=None):
    """Insere novo cliente no banco com senha gerada automaticamente."""
    conn = get_db_connection(db_config)
    if not conn:
        return {"erro": "Não foi possível conectar ao banco de dados"}

    try:
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"erro": "Este email já está cadastrado."}

        cursor.execute("SELECT id FROM usuarios WHERE telefone = %s", (telefone_limpo,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return {"erro": "Este telefone já está cadastrado."}

        data_nascimento_obj = None
        if data_nascimento:
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                try:
                    data_nascimento_obj = datetime.strptime(data_nascimento, fmt).date()
                    break
                except ValueError:
                    continue

        senha_texto = _gerar_senha_cliente(nome, data_nascimento_obj)
        senha_hash = bcrypt.hashpw(senha_texto.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cursor.execute("""
            INSERT INTO usuarios (nome, email, senha, telefone, data_nascimento, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (nome, email, senha_hash, telefone_limpo, data_nascimento_obj))
        conn.commit()
        cliente_id = cursor.lastrowid

        cursor.close()
        conn.close()

        print(f"[tools] Cliente {nome} cadastrado com senha gerada", file=sys.stderr)

        return {
            "sucesso": True,
            "cliente_id": cliente_id,
            "nome": nome,
            "email": email,
            "telefone": telefone_limpo,
            "senha_acesso": senha_texto,
            "mensagem": f"Cliente {nome} cadastrado com sucesso!"
        }
    except Exception as e:
        if conn:
            conn.close()
        return {"erro": str(e)}


def listar_produtos(db_config, categoria=None):
    """Busca produtos ativos, opcionalmente filtrados por categoria."""
    conn = get_db_connection(db_config)
    if not conn:
        return {"erro": "Não foi possível conectar ao banco de dados"}

    try:
        cursor = conn.cursor(dictionary=True)

        if categoria:
            cursor.execute("""
                SELECT id, nome, descricao, preco, categoria, tipo
                FROM produtos WHERE ativo = TRUE AND categoria = %s
                ORDER BY nome
            """, (categoria,))
        else:
            cursor.execute("""
                SELECT id, nome, descricao, preco, categoria, tipo
                FROM produtos WHERE ativo = TRUE
                ORDER BY categoria, nome
            """)

        produtos = cursor.fetchall()
        for p in produtos:
            p['preco'] = float(p['preco'])

        cursor.close()
        conn.close()

        return {"produtos": produtos, "total": len(produtos)}
    except Exception as e:
        if conn:
            conn.close()
        return {"erro": str(e)}


def criar_pedido(itens, db_config, whatsapp_id=None, tipo_entrega="retirada", endereco=None,
                 cliente_id=None, nome_cliente=None):
    """Cria pedido no banco. Use cliente_id para cadastrado ou nome_cliente para visitante."""
    conn = get_db_connection(db_config)
    if not conn:
        return {"erro": "Não foi possível conectar ao banco de dados"}

    # Pedido de visitante: cliente recusou cadastro, informou só o nome
    is_visitante = (nome_cliente and (cliente_id is None or cliente_id == ""))
    if is_visitante:
        cliente_id_final = None
        cliente_nome_final = str(nome_cliente).strip() or "Cliente"
    else:
        # Pedido de cliente cadastrado
        if not cliente_id:
            cursor = conn.cursor(dictionary=True)
            cursor.close()
            conn.close()
            return {"erro": "Informe cliente_id ou nome_cliente. Para cadastrado use cliente_id; para visitante use nome_cliente."}
        if int(cliente_id) > 999999:
            conn.close()
            return {
                "erro": "cliente_id inválido. Parece ser um número de telefone/chat, não um ID do banco. "
                        "Use o cliente_id retornado por cadastrar_cliente ou verificar_cliente."
            }
        cliente_id_final = int(cliente_id)
        cliente_nome_final = None  # será preenchido abaixo

    try:
        cursor = conn.cursor(dictionary=True)

        if not is_visitante:
            cursor.execute("SELECT id, nome FROM usuarios WHERE id = %s", (cliente_id_final,))
            cliente = cursor.fetchone()
            if not cliente:
                if whatsapp_id:
                    telefone_num = whatsapp_id.split('@')[0] if '@' in whatsapp_id else whatsapp_id
                    cursor.execute(
                        "SELECT id, nome FROM usuarios WHERE telefone = %s OR telefone LIKE %s LIMIT 1",
                        (telefone_num, f'%{telefone_num[-8:]}%')
                    )
                    cliente = cursor.fetchone()
                    if cliente:
                        cliente_id_final = cliente['id']
                        cliente_nome_final = cliente['nome']
                        print(f"[tools] criar_pedido: cliente_id corrigido para {cliente_id_final} ({cliente['nome']}) via chat_id", file=sys.stderr)
            else:
                cliente_nome_final = cliente['nome']
            if not cliente and not is_visitante:
                cursor.close()
                conn.close()
                return {"erro": "Cliente não encontrado. Cadastre o cliente primeiro com cadastrar_cliente."}

        total = 0
        itens_resolvidos = []
        itens_descricao = []

        for item in itens:
            nome_produto = item.get('nome_produto', '')
            pid = item.get('produto_id')
            qtd = item.get('quantidade', 1)

            if nome_produto:
                cursor.execute(
                    "SELECT id, nome, preco, ativo FROM produtos WHERE nome LIKE %s AND ativo = TRUE LIMIT 1",
                    (f'%{nome_produto}%',)
                )
            elif pid:
                cursor.execute(
                    "SELECT id, nome, preco, ativo FROM produtos WHERE id = %s",
                    (pid,)
                )
            else:
                cursor.close()
                conn.close()
                return {"erro": "Item sem nome_produto ou produto_id"}

            produto = cursor.fetchone()
            if not produto:
                cursor.close()
                conn.close()
                return {"erro": f"Produto '{nome_produto or pid}' não encontrado no cardápio"}
            if not produto['ativo']:
                cursor.close()
                conn.close()
                return {"erro": f"Produto '{produto['nome']}' não está disponível"}

            subtotal = float(produto['preco']) * qtd
            total += subtotal
            itens_resolvidos.append({'produto_id': produto['id'], 'quantidade': qtd, 'preco': float(produto['preco'])})
            itens_descricao.append(f"{produto['nome']} x{qtd} = R$ {subtotal:.2f}")

        observacoes_dict = {
            'whatsapp_id': whatsapp_id,
            'origem': 'whatsapp_ia',
            'tipo_entrega': tipo_entrega
        }

        if tipo_entrega == 'retirada':
            observacoes_dict['retirada_local'] = True
        elif tipo_entrega == 'entrega' and endereco:
            observacoes_dict['bairro'] = endereco.get('bairro', '')
            observacoes_dict['rua'] = endereco.get('rua', '')
            observacoes_dict['numero'] = endereco.get('numero', '')
            observacoes_dict['complemento'] = endereco.get('complemento', '')

        telefone_num = None
        if whatsapp_id:
            telefone_num = whatsapp_id.split('@')[0] if '@' in whatsapp_id else whatsapp_id

        cursor.execute("""
            INSERT INTO pedidos (cliente_id, cliente_nome, cliente_telefone, cliente_whatsapp, total, status, observacoes, created_at)
            VALUES (%s, %s, %s, %s, %s, 'pendente', %s, NOW())
        """, (cliente_id_final, cliente_nome_final, telefone_num, telefone_num, total, json.dumps(observacoes_dict)))

        pedido_id = cursor.lastrowid

        for item_r in itens_resolvidos:
            cursor.execute("""
                INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
            """, (pedido_id, item_r['produto_id'], item_r['quantidade'],
                  item_r['preco'], item_r['preco'] * item_r['quantidade']))

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "sucesso": True,
            "pedido_id": pedido_id,
            "total": total,
            "itens": itens_descricao,
            "mensagem": f"Pedido #{pedido_id} criado! Total: R$ {total:.2f}"
        }
    except Exception as e:
        if conn:
            conn.close()
        return {"erro": str(e)}


def gerar_pagamento_pix(pedido_id, valor_total, db_config,
                        cliente_nome="", cliente_email="", chat_id=None):
    """Gera QR Code PIX via Mercado Pago."""
    try:
        conn = get_db_connection(db_config)
        if not conn:
            return {"erro": "Não foi possível conectar ao banco de dados"}

        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, total, status FROM pedidos WHERE id = %s", (pedido_id,))
        pedido = cursor.fetchone()

        if not pedido and chat_id:
            print(f"[pix] Pedido #{pedido_id} não existe, buscando último pendente para {chat_id}", file=sys.stderr)
            cursor.execute(
                "SELECT id, total, status FROM pedidos WHERE observacoes LIKE %s AND status = 'pendente' ORDER BY id DESC LIMIT 1",
                (f'%{chat_id}%',)
            )
            pedido = cursor.fetchone()

        if not pedido:
            cursor.close()
            conn.close()
            return {"erro": f"Pedido #{pedido_id} não encontrado no banco de dados"}

        pedido_id_real = pedido['id']
        valor_total_real = float(pedido['total'])
        print(f"[pix] Usando pedido real #{pedido_id_real} (valor: R$ {valor_total_real:.2f})", file=sys.stderr)

        cursor.close()
        conn.close()

        script_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'Mercado pago', 'api-mercadopago.py'
        )

        dados = {
            'action': 'criar_pedido',
            'pedido_id': pedido_id_real,
            'valor_total': valor_total_real,
            'itens': [f"Pedido #{pedido_id_real}"],
            'dados_cliente': {
                'nome': cliente_nome,
                'email': cliente_email
            }
        }

        env = os.environ.copy()
        from config import WEBHOOK_PUBLIC_URL
        if WEBHOOK_PUBLIC_URL:
            env['WEBHOOK_PUBLIC_URL'] = WEBHOOK_PUBLIC_URL

        result = subprocess.run(
            [sys.executable, script_path],
            input=json.dumps(dados),
            text=True,
            capture_output=True,
            timeout=30,
            env=env
        )

        if result.returncode == 0:
            stdout_lines = result.stdout.strip().split('\n')
            json_line = stdout_lines[-1] if stdout_lines else ''
            if json_line:
                mp_result = json.loads(json_line)
                if mp_result.get('success'):
                    payment_id = mp_result.get('payment_id') or mp_result.get('id')
                    if payment_id:
                        conn = get_db_connection(db_config)
                        if conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE pedidos SET preference_id = %s WHERE id = %s",
                                (str(payment_id), pedido_id_real)
                            )
                            rows = cursor.rowcount
                            conn.commit()
                            cursor.close()
                            conn.close()
                            print(f"[pix] preference_id={payment_id} salvo no pedido #{pedido_id_real} ({rows} linhas)", file=sys.stderr)

                    return {
                        "sucesso": True,
                        "pedido_id": pedido_id_real,
                        "valor_total": valor_total_real,
                        "qr_code": mp_result.get('qr_code'),
                        "qr_code_base64": mp_result.get('qr_code_base64'),
                        "link_pagamento": mp_result.get('init_point'),
                        "mensagem": f"PIX gerado para o pedido #{pedido_id_real}. Valor: R$ {valor_total_real:.2f}"
                    }
                return {"erro": mp_result.get('error', 'Erro ao gerar PIX')}

        return {"erro": f"Erro no script de pagamento (código {result.returncode})"}
    except subprocess.TimeoutExpired:
        return {"erro": "Timeout ao gerar pagamento. Tente novamente."}
    except Exception as e:
        return {"erro": str(e)}


def gerar_pagamento_cartao(pedido_id, valor_total, db_config,
                           cliente_nome="", cliente_email="", chat_id=None):
    """Gera link de pagamento Mercado Pago para cartão."""
    try:
        conn = get_db_connection(db_config)
        if not conn:
            return {"erro": "Não foi possível conectar ao banco de dados"}

        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, total, status FROM pedidos WHERE id = %s", (pedido_id,))
        pedido = cursor.fetchone()

        if not pedido and chat_id:
            print(f"[cartao] Pedido #{pedido_id} não existe, buscando último pendente para {chat_id}", file=sys.stderr)
            cursor.execute(
                "SELECT id, total, status FROM pedidos WHERE observacoes LIKE %s AND status = 'pendente' ORDER BY id DESC LIMIT 1",
                (f'%{chat_id}%',)
            )
            pedido = cursor.fetchone()

        if not pedido:
            cursor.close()
            conn.close()
            return {"erro": f"Pedido #{pedido_id} não encontrado no banco de dados"}

        pedido_id_real = pedido['id']
        valor_total_real = float(pedido['total'])
        print(f"[cartao] Usando pedido real #{pedido_id_real} (valor: R$ {valor_total_real:.2f})", file=sys.stderr)

        cursor.close()
        conn.close()

        script_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'Mercado pago', 'api-mercadopago.py'
        )

        dados = {
            'action': 'criar_pedido',
            'pedido_id': pedido_id_real,
            'valor_total': valor_total_real,
            'itens': [f"Pedido #{pedido_id_real}"],
            'forcar_preferencia': True,
            'dados_cliente': {
                'nome': cliente_nome,
                'email': cliente_email
            }
        }

        env = os.environ.copy()
        from config import WEBHOOK_PUBLIC_URL
        if WEBHOOK_PUBLIC_URL:
            env['WEBHOOK_PUBLIC_URL'] = WEBHOOK_PUBLIC_URL

        result = subprocess.run(
            [sys.executable, script_path],
            input=json.dumps(dados),
            text=True,
            capture_output=True,
            timeout=30,
            env=env
        )

        if result.returncode == 0:
            stdout_lines = result.stdout.strip().split('\n')
            json_line = stdout_lines[-1] if stdout_lines else ''
            if json_line:
                mp_result = json.loads(json_line)
                if mp_result.get('success'):
                    preference_id = mp_result.get('id')
                    if preference_id:
                        conn = get_db_connection(db_config)
                        if conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE pedidos SET preference_id = %s WHERE id = %s",
                                (str(preference_id), pedido_id_real)
                            )
                            conn.commit()
                            cursor.close()
                            conn.close()
                            print(f"[cartao] preference_id={preference_id} salvo no pedido #{pedido_id_real}", file=sys.stderr)

                    return {
                        "sucesso": True,
                        "pedido_id": pedido_id_real,
                        "valor_total": valor_total_real,
                        "link_pagamento": mp_result.get('init_point'),
                        "mensagem": f"Link de pagamento gerado para o pedido #{pedido_id_real}. Valor: R$ {valor_total_real:.2f}"
                    }
                return {"erro": mp_result.get('error', 'Erro ao gerar link de pagamento')}

        return {"erro": f"Erro no script de pagamento (código {result.returncode})"}
    except subprocess.TimeoutExpired:
        return {"erro": "Timeout ao gerar pagamento. Tente novamente."}
    except Exception as e:
        return {"erro": str(e)}


def confirmar_pagamento_dinheiro(pedido_id, db_config, chat_id=None,
                                 precisa_troco=False, troco_para=None):
    """Confirma pedido com pagamento em dinheiro."""
    try:
        conn = get_db_connection(db_config)
        if not conn:
            return {"erro": "Não foi possível conectar ao banco de dados"}

        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, total, status, observacoes FROM pedidos WHERE id = %s", (pedido_id,))
        pedido = cursor.fetchone()

        if not pedido and chat_id:
            cursor.execute(
                "SELECT id, total, status, observacoes FROM pedidos WHERE observacoes LIKE %s AND status = 'pendente' ORDER BY id DESC LIMIT 1",
                (f'%{chat_id}%',)
            )
            pedido = cursor.fetchone()

        if not pedido:
            cursor.close()
            conn.close()
            return {"erro": f"Pedido #{pedido_id} não encontrado"}

        pedido_id_real = pedido['id']
        valor_total = float(pedido['total'])

        obs = {}
        try:
            obs = json.loads(pedido['observacoes']) if pedido['observacoes'] else {}
        except (json.JSONDecodeError, TypeError):
            pass

        obs['metodo_pagamento'] = 'dinheiro'
        obs['precisa_troco'] = precisa_troco
        if precisa_troco and troco_para:
            obs['troco_para'] = troco_para
            obs['valor_troco'] = round(troco_para - valor_total, 2)

        cursor.execute(
            "UPDATE pedidos SET status = 'confirmado', observacoes = %s WHERE id = %s",
            (json.dumps(obs, ensure_ascii=False), pedido_id_real)
        )
        conn.commit()
        cursor.close()
        conn.close()

        resultado = {
            "sucesso": True,
            "pedido_id": pedido_id_real,
            "valor_total": valor_total,
            "metodo_pagamento": "dinheiro",
            "mensagem": f"Pedido #{pedido_id_real} confirmado! Pagamento em dinheiro."
        }

        if precisa_troco and troco_para:
            troco = round(troco_para - valor_total, 2)
            resultado["troco"] = troco
            resultado["mensagem"] += f" Troco de R$ {troco:.2f} para nota de R$ {troco_para:.2f}."

        print(f"[dinheiro] Pedido #{pedido_id_real} confirmado com dinheiro", file=sys.stderr)
        return resultado

    except Exception as e:
        return {"erro": str(e)}


# =====================================================================
# Dispatcher: executa a função pelo nome
# =====================================================================

def executar_tool(nome_funcao, argumentos, db_config, chat_id=None):
    """Executa uma tool pelo nome e retorna o resultado como string JSON."""
    try:
        if nome_funcao == "verificar_cliente":
            resultado = verificar_cliente(argumentos.get("telefone", ""), db_config)

        elif nome_funcao == "cadastrar_cliente":
            resultado = cadastrar_cliente(
                argumentos.get("nome", ""),
                argumentos.get("email", ""),
                argumentos.get("telefone", ""),
                db_config,
                argumentos.get("data_nascimento")
            )

        elif nome_funcao == "enviar_cardapio_foto":
            from utils.whatsapp_sender import enviar_cardapio_foto
            resultado = enviar_cardapio_foto(chat_id)

        elif nome_funcao == "enviar_lista_produtos_whatsapp":
            from utils.whatsapp_sender import enviar_cardapio_lista
            ok = enviar_cardapio_lista(chat_id, db_config, incluir_link=False)
            resultado = {"success": ok, "mensagem": "Lista de produtos enviada" if ok else "Erro ao enviar lista"}

        elif nome_funcao == "listar_produtos":
            resultado = listar_produtos(db_config, argumentos.get("categoria"))

        elif nome_funcao == "criar_pedido":
            itens_raw = argumentos.get("itens", [])
            resultado = criar_pedido(
                itens_raw,
                db_config,
                whatsapp_id=chat_id,
                tipo_entrega=argumentos.get("tipo_entrega", "retirada"),
                endereco=argumentos.get("endereco"),
                cliente_id=argumentos.get("cliente_id"),
                nome_cliente=argumentos.get("nome_cliente")
            )

        elif nome_funcao == "gerar_pagamento_pix":
            resultado = gerar_pagamento_pix(
                argumentos.get("pedido_id"),
                argumentos.get("valor_total"),
                db_config,
                argumentos.get("cliente_nome", ""),
                argumentos.get("cliente_email", ""),
                chat_id=chat_id
            )

        elif nome_funcao == "gerar_pagamento_cartao":
            resultado = gerar_pagamento_cartao(
                argumentos.get("pedido_id"),
                argumentos.get("valor_total"),
                db_config,
                argumentos.get("cliente_nome", ""),
                argumentos.get("cliente_email", ""),
                chat_id=chat_id
            )

        elif nome_funcao == "confirmar_pagamento_dinheiro":
            resultado = confirmar_pagamento_dinheiro(
                argumentos.get("pedido_id"),
                db_config,
                chat_id=chat_id,
                precisa_troco=argumentos.get("precisa_troco", False),
                troco_para=argumentos.get("troco_para")
            )

        else:
            resultado = {"erro": f"Função '{nome_funcao}' não encontrada"}

        return json.dumps(resultado, ensure_ascii=False, default=str)

    except Exception as e:
        return json.dumps({"erro": str(e)}, ensure_ascii=False)
