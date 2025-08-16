-- Fix alembic_version table column size
ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64);
