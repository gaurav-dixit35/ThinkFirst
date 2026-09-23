"""Apply local Clerk configuration without printing credentials or making requests."""
import argparse
import base64
import os
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def updated_text(path, changes):
    lines = path.read_text(encoding='utf-8-sig').splitlines() if path.exists() else []
    remaining = dict(changes)
    result = []
    for line in lines:
        key = line.partition('=')[0].strip()
        if key in changes:
            if key in remaining:
                result.append(key + '=' + remaining.pop(key))
        else:
            result.append(line)
    result.extend(key + '=' + value for key, value in remaining.items())
    return '\n'.join(result) + '\n'


def replace_file(path, content):
    temporary = path.with_name(path.name + '.auth-tmp')
    try:
        temporary.write_text(content, encoding='utf-8')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Write validated local configuration.')
    args = parser.parse_args()
    root_env = ROOT / '.env'
    web_env = ROOT / 'apps/web/.env.local'
    root = dotenv_values(root_env, interpolate=False)
    web = dotenv_values(web_env, interpolate=False)
    if root.get('ENVIRONMENT') != 'development':
        raise SystemExit('This helper is for ENVIRONMENT=development only. Use hosting secret stores for production.')
    public = root.get('NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY') or web.get('NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY') or ''
    secret = root.get('CLERK_SECRET_KEY') or web.get('CLERK_SECRET_KEY') or ''
    issuer = (root.get('CLERK_ISSUER') or '').rstrip('/')
    if not public.startswith(('pk_test_', 'pk_live_')) or not secret.startswith(('sk_test_', 'sk_live_')) or not issuer:
        raise SystemExit('Add NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY, CLERK_SECRET_KEY and CLERK_ISSUER to the root .env. No files changed.')
    if public.split('_')[1] != secret.split('_')[1]:
        raise SystemExit('Publishable and secret keys must use the same Clerk environment. No files changed.')
    try:
        encoded = public.split('_', 2)[2]
        domain = base64.b64decode(encoded + '=' * (-len(encoded) % 4), validate=True).decode('ascii').removesuffix('$')
        parsed = urlsplit(issuer)
        if parsed.scheme != 'https' or parsed.netloc != domain or parsed.path or parsed.query or parsed.fragment or parsed.username:
            raise ValueError()
    except (ValueError, UnicodeError):
        raise SystemExit('CLERK_ISSUER must match the HTTPS frontend API domain in the publishable key. No files changed.') from None
    api_url = root.get('NEXT_PUBLIC_API_URL') or web.get('NEXT_PUBLIC_API_URL') or 'http://localhost:8000'
    origin = urlsplit(api_url)
    if origin.scheme not in ('http','https') or origin.hostname not in ('localhost','127.0.0.1') or origin.username or origin.query or origin.fragment or origin.path not in ('','/'):
        raise SystemExit('This local helper requires a localhost NEXT_PUBLIC_API_URL. No files changed.')
    for value in (public, secret, issuer, api_url):
        if any(character.isspace() for character in value) or any(character in value for character in ('"', "'", '#', '$')):
            raise SystemExit('Configuration contains unexpected characters. No files changed.')
    origins = [value.strip().rstrip('/') for value in (root.get('WEB_ORIGINS') or '').split(',') if value.strip()]
    if 'http://localhost:3000' not in origins:
        origins.append('http://localhost:3000')
    web_values = {'NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY':public, 'CLERK_SECRET_KEY':secret, 'NEXT_PUBLIC_API_URL':api_url,
                  'NEXT_PUBLIC_CLERK_SIGN_IN_URL':'/login', 'NEXT_PUBLIC_CLERK_SIGN_UP_URL':'/signup',
                  'NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL':'/', 'NEXT_PUBLIC_CLERK_SIGN_UP_FALLBACK_REDIRECT_URL':'/'}
    root_text = updated_text(root_env, {'AUTH_MODE':'clerk', 'CLERK_ISSUER':issuer, 'WEB_ORIGINS':','.join(origins)})
    web_text = updated_text(web_env, web_values)
    if not args.apply:
        print('Local configuration is complete. Run again with --apply to enable Clerk. Credentials were not sent or validated with Clerk.')
        return
    replace_file(web_env, web_text)
    replace_file(root_env, root_text)
    print('Local Clerk configuration written. Restart the API and rebuild/restart the website. Existing shared-workspace conversations remain separate. No network requests were made.')


if __name__ == '__main__':
    main()
