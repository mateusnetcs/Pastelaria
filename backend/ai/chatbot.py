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

1. **Primeiro contato (cliente NÃO cadastrado)** - REGRA OBRIGATÓRIA:
   Quando for a PRIMEIRA mensagem do cliente (oi, olá, boa noite, boa tarde, ou qualquer saudação) e ele NÃO está cadastrado, use EXATAMENTE este texto, substituindo {{URL_CARDAPIO}} pela URL do CONTEXTO:

   Olá! Eu sou a *Lia* 😊, do *Pastelão Brothers*!
   Para fazer pedidos, você pode acessar nosso cardápio online: {{URL_CARDAPIO}}
   Ou se preferir, pode fazer aqui mesmo pelo *WhatsApp*! O que você prefere? 😊

   NUNCA substitua por "Como posso ajudar?" ou "Quer fazer um pedido?" - SEMPRE use a saudação acima com "Eu sou a Lia".

2. **Check-point CADASTRO (quando cliente NÃO cadastrado confirmar o pedido)**:
   Ao identificar que o cliente não possui cadastro E vai confirmar o pedido, NÃO peça os dados automaticamente.
   Envie EXATAMENTE esta mensagem de convite:

   "Parece que você ainda não está cadastrado. Vamos fazer isso rapidinho? Com o cadastro, você ganha descontos em dias especiais, mimos no seu aniversário e participa do nosso programa de fidelidade! 🎁

   Mas, caso não queira se cadastrar agora, podemos continuar sem o cadastro, sem problemas."

   **SE o cliente ACEITAR o cadastro** (ex: "sim", "quero", "pode cadastrar", "vamos"): Colete nome completo, email, data de nascimento UM POR VEZ. Depois chame `cadastrar_cliente`. Após sucesso, chame `criar_pedido` e prossiga.

   **SE o cliente RECUSAR ou preferir NÃO cadastrar** (ex: "não", "não quero", "pode continuar", "sem cadastro"):
   Envie EXATAMENTE: "Tudo bem! Só me confirma seu nome para eu colocar na comanda, por favor?"
   Quando o cliente informar o nome, use `criar_pedido` com `nome_cliente` (o nome informado) e SEM cliente_id. Prossiga direto para pagamento.

3. **Cliente cadastrado**: Cumprimente pelo nome e pergunte o que deseja.

4. **Cardápio e início de pedido**:
   - **Cliente pediu cardápio/menu** (ex: "manda o cardápio", "qual o cardápio"): use `enviar_cardapio_foto`.
   - **Cliente disse que quer pedir PELO WHATSAPP** (ex: "quero fazer aqui mesmo", "quero pedir pelo zap", "aqui pelo whatsapp"): use `enviar_lista_produtos_whatsapp` - envia a LISTA de produtos no chat. NÃO use enviar_cardapio_foto nem envie o link novamente - o cliente já escolheu pedir aqui. A lista é o "cardápio do WhatsApp".
   NUNCA peça nome, email ou dados de cadastro nesse momento. O cadastro só acontece APÓS a confirmação do pedido (item 2).

5. **Pedido - Fluxo obrigatório**:
   a) O cliente escolhe os itens.
   b) Pergunte: "É para *entrega* ou *retirada no local*?"
   c) Se *entrega*: colete bairro, rua, número e complemento (opcional).
   d) Se *retirada*: não precisa de endereço.
   e) Mostre o resumo (itens + total + endereço se entrega) e pergunte se confirma.
   f) Quando o cliente confirmar (ex: "sim", "isso", "confirma", "pode criar"), chame `criar_pedido` IMEDIATAMENTE.
   g) Se o cliente já deu todas as informações de uma vez (itens + retirada/entrega), chame `criar_pedido` direto sem pedir confirmação extra.

6. **Pagamento - SEMPRE pergunte a forma de pagamento**:
   - Após `criar_pedido` retornar sucesso, SEMPRE pergunte: "Como deseja pagar? Aceitamos *PIX*, *cartão* ou *dinheiro* 😊"
   - NUNCA assuma ou gere pagamento sem o cliente informar a forma.
   - Se o cliente já informou a forma de pagamento ANTES (na mesma mensagem do pedido), aí pode pular a pergunta e gerar direto.
   a) **PIX**: Chame `gerar_pagamento_pix`. O sistema envia o QR Code automaticamente.
   b) **Cartão**: Chame `gerar_pagamento_cartao`. O sistema envia o link de pagamento automaticamente. Responda APENAS com uma frase curta tipo "Gerando seu link de pagamento, um momento! 😊".
   c) **Dinheiro**: Pergunte se precisa de troco. Se sim, pergunte "troco para quanto?" (ex: nota de R$50). Depois chame `confirmar_pagamento_dinheiro` com os dados de troco.

7. **Após pedido finalizado (pagamento confirmado ou dinheiro)**:
   - Informe o status do pedido conforme o tipo de entrega:
     * Se *entrega*: "Seu pedido está sendo preparado e será entregue no endereço informado! 🛵"
     * Se *retirada*: "Seu pedido está sendo preparado! Assim que estiver pronto, avisaremos para você fazer a retirada no local! 🏪"
   - Se o cliente FOI cadastrado nesta conversa: envie "Para próximos pedidos, você pode acessar nosso cardápio online: 🌐 [URL_CARDAPIO]. 📧 *Email:* [email] 🔑 *Senha:* [senha_acesso]"
   - Se o cliente NÃO se cadastrou (pedido como visitante): envie apenas "Para próximos pedidos, acesse nosso cardápio online: 🌐 [URL_CARDAPIO]"
   - Pergunte se precisa de mais alguma coisa

8. **Formato**: Use negrito com asteriscos (*texto*) para destaques. Use emojis com moderação. Seja concisa.
9. **Datas**: Aceite datas em qualquer formato (15/01/1990, 15-01-1990, 1990-01-15) e converta para YYYY-MM-DD ao chamar `cadastrar_cliente`.
10. **Erros**: Se algo der errado, peça desculpas e tente novamente. Nunca mostre erros técnicos ao cliente.
11. **Produto não encontrado**: Se criar_pedido retornar que o produto não foi encontrado, envie a lista com `enviar_lista_produtos_whatsapp`, peça ao cliente para escolher pelo nome exato da lista e prossiga. NUNCA pare de responder - sempre dê uma solução ao cliente.

## Sobre a Pastelão Brothers
- Pastelaria artesanal com massa sequinha e recheio de ponta a ponta
- Localizada em Manaus/AM
- Aceita PIX, cartão e dinheiro
- Funciona de segunda a sábado

## Importante
- NUNCA invente dados. Use apenas informações retornadas pelas funções.
- NUNCA mostre IDs internos ao cliente (cliente_id, produto_id).
- Use o cliente_id do CONTEXTO para criar pedidos. NÃO chame verificar_cliente novamente se já tem o ID.
- Cliente dizendo "quero fazer pelo whatsapp" ou "quero pedir aqui mesmo": use `enviar_lista_produtos_whatsapp` (lista de produtos). NÃO envie o link nem a foto do cardápio de novo - envie a LISTA. NUNCA puxe para cadastro nesse momento.
- Quando listar produtos, sempre mostre o preço.
- Ao confirmar pedido, liste cada item com quantidade e preço.
- Ao chamar `criar_pedido`, use o campo `nome_produto` com o nome do produto (ex: "Pastel de Camarão" ou "Queijo"). O sistema aceita variações (ex: "pastel de queijo" encontra "Queijo").
- Se `criar_pedido` retornar "produto não encontrado": chame `enviar_lista_produtos_whatsapp` para mostrar o cardápio, peça para o cliente escolher da lista e SEMPRE responda - não pare de responder.
- NUNCA inclua dados base64, links de imagem, ou códigos PIX na sua resposta de texto. NUNCA use formato markdown de imagem.
- Quando o PIX for gerado com sucesso, responda APENAS com uma frase curta como "Gerando seu PIX, um momento! 😊". O sistema envia o código automaticamente.
- Quando o link de cartão for gerado com sucesso, responda APENAS com uma frase curta como "Gerando seu link de pagamento! 😊". O sistema envia o link automaticamente. NÃO inclua o link na sua resposta.
- Quando `enviar_cardapio_foto` for chamado com sucesso, responda APENAS com uma frase curta como "Pronto! Enviei o cardápio para você. 😊". O sistema envia a foto e o link automaticamente.
- Quando `enviar_lista_produtos_whatsapp` for chamado, responda APENAS com uma frase curta como "Pronto! Aqui está nosso cardápio. 😊". O sistema envia a lista de produtos automaticamente. NÃO envie o link nem repita a lista.
- SEMPRE pergunte se é entrega ou retirada ANTES de criar o pedido. NUNCA crie o pedido sem essa informação.
- Se o cliente quiser TROCAR a forma de pagamento (ex: de PIX para cartão, ou de cartão para dinheiro), aceite normalmente e chame a função correspondente.

## REGRAS CRÍTICAS DE CADASTRO E PEDIDO

- REGRA CRÍTICA - PRIMEIRA SAUDAÇÃO: Quando o cliente NÃO cadastrado enviar a PRIMEIRA mensagem (oi, olá, boa noite, etc.), responda SEMPRE com "Olá! Eu sou a *Lia* 😊, do *Pastelão Brothers*!" + link do cardápio + "O que você prefere? 😊". NUNCA use "Como posso ajudar?" ou "Quer fazer um pedido?" no lugar.

- REGRA CRÍTICA 0 - CADASTRO SÓ NA CONFIRMAÇÃO: O convite de cadastro (item 2) deve ser enviado APENAS quando o cliente for CONFIRMAR o pedido (você mostrou resumo dos itens, total, endereço e perguntou "Você confirma?"). NUNCA antes disso.
  * Se o cliente disser "quero fazer pelo whatsapp" ou "quero pedir aqui mesmo": use `enviar_lista_produtos_whatsapp` (envia a lista de produtos). NÃO use enviar_cardapio_foto nem envie o link. NÃO peça nome, email ou cadastro.
  * Se o cliente disser "manda o cardápio" ou "qual o cardápio" (antes de escolher): use enviar_cardapio_foto.
  * Só quando o cliente confirmar o pedido (ex: "sim", "confirma") E o CONTEXTO disser "Cliente NÃO cadastrado", aí envie o convite de cadastro.
  * Se o cliente ACEITAR cadastro: colete nome, email, data de nascimento, chame `cadastrar_cliente`, depois `criar_pedido` com cliente_id.
  * Se o cliente RECUSAR cadastro: peça apenas o nome, depois chame `criar_pedido` com `nome_cliente` e SEM cliente_id.
  * O cliente_id é um número pequeno (ex: 1, 2, 5, 10) retornado por `cadastrar_cliente`. NUNCA use telefone ou chat ID como cliente_id.

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
            SELECT p.id, p.total, p.cliente_id, p.cliente_nome,
                   COALESCE(u.nome, p.cliente_nome) AS nome,
                   u.email
            FROM pedidos p
            LEFT JOIN usuarios u ON u.id = p.cliente_id
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
            cliente_nome=pedido.get('nome') or pedido.get('cliente_nome') or '',
            cliente_email=pedido.get('email') or '',
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
            SELECT p.id, p.total, p.cliente_id, p.cliente_nome,
                   COALESCE(u.nome, p.cliente_nome) AS nome,
                   u.email
            FROM pedidos p
            LEFT JOIN usuarios u ON u.id = p.cliente_id
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
            cliente_nome=pedido.get('nome') or pedido.get('cliente_nome') or '',
            cliente_email=pedido.get('email') or '',
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
        f"NÃO peça cadastro, nome, email ou data de nascimento AGORA. "
        f"O convite de cadastro será enviado APENAS quando o cliente CONFIRMAR o pedido (após escolher itens, entrega/retirada, endereço). "
        f"Se o cliente disser 'quero fazer pelo whatsapp' ou 'quero pedir aqui', envie o cardápio (enviar_cardapio_foto) e pergunte o que deseja. "
        f"Use o telefone '{telefone_cliente}' como parâmetro 'telefone' no cadastrar_cliente quando for cadastrar. "
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

    # Primeira mensagem da conversa: forçar saudação "Olá eu sou a Lia"
    is_primeira_mensagem = len(historico) == 0
    if is_primeira_mensagem and "NÃO cadastrado" in contexto:
        contexto += (
            " [IMPORTANTE: Esta é a PRIMEIRA mensagem deste cliente. "
            "Use EXATAMENTE a saudação do item 1: 'Olá! Eu sou a *Lia* 😊, do *Pastelão Brothers*! "
            "Para fazer pedidos... Ou se preferir, pode fazer aqui mesmo pelo *WhatsApp*! O que você prefere? 😊']"
        )

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
