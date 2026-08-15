-- TeluAI v20 role-based administration
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(30) NOT NULL DEFAULT 'user';
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);
CREATE INDEX IF NOT EXISTS ix_users_is_active ON users (is_active);
UPDATE users SET role = 'user' WHERE role IS NULL OR role = '';
UPDATE users SET is_active = TRUE WHERE is_active IS NULL;
