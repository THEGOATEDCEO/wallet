import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from models import db, User

app = create_app()
with app.app_context():
    u = User.query.filter_by(username='miner_ci').first()
    if not u:
        u = User(username='miner_ci', email='miner_ci@example.com')
        u.set_password('pass1234')
        db.session.add(u)
        db.session.commit()

    client = app.test_client()
    resp = client.post('/login', data={'username':'miner_ci','password':'pass1234'}, follow_redirects=True)
    resp = client.post('/mine', data={'nonce':'123456789012345'}, follow_redirects=True)
    print('mine post status', resp.status_code)
    print('contains invalid text?', b'Invalid solution' in resp.data)
