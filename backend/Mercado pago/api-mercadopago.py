import mercadopago
import uuid
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

_access_token = os.getenv('MERCADOPAGO_ACCESS_TOKEN', '')
if not _access_token:
    print("ERRO: MERCADOPAGO_ACCESS_TOKEN não configurado no .env", file=sys.stderr)

sdk = mercadopago.SDK(_access_token)

def criar_pagamento_pix_direto(valor_total, itens, dados_cliente, pedido_id):
    """
    Cria um pagamento Pix direto (não preferência) que retorna QR code imediatamente
    
    Args:
        valor_total (float): Valor total do pedido
        itens (list): Lista de itens do pedido
        dados_cliente (dict): Dados do cliente (nome, email, telefone, endereco)
        pedido_id (int): ID do pedido no banco de dados
    
    Returns:
        dict: QR code Pix e informações do pagamento
    """
    
    # Gerar ID único para a transação
    transaction_id = f"PEDIDO_{pedido_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Limpar e formatar telefone
    telefone_limpo = "".join(filter(str.isdigit, dados_cliente.get("telefone", ""))) if dados_cliente.get("telefone") else ""
    if telefone_limpo and len(telefone_limpo) < 10:
        telefone_limpo = ""
    
    # Criar descrição dos itens
    descricao_itens = " | ".join(itens) if isinstance(itens, list) else str(itens)
    
    webhook_url = os.environ.get('WEBHOOK_PUBLIC_URL', '')
    notification_url = f"{webhook_url}/api/mercadopago/webhook" if webhook_url else None

    payment_data = {
        "transaction_amount": float(valor_total),
        "description": f"Pedido Pastelaria Delícia - #{pedido_id}",
        "payment_method_id": "pix",
        "payer": {
            "email": dados_cliente.get("email"),
            "first_name": dados_cliente.get("nome", "").split()[0] if dados_cliente.get("nome") else "",
            "last_name": " ".join(dados_cliente.get("nome", "").split()[1:]) if dados_cliente.get("nome") and len(dados_cliente.get("nome", "").split()) > 1 else "",
            "identification": {
                "type": "CPF",
                "number": "00000000000"
            }
        },
        "external_reference": transaction_id,
        "notification_url": notification_url,
        "statement_descriptor": "PASTELARIA DELICIA",
        "additional_info": {
            "items": [
                {
                    "id": f"pedido_{pedido_id}",
                    "title": f"Pedido Pastelaria Delícia - #{pedido_id}",
                    "description": descricao_itens[:250],
                    "quantity": 1,
                    "unit_price": float(valor_total)
                }
            ],
            "payer": {
                "first_name": dados_cliente.get("nome", "").split()[0] if dados_cliente.get("nome") else "",
                "last_name": " ".join(dados_cliente.get("nome", "").split()[1:]) if dados_cliente.get("nome") and len(dados_cliente.get("nome", "").split()) > 1 else "",
                "phone": {
                    "area_code": telefone_limpo[:2] if len(telefone_limpo) >= 2 else "92",
                    "number": telefone_limpo[2:] if len(telefone_limpo) > 2 else telefone_limpo
                } if telefone_limpo else None,
                "address": {
                    "zip_code": "69000000",
                    "street_name": dados_cliente.get("rua", "Não informado"),
                    "street_number": str(dados_cliente.get("numero", "S/N"))
                }
            }
        }
    }
    
    try:
        print(f"DEBUG: Criando pagamento Pix DIRETO:", file=sys.stderr)
        print(f"   - Pedido ID: {pedido_id}", file=sys.stderr)
        print(f"   - Valor: {valor_total}", file=sys.stderr)
        
        # Criar pagamento Pix
        result = sdk.payment().create(payment_data)
        
        print(f"DEBUG: Resultado do pagamento Pix:", file=sys.stderr)
        print(f"   - Status: {result.get('status')}", file=sys.stderr)
        
        if result.get("status") == 201:
            payment = result["response"]
            
            # Extrair QR code do Pix
            qr_code = None
            qr_code_base64 = None
            
            if "point_of_interaction" in payment:
                poi = payment["point_of_interaction"]
                if poi and "transaction_data" in poi:
                    transaction_data = poi["transaction_data"]
                    if "qr_code" in transaction_data:
                        qr_code = transaction_data["qr_code"]
                    if "qr_code_base64" in transaction_data:
                        qr_code_base64 = transaction_data["qr_code_base64"]
            
            resultado = {
                "success": True,
                "payment_id": payment.get("id"),
                "status": payment.get("status"),
                "external_reference": transaction_id,
                "qr_code": qr_code,
                "qr_code_base64": qr_code_base64
            }
            
            print(f"DEBUG: QR Code Pix obtido: {qr_code[:50] if qr_code else 'N/A'}...", file=sys.stderr)
            
            return resultado
        else:
            error_msg = result.get("response", {}).get("message", "Erro desconhecido")
            print(f"DEBUG: Erro ao criar pagamento Pix: {error_msg}", file=sys.stderr)
            return {
                "success": False,
                "error": error_msg,
                "details": result.get("response", {})
            }
            
    except Exception as e:
        print(f"ERRO ao criar pagamento Pix: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {
            "success": False,
            "error": str(e)
        }


def gerar_link_pagamento_pedido(valor_total, itens, dados_cliente, pedido_id):
    """
    Gera link de pagamento para pedido da pastelaria
    Tenta criar pagamento Pix direto primeiro, se falhar usa preferência
    
    Args:
        valor_total (float): Valor total do pedido
        itens (list): Lista de itens do pedido
        dados_cliente (dict): Dados do cliente (nome, email, telefone, endereco)
        pedido_id (int): ID do pedido no banco de dados
    
    Returns:
        dict: Link de pagamento e informações da preferência ou QR code Pix
    """
    
    # Verificar se deve forçar preferência (para cartão)
    forcar_preferencia = dados_cliente.get('forcar_preferencia', False)
    
    # Se não forçar preferência, tentar criar pagamento Pix direto primeiro
    if not forcar_preferencia:
        pix_result = criar_pagamento_pix_direto(valor_total, itens, dados_cliente, pedido_id)
        
        if pix_result.get("success") and pix_result.get("qr_code"):
            # Se conseguiu criar pagamento Pix, retornar QR code
            print(f"DEBUG: Pagamento Pix criado com sucesso!", file=sys.stderr)
            return pix_result
    
    # Se falhou ou for cartão, usar preferência
    if forcar_preferencia:
        print(f"DEBUG: Forçando preferência (cartão)", file=sys.stderr)
    else:
        print(f"DEBUG: Pagamento Pix direto falhou, usando preferência como fallback", file=sys.stderr)
    
    # Gerar ID único para a transação
    transaction_id = f"PEDIDO_{pedido_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Configurar opções de requisição
    request_options = mercadopago.config.RequestOptions()
    request_options.custom_headers = {
        'x-idempotency-key': transaction_id
    }
    
    # Limpar e formatar telefone
    telefone_limpo = "".join(filter(str.isdigit, dados_cliente.get("telefone", ""))) if dados_cliente.get("telefone") else ""
    if telefone_limpo and len(telefone_limpo) < 10:
        telefone_limpo = ""
    
    # Garantir endereço mínimo - usar campos separados ou endereco completo
    rua = dados_cliente.get("rua", dados_cliente.get("endereco", "")) or "Não informado"
    numero = dados_cliente.get("numero", "") or "S/N"
    complemento = dados_cliente.get("complemento", "")
    bairro = dados_cliente.get("bairro", "") or "Centro"
    outro = dados_cliente.get("outro", "")
    
    # Montar endereço completo
    endereco = rua
    if numero and numero != "S/N":
        endereco += f", {numero}"
    if complemento:
        endereco += f" - {complemento}"

    webhook_url = os.environ.get('WEBHOOK_PUBLIC_URL', '')

    # Extrair CEP do campo "outro" se disponível
    cep = "69000000"
    if outro:
        # Tentar extrair CEP (8 dígitos)
        cep_digits = "".join(filter(str.isdigit, outro))[:8]
        if len(cep_digits) == 8:
            cep = cep_digits
    elif dados_cliente.get("cep"):
        cep = "".join(filter(str.isdigit, dados_cliente.get("cep", "")))[:8] or "69000000"
    
    # Criar descrição dos itens
    descricao_itens = " | ".join(itens) if isinstance(itens, list) else str(itens)
    
    # Dados da preferência de pagamento
    preference_data = {
        "items": [
            {
                "id": f"pedido_{pedido_id}",
                "title": f"Pedido Pastelaria Delícia - #{pedido_id}",
                "description": descricao_itens[:250],  # Limitar tamanho
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": float(valor_total),
                "picture_url": "https://images.unsplash.com/photo-1626074353765-517a681e40be?q=80&w=600&auto=format&fit=crop"
            }
        ],
        "payer": {
            "email": dados_cliente.get("email"),
            "name": dados_cliente.get("nome", "").strip(),
            "phone": {
                "number": telefone_limpo,
                "area_code": telefone_limpo[:2] if len(telefone_limpo) >= 2 else "92"
            } if telefone_limpo else None,
            "address": {
                "street_name": rua,
                "street_number": str(numero) if numero and numero != "S/N" else "S/N",
                "neighborhood": bairro,
                "city": "Manaus",
                "federal_unit": "AM",
                "zip_code": cep
            }
        },
        "back_urls": {
            "success": "http://localhost:8001/?status=success&pedido=" + str(pedido_id),
            "failure": "http://localhost:8001/?status=failure&pedido=" + str(pedido_id),
            "pending": "http://localhost:8001/?status=pending&pedido=" + str(pedido_id)
        },
        "external_reference": transaction_id,
        "notification_url": f"{webhook_url}/api/mercadopago/webhook" if webhook_url else "http://localhost:5000/api/mercadopago/webhook",
        "statement_descriptor": "PASTELARIA DELICIA",
        "additional_info": f"Pedido #{pedido_id} - Pastelaria Delícia",
        "payment_methods": {
            "excluded_payment_methods": [],
            "excluded_payment_types": [],
            "installments": 12,
            "default_payment_method_id": None,
            "default_installments": None
        }
    }
    
    try:
        print(f"DEBUG: Criando preferencia de PEDIDO com dados:", file=sys.stderr)
        print(f"   - Pedido ID: {pedido_id}", file=sys.stderr)
        print(f"   - Email: {dados_cliente.get('email')}", file=sys.stderr)
        print(f"   - Nome: {dados_cliente.get('nome', '')}", file=sys.stderr)
        print(f"   - Valor total: {valor_total}", file=sys.stderr)
        
        # Criar preferência
        result = sdk.preference().create(preference_data, request_options)
        
        print(f"DEBUG: Resultado do Mercado Pago (PEDIDO):", file=sys.stderr)
        print(f"   - Status: {result.get('status')}", file=sys.stderr)
        if result.get("status") != 201:
            print(f"   - Erro: {result.get('response', {}).get('message', 'Erro desconhecido')}", file=sys.stderr)
            print(f"   - Detalhes: {result.get('response', {})}", file=sys.stderr)
        
        if result["status"] == 201:
            preference = result["response"]
            
            # Extrair QR code se disponível (para Pix)
            qr_code = None
            qr_code_base64 = None
            
            # Verificar se há point_of_interaction (Pix)
            if "point_of_interaction" in preference:
                poi = preference["point_of_interaction"]
                if poi and "transaction_data" in poi:
                    transaction_data = poi["transaction_data"]
                    if "qr_code" in transaction_data:
                        qr_code = transaction_data["qr_code"]
                    if "qr_code_base64" in transaction_data:
                        qr_code_base64 = transaction_data["qr_code_base64"]
            
            resultado = {
                "success": True,
                "init_point": preference["init_point"],
                "id": preference["id"],
                "external_reference": transaction_id,
                "status": "created"
            }
            
            # Adicionar QR code se disponível
            if qr_code:
                resultado["qr_code"] = qr_code
                print(f"DEBUG: QR Code encontrado: {qr_code[:50]}...", file=sys.stderr)
            if qr_code_base64:
                resultado["qr_code_base64"] = qr_code_base64
                print(f"DEBUG: QR Code Base64 encontrado", file=sys.stderr)
            
            return resultado
        else:
            return {
                "success": False,
                "error": "Erro ao criar preferência",
                "details": result
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Erro na integração: {str(e)}"
        }

def verificar_status_pagamento(payment_id):
    """
    Verifica o status de um pagamento
    
    Args:
        payment_id (str): ID do pagamento
    
    Returns:
        dict: Status do pagamento
    """
    try:
        result = sdk.payment().get(payment_id)
        
        if result["status"] == 200:
            payment = result["response"]
            
            return {
                "success": True,
                "status": payment["status"],
                "status_detail": payment["status_detail"],
                "external_reference": payment["external_reference"],
                "transaction_amount": payment["transaction_amount"],
                "date_approved": payment.get("date_approved"),
                "date_created": payment["date_created"]
            }
        else:
            return {
                "success": False,
                "error": "Erro ao consultar pagamento"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Erro na consulta: {str(e)}"
        }

# Exemplo de uso
if __name__ == "__main__":
    import sys
    import json
    
    try:
        # Ler dados do stdin
        input_data = sys.stdin.read()
        if input_data:
            dados = json.loads(input_data)
            
            # Verificar ação solicitada
            if dados.get('action') == 'verificar_status':
                resultado = verificar_status_pagamento(dados['payment_id'])
            elif dados.get('action') == 'criar_pedido':
                dados_cliente = dados.get('dados_cliente', {})
                if dados.get('forcar_preferencia'):
                    dados_cliente['forcar_preferencia'] = True
                resultado = gerar_link_pagamento_pedido(
                    dados['valor_total'],
                    dados['itens'],
                    dados_cliente,
                    dados['pedido_id']
                )
            else:
                resultado = {"success": False, "error": "Ação não reconhecida"}
        else:
            resultado = {"success": False, "error": "Nenhum dado recebido via stdin"}
        
        # Retornar resultado como JSON
        print(json.dumps(resultado, ensure_ascii=False))
        
    except Exception as e:
        erro = {
            "success": False,
            "error": f"Erro no script Python: {str(e)}"
        }
        print(json.dumps(erro, ensure_ascii=False))