import hashlib
from datetime import datetime

from models import MiningSubmission, Treasury, User, db

REWARD_AMOUNT = 20
MINING_PREFIX = '00000000'


def get_treasury() -> Treasury:
    treasury = Treasury.query.first()
    if treasury is None:
        treasury = Treasury(available_perks=100)
        db.session.add(treasury)
        db.session.commit()
    return treasury


def validate_nonce(nonce: str, username: str, balance: int) -> tuple[bool, str]:
    if not nonce or len(nonce) != 15 or not nonce.isdigit():
        return False, 'Nonce must be exactly 15 digits.'

    payload = f'{nonce}{username}{balance}'
    digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    return digest.startswith(MINING_PREFIX), digest


def create_mining_submission(user: User, nonce: str, hash_value: str) -> MiningSubmission:
    submission = MiningSubmission(
        user_id=user.id,
        nonce=nonce,
        hash=hash_value,
        reward=REWARD_AMOUNT,
        status='Pending',
    )
    db.session.add(submission)
    db.session.commit()
    return submission


def award_mining_submission(submission: MiningSubmission, reviewer: User) -> None:
    treasury = get_treasury()
    if submission.status != 'Pending':
        raise ValueError('Submission is not pending.')
    if treasury.available_perks < REWARD_AMOUNT:
        raise ValueError('Insufficient Treasury balance.')

    user = User.query.get(submission.user_id)
    if not user:
        raise ValueError('User not found.')

    user.balance += REWARD_AMOUNT
    treasury.available_perks -= REWARD_AMOUNT
    submission.status = 'Awarded'
    submission.reviewed_at = datetime.utcnow()
    submission.reviewed_by = reviewer.id
    db.session.commit()


def reject_mining_submission(submission: MiningSubmission, reviewer: User) -> None:
    if submission.status != 'Pending':
        raise ValueError('Submission is not pending.')

    submission.status = 'Rejected'
    submission.reviewed_at = datetime.utcnow()
    submission.reviewed_by = reviewer.id
    db.session.commit()
