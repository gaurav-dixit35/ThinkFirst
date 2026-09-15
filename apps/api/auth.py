import os
from functools import lru_cache
import jwt
from fastapi import Header, HTTPException


def mode():
    value = os.getenv('AUTH_MODE', 'clerk')
    if value == 'development' and os.getenv('ENVIRONMENT', 'production') != 'development':
        raise RuntimeError('Development identity is forbidden outside development.')
    return value


@lru_cache
def jwks(issuer):
    return jwt.PyJWKClient(issuer.rstrip('/') + '/.well-known/jwks.json')


def identity(authorization: str | None = Header(default=None)):
    if mode() == 'development':
        return 'local-development-participant'
    issuer = os.getenv('CLERK_ISSUER', '')
    if not issuer.startswith('https://'):
        raise HTTPException(503, 'Authentication is not configured.')
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Please sign in to continue.')
    token = authorization[7:]
    try:
        claims = jwt.decode(token, jwks(issuer).get_signing_key_from_jwt(token).key,
                            algorithms=['RS256'], issuer=issuer,
                            options={'verify_aud': False, 'require': ['exp', 'iat', 'sub']})
        origins = os.getenv('WEB_ORIGINS', 'http://localhost:3000').split(',')
        if claims.get('azp') not in origins:
            raise ValueError('Unexpected authorized party')
        return claims['sub']
    except Exception as exc:
        raise HTTPException(401, 'Your sign-in could not be verified. Please sign in again.') from exc


def is_admin(subject):
    return subject in [s.strip() for s in os.getenv('ADMIN_SUBJECTS', '').split(',') if s.strip()]
