#!/usr/bin/env python3
"""
Servidor HTTP simples para servir o site da Pastelaria Delícia
Execute: python server.py
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

PORT = 8001

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Adicionar headers CORS para permitir requisições do n8n
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def main():
    # Mudar para o diretório do script
    os.chdir(Path(__file__).parent)
    
    # Verificar se o arquivo index.html existe
    if not os.path.exists('index.html'):
        print("❌ Erro: Arquivo 'index.html' não encontrado!")
        print("   Certifique-se de que o arquivo está no mesmo diretório do servidor.")
        return
    
    Handler = MyHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print("=" * 60)
        print("🚀 Servidor da Pastelaria Delícia iniciado!")
        print("=" * 60)
        print(f"📍 URL Local: http://localhost:{PORT}")
        print(f"📍 URL Rede: http://{get_local_ip()}:{PORT}")
        print("=" * 60)
        print("📝 Para conectar do n8n no Docker, use:")
        print(f"   http://host.docker.internal:{PORT}")
        print("=" * 60)
        print("⏹️  Pressione Ctrl+C para parar o servidor")
        print("=" * 60)
        
        # Abrir navegador automaticamente
        try:
            webbrowser.open(f'http://localhost:{PORT}')
        except:
            pass
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n🛑 Servidor parado.")

def get_local_ip():
    """Obtém o IP local da máquina"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

if __name__ == "__main__":
    main()
