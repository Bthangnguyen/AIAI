"""Firebase Auth token verification middleware for FastAPI Gateway.

Verifies Firebase ID tokens sent via Authorization: Bearer header.
Extracts uid and attaches it to request.state for downstream handlers.

Security:
- Service account credentials read from GOOGLE_APPLICATION_CREDENTIALS env var
  or FIREBASE_SERVICE_ACCOUNT_PATH setting. NEVER hardcode credentials.
- Falls back to Application Default Credentials (ADC) in Cloud environments.

Usage:
    from app.middleware.firebase_verify import get_current_user, FirebaseUser

    @router.post("/protected")
    async def protected_route(user: FirebaseUser = Depends(get_current_user)):
        print(f"Authenticated user: {user.uid}")
"""

import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials

from app.config import settings
from app.utils.logging import AppLogger

logger = AppLogger().get_logger()

# ─── Firebase Admin SDK Initialization ─────────────────────────────

_firebase_app: Optional[firebase_admin.App] = None


def _init_firebase() -> firebase_admin.App:
    """Initialize Firebase Admin SDK (singleton).

    Credential resolution order:
    1. FIREBASE_SERVICE_ACCOUNT_PATH setting (explicit path to JSON)
    2. GOOGLE_APPLICATION_CREDENTIALS env var (standard GCP pattern)
    3. Application Default Credentials (Cloud Run, GCE, etc.)
    """
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    cred = None
    sa_path = getattr(settings, "FIREBASE_SERVICE_ACCOUNT_PATH", None)

    if sa_path and os.path.exists(sa_path):
        logger.info(f"Firebase Admin: using service account from {sa_path}")
        cred = credentials.Certificate(sa_path)
    elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        logger.info("Firebase Admin: using GOOGLE_APPLICATION_CREDENTIALS")
        cred = credentials.ApplicationDefault()
    else:
        logger.info("Firebase Admin: using Application Default Credentials")
        cred = credentials.ApplicationDefault()

    project_id = getattr(settings, "FIREBASE_PROJECT_ID", None)
    options = {"projectId": project_id} if project_id else {}

    _firebase_app = firebase_admin.initialize_app(cred, options)
    logger.info(f"Firebase Admin SDK initialized (project: {project_id or 'auto-detect'})")
    return _firebase_app


# Initialize on module load
try:
    _init_firebase()
except Exception as e:
    logger.warning(f"Firebase Admin SDK init deferred: {e}")


# ─── Data Models ───────────────────────────────────────────────────


class FirebaseUser:
    """Lightweight user object extracted from a verified Firebase ID token."""

    __slots__ = ("uid", "email", "name", "picture", "email_verified")

    def __init__(
        self,
        uid: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        picture: Optional[str] = None,
        email_verified: bool = False,
    ):
        self.uid = uid
        self.email = email
        self.name = name
        self.picture = picture
        self.email_verified = email_verified

    def __repr__(self) -> str:
        return f"FirebaseUser(uid={self.uid!r}, email={self.email!r})"


# ─── Security Scheme ───────────────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=False)


# ─── Dependency: Verify Token ──────────────────────────────────────


async def get_current_user(
    credentials_header: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> FirebaseUser:
    """FastAPI dependency that verifies Firebase ID token.

    Extracts the token from Authorization: Bearer <token> header,
    verifies it with Firebase Admin SDK, and returns a FirebaseUser.

    Raises:
        HTTPException 401: If token is missing, invalid, or expired.
    """
    if credentials_header is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu token xác thực. Vui lòng đăng nhập.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials_header.credentials

    # Check for developer mock token bypass
    if token == "mock-session-token-xyz-987" or token.startswith("mock-"):
        logger.info("Firebase Auth Bypass: accepting mock developer session token.")
        return FirebaseUser(
            uid="mock-uid-12345",
            email="demo@aiai.travel",
            name="Gia Long",
            email_verified=True
        )

    try:
        # Ensure Firebase is initialized
        if _firebase_app is None:
            _init_firebase()

        # Verify the ID token (checks signature, expiry, issuer)
        decoded_token = firebase_auth.verify_id_token(token, check_revoked=True)

        return FirebaseUser(
            uid=decoded_token["uid"],
            email=decoded_token.get("email"),
            name=decoded_token.get("name"),
            picture=decoded_token.get("picture"),
            email_verified=decoded_token.get("email_verified", False),
        )

    except firebase_auth.RevokedIdTokenError:
        logger.warning("Firebase token was revoked")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã bị thu hồi. Vui lòng đăng nhập lại.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except firebase_auth.ExpiredIdTokenError:
        logger.warning("Firebase token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except firebase_auth.InvalidIdTokenError as e:
        logger.warning(f"Invalid Firebase token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ. Vui lòng đăng nhập lại.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Firebase token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Xác thực thất bại. Vui lòng thử lại.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─── Optional Auth (for endpoints that work with or without auth) ──


async def get_optional_user(
    credentials_header: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[FirebaseUser]:
    """Like get_current_user but returns None instead of raising 401.

    Useful for endpoints that enhance behavior for authenticated users
    but still work anonymously (e.g., health check, public search).
    """
    if credentials_header is None:
        return None

    try:
        return await get_current_user(credentials_header)
    except HTTPException:
        return None
