"""FastAPI entry point — Single pool, rate limiter, proxy headers.

ARCHITECTURE:
- ONE connection pool (SQLAlchemy AsyncSessionFactory in database.py)
- NO psycopg AsyncConnectionPool (ghost pool eliminated)
- ProxyHeadersMiddleware for real client IP behind Docker NAT
- slowapi rate limiter to prevent DDoS on LLM/L4 endpoints
"""

import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.trip_planner import router as trip_router, limiter
from app.api.admin_pois import router as admin_router
from app.config import settings

app = FastAPI(
    title="AI Travel Gateway — Layer 2 & 3",
    version="1.0.0",
    description="LLM Intent Extraction + Spatial POI Filter + OR-Tools Integration",
)

# CORS — allow mobile app + dev origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Decode real client IP from X-Forwarded-For (Docker NAT sends 172.x.x.x)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

# Wire rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(trip_router)
app.include_router(admin_router)
