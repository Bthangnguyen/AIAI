FROM postgis/postgis:16-3.4 AS base

# Install extensions via apt-get (pgvector and pg_cron are in pgdg repo)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-16-pgvector postgresql-16-cron && \
    rm -rf /var/lib/apt/lists/*

# Copy init scripts
ADD create.sql /docker-entrypoint-initdb.d/
COPY postgresql.conf /etc/postgresql/conf.d/