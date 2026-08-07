import re
import unittest

from app import create_app
from models import User, db


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_registration_succeeds_with_valid_csrf_token(self):
        client = self.app.test_client()

        response = client.get('/register')
        self.assertEqual(response.status_code, 200)

        html = response.get_data(as_text=True)
        match = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', html)
        self.assertIsNotNone(match, 'Expected a CSRF token in the registration page')

        token = match.group(1)
        response = client.post('/register', data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'secret123',
            'confirm_password': 'secret123',
            'csrf_token': token,
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.query.filter_by(username='newuser').first())


if __name__ == '__main__':
    unittest.main()
