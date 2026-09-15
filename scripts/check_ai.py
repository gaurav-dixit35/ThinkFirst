"""Check configuration without making a request; --live explicitly tests one synthetic hint."""
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / '.env')
from apps.api import provider, routing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=list(provider.PROVIDERS))
    parser.add_argument('--live', action='store_true', help='Send a synthetic math question to the selected provider; account usage may apply.')
    parser.add_argument('--fallback', action='store_true', help='Test the configured fallback chain with --live; may contact several providers.')
    args = parser.parse_args()
    try:
        selected = provider.configuration(args.provider)
        for name in provider.PROVIDERS:
            config = provider.configuration(name)
            print(f"{config['provider']}: {'configuration present (not verified)' if config['configured'] else 'configuration missing'} | {config['model']}")
        print(f"Selected: {selected['provider']}")
        print('Fallback: ' + (' -> '.join(routing.order(args.provider)) if routing.enabled() else 'disabled'))
        if args.live:
            if not args.fallback and not selected['configured']:
                print(f"Set {selected['key_env']} in {ROOT / '.env'} before running a live check.")
                return 2
            result = (routing.generate if args.fallback else provider.generate)(1, 'Solve 2x + 3 = 11', '', [], selected['id'])
            print(f'Live response ({result.provider}, {result.reported_model or result.model}): {result.text}')
            print('Connection and level-1 validation passed. This diagnostic is excluded from research data.')
        return 0
    except (ValueError, provider.TierViolation) as exc:
        print(str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
