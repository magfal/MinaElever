import hashlib
import secrets
import random
from datetime import datetime, timezone, timedelta
from flask import session, g, request, redirect, url_for, make_response, abort
from sqlalchemy import select, delete
from ..extensions import db
from app.models import RememberToken, User, Teacher, Student
from ..config import MAX_TOKENS_PER_STUDENT
from functools import wraps

def teacher_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not isinstance(g.user, Teacher):
            abort(403)
        return view(*args, **kwargs)
    return wrapped_view

# Registrerar autentisering som körs före varje request
def register_auth(app):
    app.before_request(load_logged_in_user)

# Genererar en unik kod (för inloggning)
def generate_code(length=8):
    characters = ("ABCDEFGHJKMNPQRTUVWXYZabcdefghjkmnpqrtuvwxyz234679")
    while True:
        code = ''.join(random.choice(characters) for _ in range(length))
        exists = db.session.scalar(select(User).where(User.login_code == code))
        if not exists:
            return code
        
# Laddar in den inloggade användaren för aktuell request
def load_logged_in_user():
    g.user = None
    user_id = session.get("user_id")
    if not user_id:
        return
    g.user = db.session.get(User, user_id)
    if g.user is None:
        session.clear()
        return
    update_remember_activity()

def logout_everywhere(user_id):
    db.session.execute(
        delete(RememberToken).where(
            RememberToken.user_id == user_id
        )
    )

def update_remember_activity():
    token = request.cookies.get("remember_token")
    if not token:
        return
    remember = get_remember_token(token)
    if not remember:
        return
    now = datetime.now(timezone.utc)
    if utcify(remember.expires_at) < now:
        db.session.delete(remember)
        db.session.commit()
        response = make_response(redirect(url_for("auth.login")))
        response.delete_cookie("remember_token")
        session.clear()
        return response
    if now - utcify(remember.last_used) > timedelta(minutes=15):
        remember.last_used = now
        db.session.commit()
        return

# Hämtar remember-token från databasen utifrån cookien
def get_remember_token(token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return db.session.scalar(
        select(RememberToken)
        .where(RememberToken.token_hash == token_hash)
    )

# Säkerställer att datetime är timezone-aware (UTC)
def utcify(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

def redirect_after_login(user):
    if user.type == "teacher":
        return redirect(url_for("students.manage"))
    if user.type == "student":
        return redirect(url_for("students.index"))
    return redirect(url_for("auth.login"))

# Skapar en "remember_me"-token för en användare och sparar den i databasen
def create_remember_token(user):
    tokens = (
        db.session.query(RememberToken)
        .filter_by(user_id=user.id)
        .order_by(RememberToken.last_used.asc())
        .all()
        )   
    if len(tokens) >= MAX_TOKENS_PER_STUDENT:
        for t in tokens[: len(tokens) - MAX_TOKENS_PER_STUDENT + 1]:
            db.session.delete(t)
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    remember = RememberToken(
        user_id=user.id,
        token_hash=token_hash,
        created_at=datetime.now(timezone.utc),
        last_used=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=180),
        ip_address=request.remote_addr,
        device=request.headers.get("User-Agent")
    )
    db.session.add(remember)
    db.session.commit()
    return token