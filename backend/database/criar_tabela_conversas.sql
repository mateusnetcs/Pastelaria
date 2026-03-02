USE pastelaria;

CREATE TABLE IF NOT EXISTS conversas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chat_id VARCHAR(100) NOT NULL,
    role ENUM('system', 'user', 'assistant', 'tool') NOT NULL,
    content TEXT NOT NULL,
    tool_call_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_chat_id (chat_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
