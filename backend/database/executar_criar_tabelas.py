"""
Script para executar o SQL de criação de tabelas
Senha do banco: 20220015779Ma@
"""

import mysql.connector
from mysql.connector import Error
import os

# Configuração do MySQL
DB_CONFIG = {
    'host': 'localhost',
    'database': 'pastelaria',
    'user': 'root',
    'password': '20220015779Ma@',
    'port': 3306
}

def executar_script_sql():
    """Executa o script SQL para criar todas as tabelas"""
    try:
        # Conectar ao MySQL (sem especificar database primeiro)
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            port=DB_CONFIG['port']
        )
        cursor = conn.cursor()
        print("[OK] Conectado ao MySQL")
        
        # Ler o arquivo SQL
        script_path = os.path.join(os.path.dirname(__file__), 'criar_todas_tabelas.sql')
        
        with open(script_path, 'r', encoding='utf-8') as file:
            sql_script = file.read()
        
        print("[OK] Script SQL carregado")
        
        # Executar o script (dividir por ; e executar cada comando)
        commands = sql_script.split(';')
        
        for i, command in enumerate(commands):
            command = command.strip()
            if command and not command.startswith('--'):
                try:
                    cursor.execute(command)
                    # Consumir resultados se houver
                    try:
                        cursor.fetchall()
                    except:
                        pass
                    print(f"[OK] Comando {i+1} executado")
                except Error as e:
                    # Ignorar erros de "já existe" ou "não existe"
                    if 'already exists' not in str(e).lower() and 'doesn\'t exist' not in str(e).lower() and 'unread result' not in str(e).lower():
                        print(f"[AVISO] Comando {i+1}: {e}")
        
        conn.commit()
        print("\n[OK] Todas as alterações foram commitadas")
        
        # Verificar tabelas criadas
        cursor.execute("USE pastelaria")
        cursor.execute("SHOW TABLES")
        tabelas = cursor.fetchall()
        
        print("\n[OK] Tabelas no banco 'pastelaria':")
        for tabela in tabelas:
            print(f"  - {tabela[0]}")
        
        # Verificar estrutura da tabela usuarios
        cursor.execute("DESCRIBE usuarios")
        colunas = cursor.fetchall()
        
        print("\n[OK] Estrutura da tabela 'usuarios':")
        for coluna in colunas:
            print(f"  - {coluna[0]} ({coluna[1]})")
        
        cursor.close()
        conn.close()
        print("\n[OK] Script executado com sucesso!")
        return True
        
    except Error as e:
        print(f"\n[ERRO] Erro ao executar script: {e}")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("Criando/Atualizando Tabelas no Banco de Dados")
    print("Banco: pastelaria")
    print("=" * 50)
    print()
    
    executar_script_sql()
