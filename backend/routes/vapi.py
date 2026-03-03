"""
Rotas para integração com Vapi.ai (atendimento por telefone).
Recebe tool calls do Vapi e executa as mesmas funções do WhatsApp.
"""

from flask import Blueprint, request, jsonify
import json
import sys

from config import DB_CONFIG
from ai.tools import (
    listar_produtos, criar_pedido, cadastrar_cliente,
    verificar_cliente, confirmar_pagamento_dinheiro,
    get_db_connection
)

vapi_bp = Blueprint('vapi', __name__)


def _buscar_ou_cadastrar_cliente_telefone(telefone, nome=None):
    """Busca cliente pelo telefone. Se não existir e tiver nome, cadastra."""
    telefone_limpo = ''.join(filter(str.isdigit, telefone))
    if not telefone_limpo:
        return None

    info = verificar_cliente(telefone_limpo, DB_CONFIG)
    if info.get("cliente_existe"):
        return info

    return None


def _executar_tool_vapi(tool_name, arguments, call_info):
    """Executa uma tool e retorna o resultado como string."""
    telefone_chamada = ""
    if call_info:
        customer = call_info.get("customer", {})
        telefone_chamada = customer.get("number", "")
        if not telefone_chamada:
            phone_number = call_info.get("phoneNumber", {})
            telefone_chamada = phone_number.get("number", "")

    telefone_limpo = ''.join(filter(str.isdigit, telefone_chamada))

    if tool_name == "listar_produtos":
        resultado = listar_produtos(DB_CONFIG, arguments.get("categoria"))
        if resultado.get("produtos"):
            produtos = resultado["produtos"]
            linhas = []
            cat_atual = ""
            for p in produtos:
                if p.get("categoria") != cat_atual:
                    cat_atual = p.get("categoria", "")
                    linhas.append(f"\n{cat_atual}:")
                linhas.append(f"  - {p['nome']}: R$ {p['preco']:.2f}")
            return "Cardápio da Pastelão Brothers:\n" + "\n".join(linhas)
        return "Não há produtos disponíveis no momento."

    elif tool_name == "verificar_cliente":
        tel = arguments.get("telefone", telefone_limpo)
        info = verificar_cliente(tel, DB_CONFIG)
        if info.get("cliente_existe"):
            return f"Cliente encontrado: {info['nome']} (ID: {info['cliente_id']})"
        return "Cliente não cadastrado."

    elif tool_name == "cadastrar_cliente":
        resultado = cadastrar_cliente(
            arguments.get("nome", ""),
            arguments.get("email", ""),
            arguments.get("telefone", telefone_limpo),
            DB_CONFIG,
            arguments.get("data_nascimento")
        )
        if resultado.get("sucesso"):
            return (
                f"Cliente {resultado['nome']} cadastrado com sucesso! "
                f"ID: {resultado['cliente_id']}. "
                f"Senha de acesso ao cardápio online: {resultado.get('senha_acesso', '')}"
            )
        return f"Erro ao cadastrar: {resultado.get('erro', 'erro desconhecido')}"

    elif tool_name == "criar_pedido":
        cliente_nome = arguments.get("cliente_nome", "")
        cliente_telefone = arguments.get("cliente_telefone", telefone_limpo)
        itens_texto = arguments.get("itens", "")
        tipo_entrega = arguments.get("tipo_entrega", "retirada")
        endereco_texto = arguments.get("endereco", "")
        pagamento = arguments.get("pagamento", "")
        troco_para = arguments.get("troco_para")

        tel_busca = ''.join(filter(str.isdigit, cliente_telefone))
        info = verificar_cliente(tel_busca, DB_CONFIG)

        cliente_id = None
        if info.get("cliente_existe"):
            cliente_id = info["cliente_id"]
        else:
            if cliente_nome:
                email_auto = f"{tel_busca}@telefone.local"
                reg = cadastrar_cliente(cliente_nome, email_auto, tel_busca, DB_CONFIG)
                if reg.get("sucesso"):
                    cliente_id = reg["cliente_id"]

        if not cliente_id:
            return "Não foi possível identificar o cliente. Pergunte o nome para cadastrar."

        itens_lista = []
        if isinstance(itens_texto, str):
            for parte in itens_texto.split(","):
                parte = parte.strip()
                if not parte:
                    continue
                qtd = 1
                nome_prod = parte
                for sep in [" x", " X", " x ", " X "]:
                    if sep in parte:
                        partes = parte.rsplit(sep.strip(), 1)
                        nome_prod = partes[0].strip()
                        try:
                            qtd = int(partes[1].strip())
                        except ValueError:
                            qtd = 1
                        break
                itens_lista.append({"nome_produto": nome_prod, "quantidade": qtd})
        elif isinstance(itens_texto, list):
            for item in itens_texto:
                if isinstance(item, dict):
                    itens_lista.append(item)
                else:
                    itens_lista.append({"nome_produto": str(item), "quantidade": 1})

        if not itens_lista:
            return "Nenhum item válido informado. Pergunte novamente o que o cliente deseja."

        endereco_obj = None
        if tipo_entrega == "entrega" and endereco_texto:
            endereco_obj = {"endereco_completo": endereco_texto}

        chat_id_vapi = f"vapi_{tel_busca}"

        resultado = criar_pedido(
            itens_lista, DB_CONFIG,
            whatsapp_id=chat_id_vapi,
            tipo_entrega=tipo_entrega,
            endereco=endereco_obj,
            cliente_id=cliente_id,
            nome_cliente=None
        )

        if resultado.get("sucesso"):
            pedido_id = resultado["pedido_id"]
            total = resultado["total"]
            resposta = f"Pedido #{pedido_id} criado! Total: R$ {total:.2f}. Itens: {', '.join(resultado.get('itens', []))}."

            if pagamento == "dinheiro":
                res_din = confirmar_pagamento_dinheiro(
                    pedido_id, DB_CONFIG,
                    chat_id=chat_id_vapi,
                    precisa_troco=bool(troco_para),
                    troco_para=troco_para
                )
                if res_din.get("sucesso"):
                    resposta += f" Pagamento em dinheiro confirmado."
                    if troco_para:
                        troco = round(troco_para - total, 2)
                        resposta += f" Troco de R$ {troco:.2f} para nota de R$ {troco_para:.2f}."
            elif pagamento == "pix":
                resposta += " O cliente receberá o código PIX no WhatsApp. Se não tiver WhatsApp cadastrado, informe que pode pagar na entrega."
            elif pagamento == "cartao":
                resposta += " O cliente receberá o link de pagamento por cartão no WhatsApp."

            return resposta

        return f"Erro ao criar pedido: {resultado.get('erro', 'erro desconhecido')}"

    else:
        return f"Função '{tool_name}' não reconhecida."


@vapi_bp.route('/api/vapi/tool', methods=['POST'])
def vapi_tool_webhook():
    """
    Endpoint que recebe tool calls do Vapi.ai.

    Formato de entrada:
    {
        "message": {
            "type": "tool-calls",
            "toolCallList": [{"id": "...", "name": "...", "arguments": {...}}],
            "call": {"id": "...", "customer": {"number": "+55..."}}
        }
    }

    Formato de saída:
    {
        "results": [{"toolCallId": "...", "result": "..."}]
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({"results": []}), 200

        message = data.get("message", {})
        msg_type = message.get("type", "")

        if msg_type != "tool-calls":
            return jsonify({"results": []}), 200

        tool_call_list = message.get("toolCallList", [])
        call_info = message.get("call", {})

        print(f"[vapi] Recebido {len(tool_call_list)} tool call(s)", file=sys.stderr)
        print(f"[vapi] Raw toolCallList: {json.dumps(tool_call_list, ensure_ascii=False)[:500]}", file=sys.stderr)

        tool_with_list = message.get("toolWithToolCallList", [])

        results = []
        for i, tool_call in enumerate(tool_call_list):
            tc_id = tool_call.get("id", "")
            tc_name = tool_call.get("name", "")
            tc_args = tool_call.get("arguments", {})

            if not tc_name:
                fn = tool_call.get("function", {})
                tc_name = fn.get("name", "")
                tc_args = fn.get("arguments", fn.get("parameters", {}))
                if isinstance(tc_args, str):
                    try:
                        tc_args = json.loads(tc_args)
                    except (json.JSONDecodeError, TypeError):
                        tc_args = {}

            if not tc_name and i < len(tool_with_list):
                twt = tool_with_list[i]
                if isinstance(twt, dict):
                    tc_name = twt.get("name", twt.get("function", {}).get("name", ""))
                    tc_call = twt.get("toolCall", {})
                    if not tc_id:
                        tc_id = tc_call.get("id", "")
                    fn_in_tc = tc_call.get("function", {})
                    if not tc_args or tc_args == {}:
                        tc_args = fn_in_tc.get("parameters", fn_in_tc.get("arguments", {}))
                        if isinstance(tc_args, str):
                            try:
                                tc_args = json.loads(tc_args)
                            except (json.JSONDecodeError, TypeError):
                                tc_args = {}

            print(f"[vapi] Tool: {tc_name}({json.dumps(tc_args, ensure_ascii=False)[:200]})", file=sys.stderr)

            try:
                result_str = _executar_tool_vapi(tc_name, tc_args, call_info)
            except Exception as e:
                print(f"[vapi] Erro ao executar {tc_name}: {e}", file=sys.stderr)
                result_str = "Desculpe, tive um problema ao processar. Pode repetir?"

            results.append({
                "toolCallId": tc_id,
                "result": result_str
            })

            print(f"[vapi] Resultado {tc_name}: {result_str[:100]}...", file=sys.stderr)

        return jsonify({"results": results}), 200

    except Exception as e:
        print(f"[vapi] Erro no webhook: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({"results": []}), 200
