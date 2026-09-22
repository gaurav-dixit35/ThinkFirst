import time
from types import SimpleNamespace
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from apps.api import auth


@pytest.fixture
def signed(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    wrong = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setenv('AUTH_MODE', 'clerk')
    monkeypatch.setenv('CLERK_ISSUER', 'https://issuer.example.test')
    monkeypatch.setenv('WEB_ORIGINS', ' https://thinkfirst.example.test ')
    monkeypatch.delenv('CLERK_AUDIENCE', raising=False)
    monkeypatch.setattr(auth, 'jwks', lambda issuer: SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(key=key.public_key())))
    def token(changes=None, remove=None, wrong_key=False):
        current = int(time.time())
        claims = dict(iss='https://issuer.example.test', sub='user_123', sid='session_123', azp='https://thinkfirst.example.test', iat=current, nbf=current-1, exp=current+60)
        claims.update(changes or {})
        if remove: claims.pop(remove)
        return 'Bearer ' + jwt.encode(claims, wrong if wrong_key else key, algorithm='RS256')
    return token


def test_signed_session_and_optional_audience(signed, monkeypatch):
    assert auth.identity(signed()) == 'user_123'
    monkeypatch.setenv('CLERK_AUDIENCE', 'thinkfirst-api')
    with pytest.raises(HTTPException): auth.identity(signed())
    assert auth.identity(signed({'aud': 'thinkfirst-api'})) == 'user_123'


@pytest.mark.parametrize('changes,remove,wrong', [({'exp': 1},None,False), ({'nbf': 9999999999},None,False), ({'azp': 'https://evil.test'},None,False), ({'iss': 'https://evil.test'},None,False), ({'sub':''},None,False), ({},'sid',False), ({},None,True)])
def test_invalid_signed_sessions_rejected(signed, changes, remove, wrong):
    with pytest.raises(HTTPException) as error:
        auth.identity(signed(changes, remove, wrong))
    assert error.value.status_code == 401


def test_configuration_fails_closed(monkeypatch):
    monkeypatch.setenv('AUTH_MODE', 'unknown')
    with pytest.raises(RuntimeError): auth.validate_configuration()
    monkeypatch.setenv('AUTH_MODE', 'development')
    monkeypatch.setenv('ENVIRONMENT', 'production')
    with pytest.raises(RuntimeError): auth.validate_configuration()
    monkeypatch.setenv('AUTH_MODE', 'clerk')
    monkeypatch.setenv('CLERK_ISSUER', 'https://issuer.example.test')
    for origin in ('*', 'http://localhost:3000', 'https://example.test/path', ''):
        monkeypatch.setenv('WEB_ORIGINS', origin)
        with pytest.raises(RuntimeError): auth.validate_configuration()
    monkeypatch.setenv('WEB_ORIGINS', 'https://example.test')
    auth.validate_configuration()
