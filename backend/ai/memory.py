"""
Gerenciamento de histórico de conversas no MySQL.
Mantém as últimas mensagens de cada chat para contexto da IA.
"""
import mysql.connector
from mysql.connector import Error
import sys

MAX_MESSAGES_PER_CHAT = 30


def get_db_connection(db_config):
    try:
        return mysql.connector.connect(**db_config)
    except Error as e:
        print(f"[memory] Erro ao conectar ao MySQL: {e}", file=sys.stderr)
        return None


def carregar_historico(chat_id, db_config):
    """Carrega as últimas mensagens de um chat."""
    conn = get_db_connection(db_config)
    if not conn:
        return []

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT role, content, tool_call_id
            FROM conversas
            WHERE chat_id = %s
            ORDER BY created_at ASC
            LIMIT %s
        """, (chat_id, MAX_MESSAGES_PER_CHAT))

        mensagens = []
        for row in cursor.fetchall():
            msg = {"role": row["role"], "content": row["content"]}
            if row.get("tool_call_id"):
                msg["tool_call_id"] = row["tool_call_id"]
            mensagens.append(msg)

        cursor.close()
        conn.close()
        return mensagens
    except Exception as e:
        print(f"[memory] Erro ao carregar histórico: {e}", file=sys.stderr)
        if conn:
            conn.close()
        return []


def salvar_mensagem(chat_id, role, content, db_config, tool_call_id=None):
    """Salva uma mensagem no histórico."""
    conn = get_db_connection(db_config)
    if not conn:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversas (chat_id, role, content, tool_call_id)
            VALUES (%s, %s, %s, %s)
        """, (chat_id, role, content or "", tool_call_id))
        conn.commit()

        _limpar_mensagens_antigas(cursor, chat_id)
        conn.commit()

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[memory] Erro ao salvar mensagem: {e}", file=sys.stderr)
        if conn:
            conn.close()


def _limpar_mensagens_antigas(cursor, chat_id):
    """Remove mensagens mais antigas que o limite por chat."""
    cursor.execute("""
        SELECT COUNT(*) as total FROM conversas WHERE chat_id = %s
    """, (chat_id,))
    total = cursor.fetchone()[0]

    if total > MAX_MESSAGES_PER_CHAT:
        excesso = total - MAX_MESSAGES_PER_CHAT
        cursor.execute("""
            DELETE FROM conversas
            WHERE chat_id = %s
            ORDER BY created_at ASC
            LIMIT %s
        """, (chat_id, excesso))


def limpar_conversa(chat_id, db_config):
    """Limpa todo o histórico de um chat."""
    conn = get_db_connection(db_config)
    if not conn:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversas WHERE chat_id = %s", (chat_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[memory] Erro ao limpar conversa: {e}", file=sys.stderr)
        if conn:
            conn.close()
