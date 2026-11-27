"""Authentication of the MathE document endpoints.

Only the DataGEMS Gateway calls these endpoints, on behalf of the MathE
backend. As for the other DataGEMS services behind the Gateway (dataset-recsys,
in-dataset-discovery), the Gateway exchanges the caller's token for one
addressed to this service, and this module:

* verifies the token's RS256 signature against the Keycloak realm's keys
  (found through the realm's OpenID configuration),
* requires the configured issuer and audience and an unexpired token,
* requires one of the allowed realm roles, or a privileged one.

This is separate from ``auth.py`` (Airflow's calls to /profiler), which is left
as it is. It has its own switch, DOCUMENTS_AUTH_ENABLED, on by default, so that
turning ENABLE_AUTH off for the profiler never opens these endpoints.
"""

import os
import ssl
from functools import lru_cache
from typing import Optional

import jwt
import requests
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from dataset_profiler.configs.config_logging import logger

DEFAULT_ISSUER = "https://datagems-dev.scayle.es/oauth/realms/dev"
DEFAULT_AUDIENCE = "dataset-profiler-api"
DEFAULT_ALLOWED_ROLES = "user,dg_user,dg_system"
# Realm roles that pass any role check, as in the other DataGEMS services.
PRIVILEGED_ROLES = {"dg_admin", "dg_system", "dg_dataset-curator"}

_bearer = HTTPBearer(auto_error=False)


def _env_flag(name: str, default: str) -> bool:
    return os.environ.get(name, default).lower() in ["1", "true", "yes", "on"]


def is_documents_auth_enabled() -> bool:
    return _env_flag("DOCUMENTS_AUTH_ENABLED", "true")


def oidc_issuer() -> str:
    return (os.environ.get("OIDC_ISSUER_URL") or DEFAULT_ISSUER).rstrip("/")


def oidc_audience() -> str:
    return os.environ.get("OIDC_AUDIENCE") or DEFAULT_AUDIENCE


def allowed_roles() -> set[str]:
    raw = os.environ.get("DOCUMENTS_ALLOWED_ROLES") or DEFAULT_ALLOWED_ROLES
    return {role.strip() for role in raw.split(",") if role.strip()}


@lru_cache(maxsize=4)
def _jwks_client(issuer: str, verify_ssl: bool) -> jwt.PyJWKClient:
    """Signing keys of the realm. Not cached when discovery fails, so it is retried."""
    response = requests.get(f"{issuer}/.well-known/openid-configuration",
                            timeout=10, verify=verify_ssl)
    response.raise_for_status()
    ssl_context = None if verify_ssl else ssl._create_unverified_context()  # noqa: S323
    # cache_keys: one key fetch serves every request until a new kid shows up.
    return jwt.PyJWKClient(response.json()["jwks_uri"], cache_keys=True, lifespan=3600,
                           timeout=10, ssl_context=ssl_context)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})


def verify_token(token: str) -> dict:
    """The token's claims, or an HTTPException (401, 403 or 503)."""
    issuer = oidc_issuer()
    try:
        signing_key = _jwks_client(issuer, _env_flag("OIDC_VERIFY_SSL", "true")) \
            .get_signing_key_from_jwt(token)
    except (requests.RequestException, KeyError, ValueError, jwt.PyJWKClientConnectionError) as e:
        logger.error("Cannot fetch the identity provider's signing keys", issuer=issuer, error=str(e))
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Authentication service is unavailable")
    except jwt.PyJWTError as e:
        logger.warning("Token rejected before signature check", error=str(e))
        raise _unauthorized("Invalid authentication token")

    try:
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=oidc_audience(),
            issuer=issuer,
            options={"require": ["exp", "iss", "aud"]},
        )
    except jwt.PyJWTError as e:
        logger.warning("Token rejected", error=str(e))
        raise _unauthorized("Invalid authentication token")

    roles = set((claims.get("realm_access") or {}).get("roles") or [])
    accepted = allowed_roles() | PRIVILEGED_ROLES
    if not roles & accepted:
        logger.warning("Caller lacks the required role", user_id=claims.get("sub"),
                       client_id=claims.get("azp"), roles=sorted(roles))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"One of these roles is required: {', '.join(sorted(accepted))}")
    return claims


def bearer_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
) -> Optional[str]:
    """The caller's raw token, forwarded to MoMa so that MoMa checks the caller's grants."""
    return credentials.credentials if credentials is not None and credentials.credentials else None


def require_document_access(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
) -> Optional[dict]:
    """FastAPI dependency: the caller's claims, or None when DOCUMENTS_AUTH_ENABLED is off."""
    if not is_documents_auth_enabled():
        return None
    if credentials is None or not credentials.credentials:
        raise _unauthorized("Missing bearer token")
    return verify_token(credentials.credentials)
