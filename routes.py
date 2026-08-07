from datetime import datetime, timedelta

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from forms import AdminForm, BuyPerksForm, LoginForm, MiningForm, PurchaseRequestActionForm, RegistrationForm, SearchUsersForm, SellPerksForm, SendForm, WalletSettingsForm
from models import PurchaseRequest, SellOrder, Transaction, User, WalletSettings, MiningSubmission, Treasury, db
from mining import validate_nonce, create_mining_submission, get_treasury, award_mining_submission, reject_mining_submission, REWARD_AMOUNT, MINING_PREFIX


def get_wallet_settings():
    settings = WalletSettings.query.first()
    if settings is None:
        settings = WalletSettings(perk_price=1)
        db.session.add(settings)
        db.session.commit()
    return settings


def register_routes(app):
    @app.context_processor
    def inject_wallet_settings():
        return {'wallet_settings': get_wallet_settings()}
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        form = RegistrationForm()
        if form.validate_on_submit():
            if form.password.data != form.confirm_password.data:
                flash('Passwords do not match.', 'danger')
                return redirect(url_for('register'))

            if User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first():
                flash('Username or email already exists.', 'danger')
                return redirect(url_for('register'))

            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))

        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            now = datetime.utcnow()
            if user and user.locked_until and user.locked_until > now:
                flash(f'Account locked until {user.locked_until.strftime("%Y-%m-%d %H:%M:%S UTC")}. Try later.', 'danger')
                return redirect(url_for('login'))

            if user and user.verify_password(form.password.data):
                # honor the "remember me" checkbox
                remember = bool(getattr(form, 'remember_me', None) and form.remember_me.data)
                login_user(user, remember=remember)
                # reset failed login counters on success
                user.failed_login_attempts = 0
                user.locked_until = None
                db.session.commit()
                flash('Welcome back!', 'success')
                return redirect(url_for('dashboard'))
            # invalid credentials
            if user:
                user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=15)
                    flash('Too many failed login attempts. Account locked for 15 minutes.', 'danger')
                else:
                    flash('Invalid username or password.', 'danger')
                db.session.commit()
            else:
                flash('Invalid username or password.', 'danger')

        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))

    @app.route('/api/wallet-settings')
    def wallet_settings_api():
        settings = get_wallet_settings()
        return {'perk_price': settings.perk_price}, 200

    @app.route('/dashboard')
    @login_required
    def dashboard():
        transactions = Transaction.query.filter((Transaction.sender_id == current_user.id) | (Transaction.receiver_id == current_user.id)).order_by(Transaction.timestamp.desc()).limit(5).all()
        purchase_requests = PurchaseRequest.query.filter_by(user_id=current_user.id).order_by(PurchaseRequest.created_at.desc()).all()
        sell_orders = SellOrder.query.filter_by(user_id=current_user.id).order_by(SellOrder.created_at.desc()).all()
        treasury = get_treasury()
        mining_submissions = MiningSubmission.query.filter_by(user_id=current_user.id).order_by(MiningSubmission.submitted_at.desc()).all()
        return render_template('dashboard.html', user=current_user, transactions=transactions, purchase_requests=purchase_requests, sell_orders=sell_orders, treasury=treasury, mining_submissions=mining_submissions)

    @app.route('/profile')
    @login_required
    def profile():
        from forms import TerminateForm
        terminate_form = TerminateForm()
        return render_template('profile.html', user=current_user, terminate_form=terminate_form)

    @app.route('/buy-perks', methods=['GET', 'POST'])
    @login_required
    def buy_perks():
        settings = get_wallet_settings()
        form = BuyPerksForm()
        if form.validate_on_submit():
            requested_perks = form.requested_perks.data
            total_price = requested_perks * settings.perk_price
            purchase_request = PurchaseRequest(
                user_id=current_user.id,
                requested_perks=requested_perks,
                price_per_perk=settings.perk_price,
                total_price=total_price,
                status='Pending',
            )
            db.session.add(purchase_request)
            db.session.commit()
            flash('Purchase request submitted. Your PERKS will be added after an administrator confirms your payment.', 'success')
            return redirect(url_for('dashboard'))
        return render_template('buy_perks.html', form=form, settings=settings)

    @app.route('/sell-perks', methods=['GET', 'POST'])
    @login_required
    def sell_perks():
        form = SellPerksForm()
        settings = get_wallet_settings()
        if form.validate_on_submit():
            amount = form.amount.data
            if amount > current_user.balance:
                flash('You cannot sell more PERKS than you currently hold.', 'danger')
                return redirect(url_for('sell_perks'))

            current_user.balance -= amount
            sale = SellOrder(
                user_id=current_user.id,
                amount=amount,
                price_per_perk=settings.perk_price,
                total_value=amount * settings.perk_price,
                status='Recorded',
            )
            db.session.add(sale)
            db.session.commit()
            flash('Sell order recorded. The admin can see it and review it.', 'success')
            return redirect(url_for('dashboard'))
        return render_template('sell_perks.html', form=form, settings=settings)

    @app.route('/send', methods=['GET', 'POST'])
    @login_required
    def send_perks():
        form = SendForm()
        if form.validate_on_submit():
            recipient = User.query.filter_by(username=form.recipient.data).first()
            if not recipient:
                flash('Unknown recipient.', 'danger')
                return redirect(url_for('send_perks'))

            if recipient.id == current_user.id:
                flash('You cannot send to yourself.', 'danger')
                return redirect(url_for('send_perks'))

            amount = form.amount.data
            if amount <= 0:
                flash('Amount must be greater than zero.', 'danger')
                return redirect(url_for('send_perks'))

            if current_user.balance < amount:
                flash('Insufficient balance.', 'danger')
                return redirect(url_for('send_perks'))

            current_user.balance -= amount
            recipient.balance += amount
            tx = Transaction(sender_id=current_user.id, receiver_id=recipient.id, amount=amount)
            db.session.add(tx)
            db.session.commit()
            flash('Transfer completed successfully.', 'success')
            return redirect(url_for('dashboard'))

        return render_template('send.html', form=form)

    @app.route('/history')
    @login_required
    def history():
        transactions = Transaction.query.filter((Transaction.sender_id == current_user.id) | (Transaction.receiver_id == current_user.id)).order_by(Transaction.timestamp.desc()).all()
        return render_template('history.html', transactions=transactions)

    @app.route('/admin', methods=['GET', 'POST'])
    @login_required
    def admin():
        if not current_user.is_admin:
            abort(403)

        settings = get_wallet_settings()
        form = WalletSettingsForm()
        if form.validate_on_submit():
            try:
                price_value = float(form.perk_price.data)
            except ValueError:
                flash('Please enter a valid decimal price.', 'danger')
                return redirect(url_for('admin'))

            if price_value <= 0:
                flash('Price must be greater than zero.', 'danger')
                return redirect(url_for('admin'))

            settings.perk_price = price_value
            settings.updated_at = datetime.utcnow()
            db.session.commit()
            flash('PERK price updated successfully.', 'success')
            return redirect(url_for('admin'))

        pending_requests = PurchaseRequest.query.filter_by(status='Pending').order_by(PurchaseRequest.created_at.asc()).all()
        all_requests = PurchaseRequest.query.order_by(PurchaseRequest.status != 'Pending', PurchaseRequest.created_at.desc()).all()
        pending_mining = MiningSubmission.query.filter_by(status='Pending').order_by(MiningSubmission.submitted_at.asc()).all()
        recent_sales = SellOrder.query.order_by(SellOrder.created_at.desc()).all()
        treasury = get_treasury()
        return render_template('admin_dashboard.html', settings=settings, form=form, pending_requests=pending_requests, purchase_requests=all_requests, pending_mining=pending_mining, recent_sales=recent_sales, treasury=treasury)

    @app.route('/admin/purchase-requests')
    @login_required
    def admin_purchase_requests():
        if not current_user.is_admin:
            abort(403)

        settings = get_wallet_settings()
        purchase_requests = PurchaseRequest.query.order_by(PurchaseRequest.status != 'Pending', PurchaseRequest.created_at.desc()).all()
        return render_template('purchase_requests.html', settings=settings, purchase_requests=purchase_requests)

    @app.route('/mine', methods=['GET', 'POST'])
    @login_required
    def mine():
        form = MiningForm()
        treasury = get_treasury()
        if form.validate_on_submit():
            nonce = form.nonce.data
            valid, digest = validate_nonce(nonce, current_user.username, current_user.balance)
            if not valid:
                flash('Invalid solution. Hash does not meet difficulty.', 'danger')
                return redirect(url_for('mine'))

            # Prevent duplicate nonces or hashes
            if MiningSubmission.query.filter((MiningSubmission.nonce == nonce) | (MiningSubmission.hash == digest)).first():
                flash('This nonce or hash has already been submitted.', 'danger')
                return redirect(url_for('mine'))

            create_mining_submission(current_user, nonce, digest)
            flash('Mining submission received and is pending review by an administrator.', 'success')
            return redirect(url_for('dashboard'))

        return render_template('mine_perks.html', form=form, treasury=treasury)

    @app.route('/admin/mining')
    @login_required
    def admin_mining():
        if not current_user.is_admin:
            abort(403)
        submissions = MiningSubmission.query.order_by(MiningSubmission.submitted_at.desc()).all()
        return render_template('admin_mining.html', submissions=submissions)

    @app.route('/admin/mining/<int:submission_id>/<action>', methods=['POST'])
    @login_required
    def manage_mining_submission(submission_id, action):
        if not current_user.is_admin:
            abort(403)

        submission = MiningSubmission.query.get_or_404(submission_id)
        try:
            if action == 'award':
                award_mining_submission(submission, current_user)
                flash('Mining submission awarded. User balance updated and treasury debited.', 'success')
            elif action == 'reject':
                reject_mining_submission(submission, current_user)
                flash('Mining submission rejected.', 'info')
            else:
                flash('Invalid action.', 'danger')
        except ValueError as e:
            flash(str(e), 'danger')

        return redirect(url_for('admin_mining'))

    @app.route('/admin/purchase-requests/<int:request_id>/<action>', methods=['POST'])
    @login_required
    def manage_purchase_request(request_id, action):
        if not current_user.is_admin:
            abort(403)

        purchase_request = PurchaseRequest.query.get_or_404(request_id)
        if action == 'approve':
            purchase_request.user.balance += purchase_request.requested_perks
            purchase_request.status = 'Approved'
            purchase_request.approved_at = datetime.utcnow()
            purchase_request.approved_by = current_user.id
            db.session.commit()
            flash('Purchase request approved and PERKS added to the user wallet.', 'success')
        elif action == 'reject':
            purchase_request.status = 'Rejected'
            purchase_request.approved_at = datetime.utcnow()
            purchase_request.approved_by = current_user.id
            db.session.commit()
            flash('Purchase request rejected.', 'success')
        else:
            flash('Invalid action.', 'danger')
        return redirect(url_for('admin_purchase_requests'))

    @app.route('/admin/users/<int:user_id>')
    @login_required
    def admin_user(user_id):
        if not current_user.is_admin:
            abort(403)

        user = User.query.get_or_404(user_id)
        terminate_form = None
        from forms import TerminateForm
        terminate_form = TerminateForm()
        return render_template('admin_user.html', user=user, terminate_form=terminate_form)

    @app.route('/admin/terminate', methods=['POST'])
    @login_required
    def admin_terminate():
        if not current_user.is_admin:
            abort(403)
        form = None
        from forms import TerminateForm
        form = TerminateForm()
        if form.validate_on_submit():
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                flash('Server shutdown is not available in this environment.', 'danger')
                return redirect(url_for('admin_user', user_id=current_user.id))
            flash('Shutting down server as requested by admin.', 'info')
            func()
            return 'Server shutting down...'
        flash('Invalid terminate request.', 'danger')
        return redirect(url_for('admin_user', user_id=current_user.id))

    @app.errorhandler(404)
    def not_found(_):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(_):
        return render_template('500.html'), 500

    @app.errorhandler(403)
    def forbidden(_):
        return render_template('403.html'), 403
