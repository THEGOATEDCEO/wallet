import unittest

from app import create_app
from models import User, db


class AdminTerminateTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

        self.admin = User(username='natoshi sakamoto', email='admin@example.com', is_admin=True)
        self.admin.set_password('secret123')
        db.session.add(self.admin)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_admin_profile_shows_terminate_button(self):
        client = self.app.test_client()
        login_response = client.post('/login', data={
            'username': 'natoshi sakamoto',
            'password': 'secret123',
        }, follow_redirects=True)
        self.assertEqual(login_response.status_code, 200)

        profile_response = client.get('/profile')
        self.assertEqual(profile_response.status_code, 200)
        self.assertIn('Terminate Admin', profile_response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
