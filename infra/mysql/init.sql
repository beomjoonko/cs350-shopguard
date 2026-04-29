-- ShopGuard initial DB setup.
-- Schema is created/migrated by Alembic; this only sets character set
-- and the dedicated app user.

ALTER DATABASE shopguard CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'shopguard'@'%' IDENTIFIED BY 'changeme';
GRANT ALL PRIVILEGES ON shopguard.* TO 'shopguard'@'%';
FLUSH PRIVILEGES;
