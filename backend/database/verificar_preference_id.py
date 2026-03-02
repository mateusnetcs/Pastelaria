"""
Script para verificar se a coluna preference_id existe
"""
import mysql.connector
from mysql.connector import Error

# Configuração do MySQL (mesma do backend)
DB_CONFIG = {
    'host': 'localhost',
    'database': 'pastelaria',
    'user': 'root',
    'password': '20220015779Ma@',
    'port': 3306
}

def verificar_coluna():
    """Verifica se a coluna preference_id existe"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Verificar estrutura da tabela
        cursor.execute("DESCRIBE pedidos")
        colunas = cursor.fetchall()
        
        print("Colunas da tabela pedidos:")
        print("-" * 60)
        for coluna in colunas:
            print(f"  {coluna[0]:20} {coluna[1]:20} {coluna[2]:5} {coluna[3]:5}")
        
        # Verificar especificamente preference_id
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'pastelaria' 
            AND TABLE_NAME = 'pedidos' 
            AND COLUMN_NAME = 'preference_id'
        """)
        
        existe = cursor.fetchone()[0]
        print("-" * 60)
        if existe > 0:
            print("SUCCESS: Coluna preference_id EXISTE")
        else:
            print("ERROR: Coluna preference_id NAO EXISTE")
            print("Adicionando coluna...")
            cursor.execute("""
                ALTER TABLE pedidos 
                ADD COLUMN preference_id VARCHAR(255) NULL 
                AFTER observacoes
            """)
            conn.commit()
            print("SUCCESS: Coluna preference_id adicionada!")
        
        cursor.close()
        conn.close()
        return True
        
    except Error as e:
        print(f"ERRO: {e}")
        return False

if __name__ == "__main__":
    verificar_coluna()
