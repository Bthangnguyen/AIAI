\connect travel;

-- Create schema
CREATE SCHEMA IF NOT EXISTS travel;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
-- Note: pg_cron must be created after the main server starts because it requires shared_preload_libraries
-- But since we injected shared_preload_libraries=pg_cron via docker-compose, we can create it here:
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Weather penalty updater (every 5 minutes)
SELECT cron.schedule(
    'weather-penalty-reset',
    '*/5 * * * *',
    $$UPDATE travel.poi SET weather_penalty = 0 WHERE is_outdoor = true AND weather_penalty != 0$$
);
