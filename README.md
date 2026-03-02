# 🥟 Pastelaria Delícia - Sistema de Pedidos Online

Sistema completo de pedidos online com integração WhatsApp, MySQL e Mercado Pago.

## 📁 Estrutura do Projeto

```
whatsapp/
├── frontend/              # Frontend (HTML, CSS, JavaScript)
│   ├── index.html        # Página principal
│   ├── server.py         # Servidor HTTP simples
│   └── server.bat        # Script para iniciar servidor
│
├── backend/               # Backend (Flask API)
│   ├── app.py            # Aplicação Flask principal
│   ├── requirements.txt  # Dependências Python
│   ├── Mercado pago/     # Integração Mercado Pago
│   │   └── api-mercadopago.py
│   └── database/         # Scripts SQL
│       ├── init.sql
│       ├── atualizar_produtos.sql
│       └── ...
│
├── scripts/               # Scripts de automação
│   ├── iniciar_servidores.bat
│   ├── iniciar_servidores.ps1
│   ├── iniciar_servidores_admin.bat
│   ├── parar_servidores.bat
│   └── parar_servidores.ps1
│
├── docs/                  # TODA a documentação (.md)
│   ├── PADROES_CODIGO.md           # Padrões de código e estrutura
│   ├── ESTRUTURA_PROJETO_COMPLETA.md # Estrutura detalhada
│   ├── INSTALACAO_SISTEMA_PEDIDOS.md
│   └── ...
│
├── Test_scripts/          # Scripts de teste
│   ├── README.md
│   └── test_*.py
│
├── docker-compose.yml    # Configuração Docker (WAHA + n8n)
└── README.md             # Este arquivo
```

## 🚀 Início Rápido

### 1. Instalar Dependências

```bash
pip install -r backend/requirements.txt
```

### 2. Configurar Banco de Dados

Execute os scripts SQL em `backend/database/`:
- `init.sql` - Criação inicial do banco
- `criar_tabelas_usuarios.sql` - Tabela de usuários

### 3. Iniciar Servidores

**Opção 1: Script Batch (Recomendado)**
```bash
scripts\iniciar_servidores.bat
```

**Opção 2: Script PowerShell**
```powershell
.\scripts\iniciar_servidores.ps1
```

**Opção 3: Manual**
```bash
# Terminal 1 - Backend
cd backend
python app.py

# Terminal 2 - Frontend
cd frontend
python server.py
```

### 4. Acessar o Sistema

- **Frontend:** http://localhost:8001
- **Backend API:** http://localhost:5000

## 📋 Funcionalidades

### Frontend
- ✅ Sistema de login/cadastro
- ✅ Carrinho de compras
- ✅ Listagem de produtos do MySQL
- ✅ Checkout com Mercado Pago
- ✅ Interface responsiva

### Backend
- ✅ API REST completa
- ✅ Autenticação de usuários
- ✅ Gerenciamento de pedidos
- ✅ Integração com MySQL
- ✅ Integração com Mercado Pago

### Integrações
- ✅ WhatsApp (via WAHA + n8n)
- ✅ MySQL (banco de dados)
- ✅ Mercado Pago (pagamentos)

## 🔧 Configuração

### MySQL
Edite `backend/app.py` e configure:
```python
DB_CONFIG = {
    'host': 'localhost',
    'database': 'pastelaria',
    'user': 'root',
    'password': 'sua_senha',
    'port': 3306
}
```

### Mercado Pago
Edite `backend/Mercado pago/api-mercadopago.py` e configure:
```python
sdk = mercadopago.SDK("SEU_ACCESS_TOKEN")
```

## 📝 Scripts Disponíveis

### Iniciar Servidores
- `scripts/iniciar_servidores.bat` - Inicia backend e frontend
- `scripts/iniciar_servidores.ps1` - Versão PowerShell
- `scripts/iniciar_servidores_admin.bat` - Versão com privilégios admin

### Parar Servidores
- `scripts/parar_servidores.bat` - Para todos os servidores
- `scripts/parar_servidores.ps1` - Versão PowerShell

## 🐛 Troubleshooting

### Porta já em uso
Execute `scripts/parar_servidores.bat` antes de iniciar novamente.

### Erro de conexão MySQL
Verifique se o MySQL está rodando e as credenciais em `backend/app.py`.

### Dependências não instaladas
```bash
pip install -r backend/requirements.txt
```

## 📚 Documentação

Consulte a pasta `docs/` para documentação detalhada:

### 📖 Guias Principais
- **`docs/PADROES_CODIGO.md`** - Padrões de código e estrutura do projeto
- **`docs/ESTRUTURA_PROJETO_COMPLETA.md`** - Estrutura completa do projeto

### 🔧 Guias Técnicos
- `docs/INSTALACAO_SISTEMA_PEDIDOS.md` - Instalação completa
- `docs/MYSQL_SETUP.md` - Configuração MySQL
- `docs/SOLUCAO_ERRO_PORTAS.md` - Troubleshooting

### ⚠️ Regras Importantes
- **TODAS as documentações .md** devem estar em `docs/`
- **Scripts de teste** devem estar em `Test_scripts/`
- **Nenhum arquivo** deve ultrapassar **700 linhas**

## 🎯 Próximos Passos

1. Configure suas credenciais do Mercado Pago
2. Ajuste as configurações do MySQL
3. Personalize o frontend conforme necessário
4. Teste o fluxo completo de pedidos

## 📞 Suporte

Para problemas ou dúvidas, consulte a documentação em `docs/`.
