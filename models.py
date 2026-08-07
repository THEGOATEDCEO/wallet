from datetime import datetime

from flask_login import LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from argon2 import PasswordHasher, exceptions as argon2_exceptions


db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    balance = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)

    def set_password(self, password: str) -> None:
        # Hash new passwords with Argon2
        ph = PasswordHasher()
        self.password_hash = ph.hash(password)

    def verify_password(self, password: str) -> bool:
        """
        Verify password against the stored hash. Supports existing Werkzeug hashes
        and upgrades them to Argon2 on successful verification.
        """
        ph = PasswordHasher()
        # Try Argon2 verification first
        try:
            return ph.verify(self.password_hash, password)
        except argon2_exceptions.VerifyMismatchError:
            # Not matched under Argon2 — try legacy Werkzeug hash
            try:
                if check_password_hash(self.password_hash, password):
                    # Re-hash with Argon2 for better security
                    self.set_password(password)
                    db.session.commit()
                    return True
            except Exception:
                pass
            return False
        except argon2_exceptions.InvalidHash:
            # Hash is not Argon2 formatted; try legacy check
            try:
                if check_password_hash(self.password_hash, password):
                    self.set_password(password)
                    db.session.commit()
                    return True
            except Exception:
                pass
            return False

    def __repr__(self) -> str:
        return f'<User {self.username}>'


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_transactions')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_transactions')

    def __repr__(self) -> str:
        return f'<Transaction {self.id}>'


class WalletSettings(db.Model):
    __tablename__ = 'wallet_settings'

    id = db.Column(db.Integer, primary_key=True)
    perk_price = db.Column(db.Float, nullable=False, default=1.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class PurchaseRequest(db.Model):
    __tablename__ = 'purchase_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    requested_perks = db.Column(db.Integer, nullable=False)
    price_per_perk = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref='purchase_requests')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_requests')


class SellOrder(db.Model):
    __tablename__ = 'sell_orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    price_per_perk = db.Column(db.Float, nullable=False)
    total_value = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Recorded')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', foreign_keys=[user_id], backref='sell_orders')


class Treasury(db.Model):
    __tablename__ = 'treasury'

    id = db.Column(db.Integer, primary_key=True)
    available_perks = db.Column(db.Integer, nullable=False, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class MiningSubmission(db.Model):
    __tablename__ = 'mining_submissions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nonce = db.Column(db.String(20), nullable=False)
    hash = db.Column(db.String(255), nullable=False)
    reward = db.Column(db.Integer, nullable=False, default=20)
    status = db.Column(db.String(20), nullable=False, default='Pending')
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref='mining_submissions')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='reviewed_mining_submissions')


login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))
