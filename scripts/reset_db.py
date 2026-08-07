"""Reset the application's database schema (drop all tables, then create all).

Usage:
    python scripts/reset_db.py

Warning: This will delete all data in the local database file defined in `config.py`.
"""

import os
import sys

# Ensure project root is on sys.path so imports work when invoked as a script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from config import Config
from models import db


def main():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        print('Dropping all tables...')
        db.drop_all()
        print('Creating all tables...')
        db.create_all()
        print('Done.')


if __name__ == '__main__':
    main()
