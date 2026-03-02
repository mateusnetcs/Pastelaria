# 🧪 Scripts de Teste

Esta pasta contém **TODOS** os scripts de teste do projeto.

## 📋 Regras

- ✅ Todos os scripts de teste devem estar aqui
- ✅ Nomes devem começar com `test_`
- ✅ Use unittest ou pytest
- ❌ NUNCA coloque testes em outras pastas

## 📝 Exemplos

### Teste de API
```python
# Test_scripts/test_api.py
import unittest
from backend.app import app

class TestAPI(unittest.TestCase):
    def test_produtos(self):
        client = app.test_client()
        response = client.get('/api/produtos')
        self.assertEqual(response.status_code, 200)
```

### Teste de Banco de Dados
```python
# Test_scripts/test_database.py
import unittest
import mysql.connector

class TestDatabase(unittest.TestCase):
    def test_conexao(self):
        # Teste de conexão
        pass
```

## 🚀 Como Executar

```bash
# Executar todos os testes
python -m unittest discover Test_scripts

# Executar teste específico
python Test_scripts/test_api.py
```
