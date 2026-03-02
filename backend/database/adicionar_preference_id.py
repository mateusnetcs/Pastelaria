"""
Script para adicionar coluna preference_id na tabela pedidos
Executa diretamente na conexão do backend
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

def adicionar_coluna_preference_id():
    """Adiciona coluna preference_id se não existir"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Verificar se a coluna já existe
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'pastelaria' 
            AND TABLE_NAME = 'pedidos' 
            AND COLUMN_NAME = 'preference_id'
        """)
        
        col_exists = cursor.fetchone()[0]
        
        if col_exists == 0:
            # Adicionar coluna
            cursor.execute("""
                ALTER TABLE pedidos 
                ADD COLUMN preference_id VARCHAR(255) NULL 
                AFTER observacoes
            """)
            conn.commit()
            print("SUCCESS: Coluna preference_id adicionada com sucesso!")
        else:
            print("INFO: Coluna preference_id ja existe")
        
        cursor.close()
        conn.close()
        return True
        
    except Error as e:
        print(f"ERRO ao adicionar coluna: {e}")
        return False

if __name__ == "__main__":
    print("Executando script para adicionar coluna preference_id...")
    adicionar_coluna_preference_id()
