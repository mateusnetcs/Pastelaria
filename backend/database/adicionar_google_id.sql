-- Login com Google: identificador único da conta Google
USE pastelaria;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS google_id VARCHAR(255) NULL UNIQUE AFTER email;
