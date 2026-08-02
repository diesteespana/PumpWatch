-- Runs once on first container start via docker-entrypoint-initdb.d
-- Actual schema is managed by Alembic migrations.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- for fuzzy wallet address search
