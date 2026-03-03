"""
Motor principal do chatbot com OpenAI.
Processa mensagens do WhatsApp usando function calling.
"""
from openai import OpenAI
import json
import sys

from ai.memory import carregar_historico, salvar_mensagem
from ai.tools import TOOLS_DEFINITIONS, executar_tool, verificar_cliente

SYSTEM_PROMPT = """Você é a atendente virtual da *Pastelão Brothers* no WhatsApp.
Seu nome é *Lia*. Você é simpática, eficiente e fala de forma natural (informal mas educada).

## Regras de atendimento

1. **Primeiro contato (cliente NÃO cadastrado)**:
   COPIE EXATAMENTE o texto abaixo, substituindo apenas {{URL_CARDAPIO}} pela URL do CONTEXTO. NÃO mude nenhuma palavra, NÃO adicione nada, NÃO remova nada:

   Olá! Eu sou a *Lia* 😊, do *Pastelão Brothers*!

   Para fazer pedidos, você pode acessar nosso cardápio online:
   {{URL_CARDAPIO}}

   Ou se preferir, pode fazer aqui mesmo pelo *WhatsApp*! O que você prefere? 😊

   REGRAS ABSOLUTAS da saudação:
   - NUNCA diga "atendente virtual"
   - NUNCA diga "melhor pastelaria da cidade"
   - NUNCA diga "massa sequinha e recheio de ponta a ponta"
   - NUNCA peça cadastro na primeira mensagem
   - NUNCA liste passos de como fazer pedido
   - NUNCA omita a URL do cardápio
   - A saudação deve ter APENAS 3 partes: apresentação, link do cardápio, e a pergunta sobre preferência (site ou WhatsApp)
   - Se o cliente escolher WhatsApp, AÍ SIM colete os dados UM POR VEZ: nome completo, email, data de nascimento. Depois use `cadastrar_cliente`.

2. **Cliente cadastrado**: Cumprimente pelo nome e pergunte o que deseja.

3. **Cardápio**: Quando o cliente pedir cardápio, menu ou quiser ver os produtos (ex: "manda o cardápio", "qual o cardápio"), use `enviar_cardapio_foto`. O sistema envia a foto do cardápio e o link online. Responda com algo curto tipo "Pronto! Enviei o cardápio para você. Qualquer dúvida é só perguntar! 😊". Se `enviar_cardapio_foto` retornar erro, use `listar_produtos` como alternativa.

4. **Pedido - Fluxo obrigatório**:
   a) O cliente escolhe os itens.
   b) Pergunte: "É para *entrega* ou *retirada no local*?"
   c) Se *entrega*: colete bairro, rua, número e complemento (opcional).
   d) Se *retirada*: não precisa de endereço.
   e) Mostre o resumo (itens + total + endereço se entrega) e pergunte se confirma.
   f) Quando o cliente confirmar (ex: "sim", "isso", "confirma", "pode criar"), chame `criar_pedido` IMEDIATAMENTE.
   g) Se o cliente já deu todas as informações de uma vez (itens + retirada/entrega), chame `criar_pedido` direto sem pedir confirmação extra.

5. **Pagamento - SEMPRE pergunte a forma de pagamento**:
   - Após `criar_pedido` retornar sucesso, SEMPRE pergunte: "Como deseja pagar? Aceitamos *PIX*, *cartão* ou *dinheiro* 😊"
   - NUNCA assuma ou gere pagamento sem o cliente informar a forma.
   - Se o cliente já informou a forma de pagamento ANTES (na mesma mensagem do pedido), aí pode pular a pergunta e gerar direto.
   a) **PIX**: Chame `gerar_pagamento_pix`. O sistema envia o QR Code automaticamente.
   b) **Cartão**: Chame `gerar_pagamento_cartao`. O sistema envia o link de pagamento automaticamente. Responda APENAS com uma frase curta tipo "Gerando seu link de pagamento, um momento! 😊".
   c) **Dinheiro**: Pergunte se precisa de troco. Se sim, pergunte "troco para quanto?" (ex: nota de R$50). Depois chame `confirmar_pagamento_dinheiro` com os dados de troco.

6. **Após pedido finalizado (pagamento confirmado ou dinheiro)**:
   - Informe o status do pedido conforme o tipo de entrega:
     * Se *entrega*: "Seu pedido está sendo preparado e será entregue no endereço informado! 🛵"
     * Se *retirada*: "Seu pedido está sendo preparado! Assim que estiver pronto, avisaremos para você fazer a retirada no local! 🏪"
   - Envie os dados de acesso ao cardápio online:
     "Para próximos pedidos, você pode acessar nosso cardápio online:
     🌐 [URL_CARDAPIO]
     
     📧 *Email:* [email do cliente]
     🔑 *Senha:* [senha_acesso do CONTEXTO]"
   - A senha_acesso está disponível no CONTEXTO quando o cliente foi cadastrado nesta conversa. Use o campo `senha_acesso` retornado por `cadastrar_cliente`.
   - Pergunte se precisa de mais alguma coisa

7. **Formato**: Use negrito com asteriscos (*texto*) para destaques. Use emojis com moderação. Seja concisa.
8. **Datas**: Aceite datas em qualquer formato (15/01/1990, 15-01-1990, 1990-01-15) e converta para YYYY-MM-DD ao chamar `cadastrar_cliente`.
9. **Erros**: Se algo der errado, peça desculpas e tente novamente. Nunca mostre erros técnicos ao cliente.

## Sobre a Pastelão Brothers
- Pastelaria artesanal com massa sequinha e recheio de ponta a ponta
- Localizada em Manaus/AM
- Aceita PIX, cartão e dinheiro
- Funciona de segunda a sábado

## Importante
- NUNCA invente dados. Use apenas informações retornadas pelas funções.
- NUNCA mostre IDs internos ao cliente (cliente_id, produto_id).
- Use o cliente_id do CONTEXTO para criar pedidos. NÃO chame verificar_cliente novamente se já tem o ID.
- Quando listar produtos, sempre mostre o preço.
- Ao confirmar pedido, liste cada item com quantidade e preço.
- Ao chamar `criar_pedido`, use o campo `nome_produto` com o nome exato do produto (ex: "Pastel de Camarão"). O sistema resolve o ID internamente.
- NUNCA inclua dados base64, links de imagem, ou códigos PIX na sua resposta de texto. NUNCA use formato markdown de imagem.
- Quando o PIX for gerado com sucesso, responda APENAS com uma frase curta como "Gerando seu PIX, um momento! 😊". O sistema envia o código automaticamente.
- Quando o link de cartão for gerado com sucesso, responda APENAS com uma frase curta como "Gerando seu link de pagamento! 😊". O sistema envia o link automaticamente. NÃO inclua o link na sua resposta.
- Quando `enviar_cardapio_foto` for chamado com sucesso, responda APENAS com uma frase curta como "Pronto! Enviei o cardápio para você. 😊". O sistema envia a foto e o link automaticamente. NÃO liste os produtos em texto.
- SEMPRE pergunte se é entrega ou retirada ANTES de criar o pedido. NUNCA crie o pedido sem essa informação.
- Se o cliente quiser TROCAR a forma de pagamento (ex: de PIX para cartão, ou de cartão para dinheiro), aceite normalmente e chame a função correspondente.

## REGRAS CRÍTICAS DE CADASTRO E PEDIDO

- REGRA CRÍTICA 0 - CADASTRO PRIMEIRO: Se o CONTEXTO diz "Cliente NÃO cadastrado", você NÃO TEM um cliente_id válido.
  * NUNCA chame `criar_pedido` sem um cliente_id numérico do banco de dados.
  * O número de telefone ou chat ID NÃO é um cliente_id. O cliente_id é um número pequeno (ex: 1, 2, 5, 10) retornado pelo sistema.
  * Se o cliente ainda não está cadastrado, colete os dados (nome, email, data de nascimento) e chame `cadastrar_cliente` PRIMEIRO.
  * Só depois que `cadastrar_cliente` retornar o `cliente_id`, você pode chamar `criar_pedido` com esse ID.
  * Se o cliente já informou o que quer pedir ANTES de estar cadastrado, memorize o pedido e crie depois do cadastro.

- REGRA CRÍTICA 1: Quando o cliente confirmar o pedido ou já tiver dado todas as informações, você DEVE chamar a função `criar_pedido` NESTA RESPOSTA. NUNCA responda apenas com texto dizendo "vou criar". Se você não chamar a função, o pedido NÃO será criado.

- REGRA CRÍTICA 2: Após `criar_pedido` retornar sucesso:
  * Se o cliente NÃO informou a forma de pagamento → PERGUNTE "Como deseja pagar? *PIX*, *cartão* ou *dinheiro*?"
  * Se o cliente JÁ informou a forma de pagamento na mensagem → chame a função correspondente IMEDIATAMENTE:
    - PIX → chame `gerar_pagamento_pix`
    - Cartão → chame `gerar_pagamento_cartao`
    - Dinheiro e JÁ informou valor do troco → chame `confirmar_pagamento_dinheiro` direto com os dados
    - Dinheiro sem info de troco → pergunte sobre troco, depois chame `confirmar_pagamento_dinheiro`
  NUNCA gere PIX automaticamente sem o cliente pedir. NUNCA assuma a forma de pagamento.

- REGRA CRÍTICA 3 - SENHA DO CLIENTE: Quando `cadastrar_cliente` retornar sucesso, ele inclui o campo `senha_acesso` na resposta.
  * Você DEVE guardar e usar EXATAMENTE esse valor de `senha_acesso` quando for informar as credenciais ao cliente.
  * NUNCA invente uma senha. NUNCA use "123456" ou qualquer outro valor genérico.
  * Use APENAS o valor que veio no campo `senha_acesso` da resposta do `cadastrar_cliente`.

- Priorize SEMPRE chamadas de função em vez de texto quando precisar criar pedido ou gerar pagamento.
"""

MAX_TOOL_CALLS = 5


def _texto_menciona_pix(texto):
    """Verifica se o texto da IA menciona que está GERANDO PIX (não apenas perguntando)."""
    texto_lower = texto.lower()
    if "como deseja pagar" in texto_lower or "forma de pagamento" in texto_lower:
        return False
    indicadores_gerando = ["gerando seu pix", "gerando o pix", "qr code", "qr-code", "código pix"]
    return any(ind in texto_lower for ind in indicadores_gerando)


def _fallback_gerar_pix(chat_id, db_config, telefone_cliente):
    """Busca o último pedido pendente do chat e gera PIX automaticamente."""
    from ai.tools import gerar_pagamento_pix, get_db_connection
    try:
        conn = get_db_connection(db_config)
        if not conn:
            return None

        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.id, p.total, p.cliente_id, u.nome, u.email
            FROM pedidos p
            JOIN usuarios u ON u.id = p.cliente_id
            WHERE p.status = 'pendente'
              AND p.observacoes LIKE %s
            ORDER BY p.id DESC LIMIT 1
        """, (f'%{chat_id}%',))
        pedido = cursor.fetchone()
        cursor.close()
        conn.close()

        if not pedido:
            print(f"[chatbot] Fallback PIX: nenhum pedido pendente para {chat_id}", file=sys.stderr)
            return None

        print(f"[chatbot] Fallback PIX: encontrado pedido #{pedido['id']} (R$ {pedido['total']})", file=sys.stderr)
        resultado = gerar_pagamento_pix(
            pedido_id=pedido['id'],
            valor_total=float(pedido['total']),
            db_config=db_config,
            cliente_nome=pedido.get('nome', ''),
            cliente_email=pedido.get('email', ''),
            chat_id=chat_id
        )

        if isinstance(resultado, str):
            resultado = json.loads(resultado)

        if resultado.get("sucesso") and (resultado.get("qr_code") or resultado.get("qr_code_base64")):
            return resultado
        return None

    except Exception as e:
        print(f"[chatbot] Erro no fallback PIX: {e}", file=sys.stderr)
        return None


def _texto_menciona_cartao(texto):
    """Verifica se o texto da IA menciona que está GERANDO link de cartão (não apenas perguntando)."""
    texto_lower = texto.lower()
    if "como deseja pagar" in texto_lower or "forma de pagamento" in texto_lower:
        return False
    if "pix" in texto_lower and "cartão" in texto_lower and "dinheiro" in texto_lower:
        return False
    indicadores_gerando = ["gerando seu link", "gerando o link", "link de pagamento", "link para pagar"]
    return any(ind in texto_lower for ind in indicadores_gerando)


def _fallback_gerar_cartao(chat_id, db_config):
    """Busca o último pedido pendente do chat e gera link de cartão automaticamente."""
    from ai.tools import gerar_pagamento_cartao, get_db_connection
    try:
        conn = get_db_connection(db_config)
        if not conn:
            return None

        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.id, p.total, p.cliente_id, u.nome, u.email
            FROM pedidos p
            JOIN usuarios u ON u.id = p.cliente_id
            WHERE p.status = 'pendente'
              AND p.observacoes LIKE %s
            ORDER BY p.id DESC LIMIT 1
        """, (f'%{chat_id}%',))
        pedido = cursor.fetchone()
        cursor.close()
        conn.close()

        if not pedido:
            print(f"[chatbot] Fallback cartão: nenhum pedido pendente para {chat_id}", file=sys.stderr)
            return None

        print(f"[chatbot] Fallback cartão: encontrado pedido #{pedido['id']} (R$ {pedido['total']})", file=sys.stderr)
        resultado = gerar_pagamento_cartao(
            pedido_id=pedido['id'],
            valor_total=float(pedido['total']),
            db_config=db_config,
            cliente_nome=pedido.get('nome', ''),
            cliente_email=pedido.get('email', ''),
            chat_id=chat_id
        )

        if isinstance(resultado, str):
            resultado = json.loads(resultado)

        if resultado.get("sucesso") and resultado.get("link_pagamento"):
            return resultado
        return None

    except Exception as e:
        print(f"[chatbot] Erro no fallback cartão: {e}", file=sys.stderr)
        return None


def _buscar_contexto_cliente(telefone_cliente, chat_id, db_config):
    """Busca dados do cliente no banco para injetar como contexto."""
    from config import WEBHOOK_PUBLIC_URL
    url_cardapio = WEBHOOK_PUBLIC_URL or "http://localhost:5000"

    info = verificar_cliente(telefone_cliente, db_config)
    if info.get("cliente_existe"):
        return (
            f"[CONTEXTO INTERNO - NÃO mencione ao cliente] "
            f"Cliente CADASTRADO. cliente_id={info['cliente_id']}, "
            f"nome={info['nome']}, email={info['email']}, "
            f"telefone={info['telefone']}. "
            f"Chat ID WhatsApp: {chat_id}. "
            f"Use este cliente_id={info['cliente_id']} ao criar pedidos. "
            f"ATENÇÃO: o cliente_id é {info['cliente_id']} (número inteiro do banco). "
            f"NÃO confunda com o número de telefone. "
            f"URL_CARDAPIO: {url_cardapio}"
        )
    return (
        f"[CONTEXTO INTERNO - NÃO mencione ao cliente] "
        f"Cliente NÃO cadastrado. Telefone/ChatID: {telefone_cliente}. "
        f"Chat ID WhatsApp: {chat_id}. "
        f"ATENÇÃO: Este cliente NÃO tem cliente_id ainda. "
        f"Você DEVE cadastrar o cliente com `cadastrar_cliente` ANTES de criar qualquer pedido. "
        f"Colete nome, email e data de nascimento. Depois do cadastro, use o cliente_id retornado. "
        f"Use o telefone '{telefone_cliente}' como parâmetro 'telefone' no cadastrar_cliente. "
        f"URL_CARDAPIO: {url_cardapio}"
    )


def processar_mensagem(mensagem_texto, chat_id, telefone_cliente,
                       api_key, model, db_config):
    """
    Processa uma mensagem recebida do WhatsApp e retorna a resposta da IA.

    Returns:
        dict com:
            - resposta (str): texto para enviar ao cliente
            - pix_data (dict|None): dados do QR Code PIX se gerado
            - cartao_data (dict|None): dados do link de pagamento por cartão
    """
    if not api_key or api_key == 'SUA_CHAVE_AQUI':
        return {
            "resposta": "Desculpe, o sistema de atendimento está em manutenção. Tente novamente mais tarde!",
            "pix_data": None,
            "cartao_data": None
        }

    client = OpenAI(api_key=api_key)
    historico = carregar_historico(chat_id, db_config)

    contexto = _buscar_contexto_cliente(telefone_cliente, chat_id, db_config)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": contexto}
    ]

    messages.extend(historico)
    messages.append({"role": "user", "content": mensagem_texto})

    salvar_mensagem(chat_id, "user", mensagem_texto, db_config)

    pix_data = None
    cartao_data = None

    try:
        for _ in range(MAX_TOOL_CALLS):
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS_DEFINITIONS,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1000
            )

            choice = response.choices[0]

            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                messages.append(choice.message)

                for tool_call in choice.message.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = json.loads(tool_call.function.arguments)

                    print(f"[chatbot] Tool call: {fn_name}({fn_args})", file=sys.stderr)

                    resultado = executar_tool(fn_name, fn_args, db_config, chat_id)

                    if fn_name == "gerar_pagamento_pix":
                        try:
                            pix_result = json.loads(resultado)
                            if pix_result.get("sucesso") and (pix_result.get("qr_code") or pix_result.get("qr_code_base64")):
                                pix_data = pix_result
                                print(f"[chatbot] PIX capturado: qr_code={'sim' if pix_result.get('qr_code') else 'nao'}", file=sys.stderr)
                        except json.JSONDecodeError:
                            pass

                    elif fn_name == "gerar_pagamento_cartao":
                        try:
                            cartao_result = json.loads(resultado)
                            if cartao_result.get("sucesso") and cartao_result.get("link_pagamento"):
                                cartao_data = cartao_result
                                print(f"[chatbot] Link cartão capturado: {cartao_result['link_pagamento'][:60]}...", file=sys.stderr)
                        except json.JSONDecodeError:
                            pass

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": resultado
                    })

                continue

            # Resposta final em texto
            resposta_texto = choice.message.content or ""

            # Fallback PIX: se a IA mencionou PIX mas não chamou a função
            if pix_data is None and cartao_data is None and _texto_menciona_pix(resposta_texto):
                pix_data = _fallback_gerar_pix(chat_id, db_config, telefone_cliente)
                if pix_data:
                    print(f"[chatbot] PIX gerado via fallback para pedido #{pix_data.get('pedido_id')}", file=sys.stderr)

            # Fallback Cartão: se a IA mencionou cartão/link mas não chamou a função
            if cartao_data is None and pix_data is None and _texto_menciona_cartao(resposta_texto):
                cartao_data = _fallback_gerar_cartao(chat_id, db_config)
                if cartao_data:
                    print(f"[chatbot] Link cartão gerado via fallback para pedido #{cartao_data.get('pedido_id')}", file=sys.stderr)

            salvar_mensagem(chat_id, "assistant", resposta_texto, db_config)

            return {"resposta": resposta_texto, "pix_data": pix_data, "cartao_data": cartao_data}

        # Se atingiu o limite de tool calls, forçar resposta
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        resposta_texto = response.choices[0].message.content or ""
        salvar_mensagem(chat_id, "assistant", resposta_texto, db_config)
        return {"resposta": resposta_texto, "pix_data": pix_data, "cartao_data": cartao_data}

    except Exception as e:
        print(f"[chatbot] Erro ao processar mensagem: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {
            "resposta": "Desculpe, tive um probleminha aqui. Pode repetir sua mensagem?",
            "pix_data": None,
            "cartao_data": None
        }
