from flask import Flask

from config import Config
from models import User, WalletSettings, db, login_manager
from mining import get_treasury
import os
from routes import register_routes


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    register_routes(app)

    with app.app_context():
        db.create_all()
        if not WalletSettings.query.first():
            db.session.add(WalletSettings(perk_price=1))

        # Ensure treasury row exists
        get_treasury()

        # Admin user setup. Use environment vars to set secure admin credentials
        admin_username = os.environ.get('ADMIN_USERNAME', 'natoshi sakamoto')
        admin_password = os.environ.get('ADMIN_PASSWORD')

        admin = User.query.filter_by(username=admin_username).first()
        if not admin:
            admin = User(username=admin_username, email='admin@perkmint.com', is_admin=True)
            if admin_password:
                admin.set_password(admin_password)
            else:
                # fallback to a default admin password when none provided (development only)
                admin.set_password('admin12345')
            db.session.add(admin)
        else:
            admin.is_admin = True
            if admin_password:
                admin.set_password(admin_password)

        for user in User.query.all():
            if user.balance is None:
                user.balance = 0

        db.session.commit()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
