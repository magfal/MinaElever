import hashlib
import secrets
import random
from functools import wraps
from datetime import datetime, timezone, timedelta
from flask import session, g, request, redirect, url_for, abort
from sqlalchemy import select, delete
from app.extensions import db
from app.models import RememberToken, User, Teacher
from app.config import MAX_TOKENS_PER_STUDENT

# Registrerar autentisering som körs före varje request
def register_auth(app):
    app.before_request(load_logged_in_user)

# Laddar in den inloggade användaren från sessionen eller remember-token
def load_logged_in_user():
    g.user = None
    user_id = session.get("user_id")
    if user_id is not None:
        g.user = db.session.get(User, user_id)
    if g.user is not None:
        remember_id = session.get("remember_token_id")
        if remember_id is not None:
            remember = db.session.get(
                RememberToken,
                remember_id,)
            if remember is not None:
                now = datetime.now(timezone.utc)
                if now - utcify(remember.last_used) > timedelta(minutes=15):
                    remember.last_used = now
                    db.session.commit()
        return
    # Ingen aktiv session → försök återställa den med remember-token
    token = request.cookies.get("remember_token")
    if token:
        remember = get_remember_token(token)
        if remember:
            now = datetime.now(timezone.utc)
            if utcify(remember.expires_at) >= now:
                g.user = remember.user
                session["user_id"] = g.user.id
                session["remember_token_id"] = remember.id
                session.permanent = True
                remember.last_used = now
                db.session.commit()
                return
            db.session.delete(remember)
            db.session.commit()
            session.clear()
            response = redirect(url_for("auth.login_get"))
            response.delete_cookie("remember_token")
            return response
    # Ingen session och ingen giltig remember-token
    allowed_endpoints = {
        "main.index",
        "auth.login_get",
        "auth.login_post",
        "auth.bootstrap",
        "static",
    }
    if request.endpoint not in allowed_endpoints:
        return redirect(url_for("auth.login_get"))

# Hämtar remember-token från databasen utifrån cookien
def get_remember_token(token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return db.session.scalar(
        select(RememberToken)
        .where(RememberToken.token_hash == token_hash)
    )

# Dekorator som säkerställer att användaren är en inloggad lärare
def teacher_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not isinstance(g.user, Teacher):
            abort(403)
        return view(*args, **kwargs)
    return wrapped_view

# Genererar en unik kod (för inloggning)
def generate_code(length=8):
    characters = ("ABCDEFGHJKMNPQRTUVWXYZabcdefghjkmnpqrtuvwxyz234679")
    while True:
        code = ''.join(random.choice(characters) for _ in range(length))
        exists = db.session.scalar(select(User).where(User.login_code == code))
        if not exists:
            return code

# Tar bort alla remember-tokens för en användare (loggar ut från alla enheter)
def logout_everywhere(user_id):
    db.session.execute(
        delete(RememberToken).where(
            RememberToken.user_id == user_id
        )
    )

# Säkerställer att datetime är timezone-aware (UTC)
def utcify(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

# Redirectar användaren efter inloggning baserat på användartyp
def redirect_after_login(user):
    if user.type == "teacher":
        return redirect(url_for("students.manage"))
    if user.type == "student":
        return redirect(url_for("student.index"))
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
    return remember, token