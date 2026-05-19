-- Redefinir senha do admin: admin@pastelaria.com
-- Senha em texto: 20220015 (hash bcrypt)
USE pastelaria;

UPDATE usuarios
SET senha = '$2b$12$ptc8WyZCZGqzIhudge2MI.9sPH2GXEZjgVvQhLzyYb6GVuYqeJoSu'
WHERE email = 'admin@pastelaria.com';

-- Se o usuário não existir, descomente e execute:
-- INSERT INTO usuarios (nome, email, senha, is_admin, created_at)
-- VALUES (
--   'Administrador',
--   'admin@pastelaria.com',
--   '$2b$12$ptc8WyZCZGqzIhudge2MI.9sPH2GXEZjgVvQhLzyYb6GVuYqeJoSu',
--   1,
--   NOW()
-- );

SELECT id, nome, email, is_admin FROM usuarios WHERE email = 'admin@pastelaria.com';
