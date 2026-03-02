#!/usr/bin/env python3
"""
Script para adicionar coluna data_nascimento na tabela usuarios
"""

import mysql.connector
from mysql.connector import Error

# Configuração do MySQL
DB_CONFIG = {
    'host': 'localhost',
    'database': 'pastelaria',
    'user': 'root',
    'password': '20220015779Ma@',
    'port': 3306
}

def executar_script():
    """Executa o script SQL para adicionar data_nascimento"""
    try:
        # Conectar ao banco
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("[OK] Conectado ao banco de dados 'pastelaria'")
        
        # Verificar se coluna já existe
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'pastelaria' 
            AND TABLE_NAME = 'usuarios' 
            AND COLUMN_NAME = 'data_nascimento'
        """)
        
        col_exists = cursor.fetchone()[0]
        
        if col_exists > 0:
            print("[AVISO] Coluna 'data_nascimento' ja existe!")
        else:
            # Adicionar coluna
            cursor.execute("""
                ALTER TABLE usuarios 
                ADD COLUMN data_nascimento DATE AFTER telefone
            """)
            print("[OK] Coluna 'data_nascimento' adicionada com sucesso!")
        
        # Verificar se índice já existe
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.STATISTICS 
            WHERE TABLE_SCHEMA = 'pastelaria' 
            AND TABLE_NAME = 'usuarios' 
            AND INDEX_NAME = 'idx_telefone'
        """)
        
        idx_exists = cursor.fetchone()[0]
        
        if idx_exists > 0:
            print("[AVISO] Indice 'idx_telefone' ja existe!")
        else:
            # Adicionar índice
            cursor.execute("""
                ALTER TABLE usuarios 
                ADD INDEX idx_telefone (telefone)
            """)
            print("[OK] Indice 'idx_telefone' adicionado com sucesso!")
        
        # Commit
        conn.commit()
        
        # Verificar estrutura da tabela
        cursor.execute("DESCRIBE usuarios")
        colunas = cursor.fetchall()
        
        print("\n[INFO] Estrutura da tabela 'usuarios':")
        print("-" * 60)
        for coluna in colunas:
            print(f"  {coluna[0]:20} {coluna[1]:15} {coluna[2]}")
        
        cursor.close()
        conn.close()
        
        print("\n[OK] Script executado com sucesso!")
        
    except Error as e:
        print(f"\n[ERRO] Erro ao executar script: {e}")
        return False
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("Script: Adicionar coluna data_nascimento")
    print("=" * 60)
    print()
    
    sucesso = executar_script()
    
    if sucesso:
        print("\n[SUCESSO] Pronto! Agora voce pode testar o endpoint no n8n.")
    else:
        print("\n[ERRO] Verifique os erros acima e tente novamente.")
