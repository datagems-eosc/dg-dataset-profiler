import os
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from dataset_profiler.configs.config_logging import logger

security = HTTPBearer()
ENABLE_AUTH = os.environ.get("ENABLE_AUTH", "false").lower() == "true"


def validate_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> Optional[dict]:
    """
    Validate the JWT token from the Authorization header.

    Args:
        credentials: The credentials extracted from the Authorization header

    Returns:
        The decoded token payload if valid

    Raises:
        HTTPException: If the token is invalid or missing when auth is enabled
    """
    if not ENABLE_AUTH:
        return None

    try:
        token = credentials.credentials
        # We're not verifying the signature since we're only checking the client_id
        payload = jwt.decode(token, options={"verify_signature": False})

        # Check if client_id is 'airflow'
        if payload.get("client_id") != "airflow":
            logger.warning("Invalid client_id in token", client_id=payload.get("client_id"))
            raise HTTPException(
                status_code=403,
                detail="Invalid client credentials"
            )

        return payload
    except jwt.PyJWTError as e:
        logger.warning("JWT validation error", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )


def get_token_if_enabled(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Optional[dict]:
    """
    Get the token payload if auth is enabled, otherwise return None.
    This dependency can be used when auth is optional based on ENABLE_AUTH.

    Args:
        credentials: The credentials extracted from the Authorization header

    Returns:
        The decoded token payload if auth is enabled and token is valid, None otherwise
    """
    if not ENABLE_AUTH:
        return None

    return validate_token(credentials)
