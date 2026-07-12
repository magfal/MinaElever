import random
from sqlalchemy import select
from app.extensions import db
from app.models import User

# Genererar en unik kod (för inloggning)
def generate_student_code(length=8):
    characters = ("ABCDEFGHJKMNPQRTUVWXYZabcdefghjkmnpqrtuvwxyz234679")
    while True:
        code = ''.join(random.choice(characters) for _ in range(length))
        exists = db.session.scalar(select(User).where(User.access_code == code))
        if not exists:
            return code