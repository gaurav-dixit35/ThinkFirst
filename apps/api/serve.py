"""Container entrypoint supporting Railway's assigned PORT."""
import os
import uvicorn


def port():
    try:
        value = int(os.getenv('PORT', '8000'))
    except ValueError:
        raise ValueError('PORT must be an integer between 1 and 65535.') from None
    if not 1 <= value <= 65535:
        raise ValueError('PORT must be between 1 and 65535.')
    return value


if __name__ == '__main__':
    uvicorn.run('apps.api.main:app', host='0.0.0.0', port=port(), access_log=False,
                proxy_headers=True, forwarded_allow_ips=os.getenv('FORWARDED_ALLOW_IPS', '127.0.0.1'))
