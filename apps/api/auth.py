import os
from functools import lru_cache
import jwt
from urllib.parse import urlsplit
from fastapi import Header, HTTPException


def mode():
    value = os.getenv('AUTH_MODE', 'clerk')
    if value not in ('clerk', 'development'):
        raise RuntimeError('AUTH_MODE must be clerk or development.')
    if value == 'development' and os.getenv('ENVIRONMENT', 'production') != 'development':
        raise RuntimeError('Development identity is forbidden outside development.')
    return value


def origins():
    return [s.strip().rstrip('/') for s in os.getenv('WEB_ORIGINS', 'http://localhost:3000').split(',') if s.strip()]


def validate_configuration():
    selected = mode()
    if selected == 'clerk':
        issuer = urlsplit(os.getenv('CLERK_ISSUER', ''))
        if issuer.scheme != 'https' or not issuer.hostname or issuer.query or issuer.fragment or issuer.username:
            raise RuntimeError('CLERK_ISSUER must be an HTTPS issuer URL.')
    for origin in origins():
        parsed = urlsplit(origin)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or '*' in origin:
            raise RuntimeError('WEB_ORIGINS must contain exact origins, without paths or wildcards.')
        if os.getenv('ENVIRONMENT', 'production') != 'development' and parsed.scheme != 'https':
            raise RuntimeError('Hosted WEB_ORIGINS must use HTTPS.')
    if not origins():
        raise RuntimeError('At least one WEB_ORIGINS entry is required.')


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
        audience = os.getenv('CLERK_AUDIENCE') or None
        claims = jwt.decode(token, jwks(issuer).get_signing_key_from_jwt(token).key,
                            algorithms=['RS256'], issuer=issuer,
                            audience=audience,
                            options={'verify_aud': bool(audience), 'require': ['exp', 'iat', 'nbf', 'sub', 'sid']})
        if claims.get('azp') not in origins() or not claims['sub'] or not claims['sid']:
            raise ValueError('Unexpected authorized party')
        return claims['sub']
    except Exception as exc:
        raise HTTPException(401, 'Your sign-in could not be verified. Please sign in again.') from exc


def is_admin(subject):
    return subject in [s.strip() for s in os.getenv('ADMIN_SUBJECTS', '').split(',') if s.strip()]
