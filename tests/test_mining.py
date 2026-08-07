import unittest

from flask import Flask

from models import MiningSubmission, Treasury, User, db
from mining import award_mining_submission, reject_mining_submission


class MiningWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SECRET_KEY'] = 'test-secret'
        db.init_app(self.app)
        # push an app context for the lifetime of the test so model instances remain bound
        self.ctx = self.app.app_context()
        self.ctx.push()

        db.create_all()
        self.admin = User(username='admin_test', email='admin_test@example.com', is_admin=True)
        self.admin.set_password('password')
        self.user = User(username='miner_test', email='miner_test@example.com')
        self.user.set_password('password')
        db.session.add_all([self.admin, self.user])
        db.session.commit()

    def tearDown(self):
        # clean up and pop the app context
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_award_updates_balance_and_treasury(self):
        with self.app.app_context():
            treasury = Treasury(available_perks=100)
            db.session.add(treasury)
            submission = MiningSubmission(user_id=self.user.id, nonce='123456789012345', hash='abc', reward=20, status='Pending')
            db.session.add(submission)
            db.session.commit()

            award_mining_submission(submission, self.admin)

            reloaded_user = User.query.get(self.user.id)
            reloaded_treasury = Treasury.query.get(treasury.id)
            reloaded_submission = MiningSubmission.query.get(submission.id)

            self.assertEqual(reloaded_user.balance, 20)
            self.assertEqual(reloaded_treasury.available_perks, 80)
            self.assertEqual(reloaded_submission.status, 'Awarded')
            self.assertEqual(reloaded_submission.reviewed_by, self.admin.id)

    def test_reject_marks_submission_rejected(self):
        with self.app.app_context():
            treasury = Treasury(available_perks=100)
            db.session.add(treasury)
            submission = MiningSubmission(user_id=self.user.id, nonce='987654321098765', hash='abc', reward=20, status='Pending')
            db.session.add(submission)
            db.session.commit()

            reject_mining_submission(submission, self.admin)

            self.assertEqual(submission.status, 'Rejected')
            self.assertEqual(submission.reviewed_by, self.admin.id)
            self.assertEqual(treasury.available_perks, 100)


if __name__ == '__main__':
    unittest.main()
