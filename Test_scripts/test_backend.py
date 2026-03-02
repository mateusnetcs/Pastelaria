#!/usr/bin/env python3
"""
Script de teste para verificar se o backend está funcionando
Execute: python Test_scripts/test_backend.py
"""

import requests
import sys
import json

def test_backend():
    """Testa se o backend está respondendo"""
    base_url = "http://localhost:5000/api"
    
    print("=" * 60)
    print("Teste do Backend - Pastelaria Delícia")
    print("=" * 60)
    print()
    
    # Teste 1: Verificar se o servidor está rodando
    print("1. Testando conexão com o backend...")
    try:
        response = requests.get(f"{base_url}/produtos", timeout=5)
        if response.status_code == 200:
            print("   ✅ Backend está respondendo!")
            data = response.json()
            if data.get('success'):
                produtos = data.get('produtos', [])
                print(f"   ✅ Produtos encontrados: {len(produtos)}")
                if produtos:
                    print(f"   📦 Primeiro produto: {produtos[0].get('nome', 'N/A')}")
                else:
                    print("   ⚠️  Nenhum produto no banco de dados")
            else:
                print(f"   ❌ Erro: {data.get('error', 'Erro desconhecido')}")
        else:
            print(f"   ❌ Erro HTTP: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Erro: Backend não está rodando!")
        print("   💡 Execute: scripts\\iniciar_servidores.bat")
        return False
    except Exception as e:
        print(f"   ❌ Erro: {str(e)}")
        return False
    
    print()
    print("=" * 60)
    print("✅ Teste concluído!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        test_backend()
    except KeyboardInterrupt:
        print("\n\nTeste interrompido pelo usuário.")
        sys.exit(0)
