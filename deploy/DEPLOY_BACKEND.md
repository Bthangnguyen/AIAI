# TripFlow Backend Deployment

This backend is a multi-container stack: Postgres/PostGIS, OSRM, CVRPTW solver,
and the FastAPI gateway. Deploy it on a VPS or container host with Docker.

## 1. Server

Recommended MVP size for about 50 users:

- 4 vCPU
- 8 GB RAM minimum, 16 GB preferred
- 40 GB SSD
- Ubuntu 22.04 or 24.04

## 2. Prepare files

```bash
git clone https://github.com/Bthangnguyen/AIAI.git
cd AIAI

cp deploy/backend.env.example .env
cp layer2_3_gateway/travel.prod.env.example layer2_3_gateway/travel.prod.env
```

Edit `.env` and `layer2_3_gateway/travel.prod.env` with real values. Do not
commit those files.

## 3. Start private backend only

This binds the gateway to `127.0.0.1:8001`, useful when Nginx/Caddy runs on the
host.

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
curl http://127.0.0.1:8001/v1/trip/health
```

For a temporary public IP test without HTTPS, set `GATEWAY_BIND=0.0.0.0` in
`.env` and open firewall port `8001`.

## 4. Start with built-in Caddy HTTPS

Point DNS for `BACKEND_DOMAIN` to the server first, then run:

```bash
docker compose -f docker-compose.prod.yml --env-file .env --profile public up -d --build
curl https://$BACKEND_DOMAIN/v1/trip/health
```

## 5. Connect Vercel frontend

Set this Vercel environment variable:

```txt
NEXT_PUBLIC_GATEWAY_URL=https://your-backend-domain
```

Then redeploy the Vercel frontend.

## 6. Useful commands

```bash
docker compose -f docker-compose.prod.yml --env-file .env ps
docker compose -f docker-compose.prod.yml --env-file .env logs -f travel-gateway
docker compose -f docker-compose.prod.yml --env-file .env logs -f cvrptw-solver
docker compose -f docker-compose.prod.yml --env-file .env restart travel-gateway
```
