"""
Utilitário para enviar mensagens via WhatsApp usando WAHA API
"""
import requests
import json
import sys
import time
import random

from config import WAHA_API_URL, WAHA_API_KEY, WAHA_SESSION

EMOJIS_REACAO = ["👍", "😊", "✨", "🙏", "💛", "🥟", "👀", "🔥"]


def reagir_mensagem(chat_id, message_id, emoji=None):
    """Reage a uma mensagem do cliente com um emoji."""
    try:
        if not emoji:
            emoji = random.choice(EMOJIS_REACAO)

        url = f"{WAHA_API_URL}/reaction"
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": WAHA_API_KEY
        }
        payload = {
            "chatId": chat_id,
            "messageId": message_id,
            "reaction": emoji,
            "session": WAHA_SESSION
        }
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code in (200, 201):
            print(f"[waha] Reação {emoji} enviada em {chat_id}", file=sys.stderr)
        return response.status_code in (200, 201)
    except Exception as e:
        print(f"[waha] Erro ao reagir: {e}", file=sys.stderr)
        return False


def enviar_mensagens_separadas(chat_id, texto_completo):
    """Quebra a resposta da IA em mensagens separadas e envia com delay."""
    if not texto_completo or not texto_completo.strip():
        return

    partes = _quebrar_mensagem(texto_completo)

    for i, parte in enumerate(partes):
        parte = parte.strip()
        if not parte:
            continue
        enviar_mensagem_texto(chat_id, parte)
        if i < len(partes) - 1:
            delay = min(0.8 + len(parte) * 0.01, 2.5)
            time.sleep(delay)


def _quebrar_mensagem(texto):
    """Divide a mensagem em partes lógicas para envio separado."""
    if len(texto) < 150:
        return [texto]

    blocos = texto.split("\n\n")

    partes = []
    buffer = ""

    for bloco in blocos:
        bloco = bloco.strip()
        if not bloco:
            continue

        if buffer and len(buffer) + len(bloco) > 400:
            partes.append(buffer.strip())
            buffer = bloco
        else:
            buffer = f"{buffer}\n\n{bloco}" if buffer else bloco

    if buffer.strip():
        partes.append(buffer.strip())

    if not partes:
        return [texto]

    return partes

def enviar_mensagem_texto(chat_id, mensagem):
    """
    Envia mensagem de texto via WhatsApp usando WAHA API
    
    Args:
        chat_id (str): ID do chat (ex: "5511999999999@c.us" ou "49576824307733@lid")
        mensagem (str): Texto da mensagem
    
    Returns:
        dict: Resposta da API com sucesso ou erro
    """
    try:
        url = f"{WAHA_API_URL}/sendText"
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": WAHA_API_KEY
        }
        payload = {
            "chatId": chat_id,
            "text": mensagem,
            "session": WAHA_SESSION
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code in (200, 201):
            print(f"[waha] Mensagem enviada para {chat_id}", file=sys.stderr)
            return {
                'success': True,
                'message': 'Mensagem enviada com sucesso',
                'data': response.json()
            }
        else:
            print(f"[waha] Erro {response.status_code} ao enviar para {chat_id}: {response.text}", file=sys.stderr)
            return {
                'success': False,
                'error': f'Erro ao enviar mensagem: {response.status_code}',
                'details': response.text
            }
            
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar mensagem WhatsApp: {e}", file=sys.stderr)
        return {
            'success': False,
            'error': f'Erro de conexão: {str(e)}'
        }
    except Exception as e:
        print(f"Erro inesperado ao enviar mensagem WhatsApp: {e}", file=sys.stderr)
        return {
            'success': False,
            'error': f'Erro inesperado: {str(e)}'
        }

def enviar_pix_completo(chat_id, pix_code, valor_total, pedido_id):
    """
    Envia PIX formatado: mensagem informativa + código separado + botão "Já paguei".
    """
    try:
        import time

        msg_info = (
            f"💳 *PIX - Pedido #{pedido_id}*\n\n"
            f"*Valor: R$ {float(valor_total):.2f}*\n\n"
            f"Copie o código abaixo e cole no app do seu banco:"
        )
        enviar_mensagem_texto(chat_id, msg_info)
        time.sleep(0.5)

        enviar_mensagem_texto(chat_id, pix_code)
        time.sleep(0.5)

        url = f"{WAHA_API_URL}/sendButtons"
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": WAHA_API_KEY
        }
        payload = {
            "chatId": chat_id,
            "session": WAHA_SESSION,
            "buttons": [
                {"id": "ja_paguei", "text": "Já paguei!"}
            ],
            "text": "Depois de pagar, clique no botão abaixo 👇"
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)

        if response.status_code not in (200, 201):
            enviar_mensagem_texto(chat_id, "Depois de pagar, me avise digitando *Já paguei*! 😊")

        print(f"[waha] PIX completo enviado para {chat_id}", file=sys.stderr)
        return {'success': True}

    except Exception as e:
        print(f"[waha] Erro ao enviar PIX completo: {e}", file=sys.stderr)
        enviar_mensagem_texto(chat_id, f"Código PIX:\n\n{pix_code}\n\nDepois de pagar, me avise! 😊")
        return {'success': False, 'error': str(e)}


def enviar_link_cartao(chat_id, link_pagamento, valor_total, pedido_id):
    """
    Envia link de pagamento por cartão formatado via WhatsApp.
    """
    try:
        import time

        msg_info = (
            f"💳 *Pagamento por Cartão - Pedido #{pedido_id}*\n\n"
            f"*Valor: R$ {float(valor_total):.2f}*\n\n"
            f"Clique no link abaixo para pagar com cartão de crédito ou débito:"
        )
        enviar_mensagem_texto(chat_id, msg_info)
        time.sleep(0.5)

        enviar_mensagem_texto(chat_id, link_pagamento)
        time.sleep(0.5)

        enviar_mensagem_texto(chat_id, "Após o pagamento ser aprovado, você receberá uma confirmação aqui! 😊")

        print(f"[waha] Link cartão enviado para {chat_id}", file=sys.stderr)
        return {'success': True}

    except Exception as e:
        print(f"[waha] Erro ao enviar link cartão: {e}", file=sys.stderr)
        enviar_mensagem_texto(chat_id, f"Link de pagamento:\n\n{link_pagamento}\n\nApós pagar, você receberá a confirmação! 😊")
        return {'success': False, 'error': str(e)}


def enviar_cardapio_lista(chat_id, db_config):
    """
    Envia o cardápio como lista organizada por categoria (Salgados, Doces, Bebidas).
    Cada categoria em mensagem separada para melhor leitura.
    """
    import time
    try:
        from ai.tools import listar_produtos
        from config import WEBHOOK_PUBLIC_URL

        res = listar_produtos(db_config)
        if res.get('erro'):
            return False
        produtos = res.get('produtos', [])

        categorias = {'Salgado': '🥟 *SALGADOS*', 'Doce': '🍬 *DOCES*', 'Bebida': '🥤 *BEBIDAS*'}
        por_cat = {}
        for p in produtos:
            cat = p.get('categoria', 'Outros')
            if cat not in por_cat:
                por_cat[cat] = []
            por_cat[cat].append(p)

        url_base = (WEBHOOK_PUBLIC_URL or "https://pastelaobhoters.chatboot.cloud").rstrip('/')

        # Intro
        enviar_mensagem_texto(chat_id, "📋 *Cardápio Pastelão Brothers*\n\nAqui estão nossos produtos:")
        time.sleep(0.6)

        for cat_key, titulo in categorias.items():
            if cat_key not in por_cat or not por_cat[cat_key]:
                continue
            linhas = [titulo, ""]
            for p in por_cat[cat_key]:
                preco = f"R$ {float(p['preco']):.2f}".replace('.', ',')
                linhas.append(f"• *{p['nome']}* – {preco}")
            enviar_mensagem_texto(chat_id, "\n".join(linhas))
            time.sleep(0.5)

        enviar_mensagem_texto(chat_id, f"Se preferir, acesse o cardápio online com fotos:\n🌐 {url_base}\n\nQualquer dúvida é só perguntar! 😊")
        print(f"[waha] Cardápio em lista enviado para {chat_id}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[waha] Erro ao enviar cardápio lista: {e}", file=sys.stderr)
        return False


def enviar_cardapio_foto(chat_id):
    """
    Envia a foto do cardápio e o link do sistema online.
    Usa formato WAHA: file.{url|data} (422 ocorria com campo 'image').
    """
    import os
    import base64
    import time

    try:
        from config import WEBHOOK_PUBLIC_URL
        url_base = (WEBHOOK_PUBLIC_URL or "https://pastelaobhoters.chatboot.cloud").rstrip('/')

        api_url = f"{WAHA_API_URL}/sendImage"
        headers = {"Content-Type": "application/json", "X-Api-Key": WAHA_API_KEY}

        # 1) Tentar via URL pública (WAHA baixa a imagem)
        img_url = f"{url_base}/img/cardapio.jpeg"
        payload_url = {
            "chatId": chat_id,
            "session": WAHA_SESSION,
            "file": {"mimetype": "image/jpeg", "url": img_url, "filename": "cardapio.jpeg"},
            "caption": "📋 *Cardápio Pastelão Brothers*"
        }
        resp = requests.post(api_url, json=payload_url, headers=headers, timeout=30)
        if resp.status_code not in (200, 201):
            print(f"[waha] sendImage URL falhou {resp.status_code}: {resp.text[:400]}", file=sys.stderr)
        if resp.status_code in (200, 201):
            time.sleep(0.8)
            msg_link = f"Se preferir, pode acessar nosso cardápio online e fazer o pedido por lá:\n\n🌐 {url_base}"
            enviar_mensagem_texto(chat_id, msg_link)
            print(f"[waha] Cardápio em foto enviado (URL) para {chat_id}", file=sys.stderr)
            return {'success': True, 'mensagem': 'Cardápio enviado'}

        # 2) Fallback: base64 do arquivo local (formato file.data)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for fname in ('cardapio.jpeg', 'cardapio.jpg', 'cardapio.png'):
            img_path = os.path.normpath(os.path.join(base_dir, '..', 'frontend', 'img', fname))
            if os.path.isfile(img_path):
                with open(img_path, 'rb') as f:
                    img_b64 = base64.b64encode(f.read()).decode('utf-8')
                payload_b64 = {
                    "chatId": chat_id,
                    "session": WAHA_SESSION,
                    "file": {"mimetype": "image/jpeg", "data": img_b64, "filename": "cardapio.jpeg"},
                    "caption": "📋 *Cardápio Pastelão Brothers*"
                }
                resp = requests.post(api_url, json=payload_b64, headers=headers, timeout=30)
                if resp.status_code in (200, 201):
                    time.sleep(0.8)
                    msg_link = f"Se preferir, pode acessar nosso cardápio online e fazer o pedido por lá:\n\n🌐 {url_base}"
                    enviar_mensagem_texto(chat_id, msg_link)
                    print(f"[waha] Cardápio em foto enviado (base64) para {chat_id}", file=sys.stderr)
                    return {'success': True, 'mensagem': 'Cardápio enviado'}
                print(f"[waha] sendImage base64: {resp.status_code} {resp.text[:300]}", file=sys.stderr)
                return {'erro': f'Falha ao enviar imagem: {resp.status_code}'}

        return {'erro': 'Imagem do cardápio não encontrada'}
    except Exception as e:
        print(f"[waha] Erro ao enviar cardápio: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {'erro': str(e)}


def enviar_imagem_base64(chat_id, imagem_base64, legenda=""):
    """
    Envia imagem via WhatsApp usando WAHA API (base64)
    
    Args:
        chat_id (str): ID do chat
        imagem_base64 (str): Imagem em base64 (com ou sem prefixo data:image/png;base64,)
        legenda (str): Legenda da imagem
    
    Returns:
        dict: Resposta da API com sucesso ou erro
    """
    try:
        # Remover prefixo se existir
        if imagem_base64.startswith('data:image'):
            imagem_base64 = imagem_base64.split(',')[1]
        
        url = f"{WAHA_API_URL}/sendImage"
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": WAHA_API_KEY
        }
        payload = {
            "chatId": chat_id,
            "image": imagem_base64,
            "caption": legenda,
            "session": WAHA_SESSION
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return {
                'success': True,
                'message': 'Imagem enviada com sucesso',
                'data': response.json()
            }
        else:
            return {
                'success': False,
                'error': f'Erro ao enviar imagem: {response.status_code}',
                'details': response.text
            }
            
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar imagem WhatsApp: {e}", file=sys.stderr)
        return {
            'success': False,
            'error': f'Erro de conexão: {str(e)}'
        }
    except Exception as e:
        print(f"Erro inesperado ao enviar imagem WhatsApp: {e}", file=sys.stderr)
        return {
            'success': False,
            'error': f'Erro inesperado: {str(e)}'
        }

def enviar_qr_code_pix(chat_id, qr_code_base64, valor_total, pedido_id):
    """
    Envia QR Code do PIX via WhatsApp
    
    Args:
        chat_id (str): ID do chat
        qr_code_base64 (str): QR Code em base64
        valor_total (float): Valor total do pedido
        pedido_id (int): ID do pedido
    
    Returns:
        dict: Resposta da API
    """
    legenda = f"""
🎉 *Pedido #{pedido_id} Criado!*

💰 *Valor Total: R$ {valor_total:.2f}*

📱 Escaneie o QR Code abaixo para pagar via PIX:

⏰ O pagamento será confirmado automaticamente após a aprovação.

Obrigado pela preferência! 🥟
    """.strip()
    
    return enviar_imagem_base64(chat_id, qr_code_base64, legenda)

def enviar_notificacao_pedido_criado(chat_id, pedido_id, total, itens_descricao):
    """
    Envia notificação de pedido criado
    
    Args:
        chat_id (str): ID do chat
        pedido_id (int): ID do pedido
        total (float): Valor total
        itens_descricao (list): Lista de descrições dos itens
    
    Returns:
        dict: Resposta da API
    """
    itens_texto = "\n".join([f"  • {item}" for item in itens_descricao])
    
    mensagem = f"""
✅ *Pedido #{pedido_id} Criado com Sucesso!*

📦 *Itens do Pedido:*
{itens_texto}

💰 *Valor Total: R$ {total:.2f}*

⏳ Aguardando pagamento...

Em breve você receberá o QR Code do PIX para pagamento.
    """.strip()
    
    return enviar_mensagem_texto(chat_id, mensagem)

def enviar_confirmacao_pagamento(chat_id, pedido_id, total):
    """
    Envia confirmação de pagamento aprovado
    
    Args:
        chat_id (str): ID do chat
        pedido_id (int): ID do pedido
        total (float): Valor total
    
    Returns:
        dict: Resposta da API
    """
    mensagem = f"""
🎉 *Pagamento Confirmado!*

✅ Seu pedido #{pedido_id} foi pago com sucesso!

💰 *Valor: R$ {total:.2f}*

👨‍🍳 Seu pedido está sendo preparado e em breve estará pronto!

Acompanhe o status do seu pedido em nosso sistema.

Obrigado pela preferência! 🥟
    """.strip()
    
    return enviar_mensagem_texto(chat_id, mensagem)

def obter_whatsapp_id_do_cliente(cliente_id, db_config=None):
    """
    Obtém o WhatsApp ID do cliente a partir do banco de dados
    
    Args:
        cliente_id (int): ID do cliente
        db_config (dict): Configuração do banco (opcional)
    
    Returns:
        str: WhatsApp ID ou None se não encontrado
    """
    try:
        import mysql.connector
        from mysql.connector import Error
        
        if not db_config:
            from config import DB_CONFIG
            db_config = DB_CONFIG
        
        conn = mysql.connector.connect(**db_config)
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        
        # Buscar telefone do cliente
        cursor.execute("SELECT telefone FROM usuarios WHERE id = %s", (cliente_id,))
        cliente = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if cliente and cliente.get('telefone'):
            telefone = cliente['telefone']
            # Limpar telefone (remover caracteres não numéricos)
            telefone_limpo = ''.join(filter(str.isdigit, telefone))
            
            # Formatar como WhatsApp ID (adicionar @c.us se necessário)
            if not '@' in telefone_limpo:
                # Se não tem @, assumir formato brasileiro e adicionar @c.us
                if telefone_limpo.startswith('55'):
                    return f"{telefone_limpo}@c.us"
                else:
                    # Se não começa com 55, adicionar código do país
                    return f"55{telefone_limpo}@c.us"
            
            return telefone_limpo
        
        return None
        
    except Exception as e:
        print(f"Erro ao obter WhatsApp ID do cliente: {e}", file=sys.stderr)
        return None
