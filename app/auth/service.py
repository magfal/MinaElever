import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from flask import session, g, request
from sqlalchemy import select
from ..extensions import db
from app.models import Student, RememberToken
from ..config import MAX_TOKENS_PER_STUDENT

# Konverterar datetime till UTC om den inte redan är det
def utcify(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

# Skapar en "remember me"-token för en student och sparar den i databasen
def create_remember_token(student):
    # 1. Hämta alla tokens för eleven
    tokens = (
        db.session.query(RememberToken)
        .filter_by(student_id=student.id)
        .order_by(RememberToken.last_used.asc())
        .all()
        )
    # 2. Om vi har för många → ta bort de äldsta
    if len(tokens) >= MAX_TOKENS_PER_STUDENT:
        for t in tokens[: len(tokens) - MAX_TOKENS_PER_STUDENT + 1]:
            db.session.delete(t)
    # 3. Skapa ny token
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    remember = RememberToken(
        student_id=student.id,
        token_hash=token_hash,
        created_at=datetime.now(timezone.utc),
        last_used=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=180)
    )
    db.session.add(remember)
    db.session.commit()
    return token

# Flask-funktion som körs innan varje request för att kolla om studenten är inloggad via session eller cookie.
def load_logged_in_student():
    student_id = session.get("student_id")
    if student_id:
        g.student = db.session.get(Student, student_id)
        return
    g.student = None
    token = request.cookies.get("remember_token")
    if not token:
        return
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    remember = db.session.scalar(
        select(RememberToken).where(RememberToken.token_hash == token_hash)
    )
    if not remember:
        return
    if utcify(remember.expires_at) < datetime.now(timezone.utc):
        db.session.delete(remember)
        db.session.commit()
        return
    student = db.session.get(Student, remember.student_id)
    if not student:
        return
    # logga in
    session["student_id"] = student.id
    g.student = student
    # uppdatera aktivitet
    remember.last_used = datetime.now(timezone.utc)
    db.session.commit()

def init_auth(app):
    app.before_request(load_logged_in_student)

print("Laddar auth.service")
print("init_auth finns:", "init_auth" in dir())