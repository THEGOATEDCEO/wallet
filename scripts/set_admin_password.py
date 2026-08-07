"""CLI helper to set or update the admin username and password.

Usage:
    python scripts/set_admin_password.py --username "natoshi sakamoto" --password "<secret>"

This script updates or creates the admin user using the application's models and hashes the password via `User.set_password()`.
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from models import db, User


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', required=True)
    parser.add_argument('--password', required=True)
    parser.add_argument('--email', default='admin@perkmint.com')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=args.username).first()
        if not user:
            user = User(username=args.username, email=args.email, is_admin=True)
            user.set_password(args.password)
            db.session.add(user)
            db.session.commit()
            print(f'Created admin user: {args.username}')
            return 0

        user.is_admin = True
        user.set_password(args.password)
        db.session.commit()
        print(f'Updated admin user: {args.username}')
        return 0


if __name__ == '__main__':
    sys.exit(main())
