-- Script para corrigir permissões do MySQL
-- Execute este script no MySQL Workbench

-- Permitir conexão do host DESKTOP-3EUF1A3
GRANT ALL PRIVILEGES ON pastelaria.* TO 'root'@'DESKTOP-3EUF1A3' IDENTIFIED BY '20220015779Ma@';

-- Permitir conexão de qualquer host (mais seguro para desenvolvimento)
GRANT ALL PRIVILEGES ON pastelaria.* TO 'root'@'%' IDENTIFIED BY '20220015779Ma@';

-- Permitir conexão do IP específico
GRANT ALL PRIVILEGES ON pastelaria.* TO 'root'@'192.168.0.13' IDENTIFIED BY '20220015779Ma@';

-- Permitir conexão do Docker (host.docker.internal)
GRANT ALL PRIVILEGES ON pastelaria.* TO 'root'@'172.%' IDENTIFIED BY '20220015779Ma@';

-- Aplicar as mudanças
FLUSH PRIVILEGES;

-- Verificar as permissões criadas
SELECT User, Host FROM mysql.user WHERE User = 'root';
