from flask import Blueprint
import os
import random
import string
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from rapidfuzz import fuzz
from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify, g, make_response, abort
from sqlalchemy import select, delete, and_, or_
from sqlalchemy.exc import IntegrityError
from flask_sqlalchemy import SQLAlchemy
from app.extensions import db
from app.models import QuestionType, TagType, MediaType, TemplateType, PointType
from app.models import QuestionTemplateLink
from app.models import Question, Template, Assignment, Response, User, Teacher, Student, Group, PointTransaction, Badge, Tag, Choice, RememberToken, Media 
from app.services.auth import create_remember_token, redirect_after_login, generate_code
from flask import current_app
from app.services.htmx import toast

auth_bp = Blueprint(
    "auth", 
    __name__,
    url_prefix="/auth"
)

@auth_bp.route("/bootstrap", methods=["GET", "POST"])
def bootstrap():
    # Kontrollera om en lärare redan finns
    existing_teacher = db.session.scalar(select(Teacher))
    if existing_teacher:
        return "Bootstrap redan genomförd", 403
    if request.method == "POST":
        name = request.form.get("name")
        login_code = request.form.get("login_code")
        teacher = Teacher(
            name=name,
            login_code=login_code
        )
        db.session.add(teacher)
        db.session.commit()
        flash("Första läraren skapad. Du kan nu logga in.", "success")
        return redirect(url_for("auth.login_get"))
    return render_template("auth/bootstrap.html")

@auth_bp.get("/login")
def login_get():    
    if g.user:
        return redirect_after_login(g.user)
    return render_template("login.html")

@auth_bp.post("/login")
def login_post():
    code = request.form.get("code", "").strip()
    user = db.session.scalar(
        select(User).where(User.login_code == code)
    )
    if not user:
        response = make_response(render_template(
            "login.html"))
        toast(response, "Ogiltig kod", "danger")
        return response
    session.clear()
    session["user_id"] = user.id
    session.permanent = True
    response = make_response(
        redirect_after_login(user)
    )
    token = create_remember_token(user)
    response.set_cookie(
        "remember_token",
        token,
        max_age=60*60*24*180,
        httponly=True,
        secure=not current_app.debug,
        samesite="Lax",
    )
    return response

@auth_bp.post("/logout/<int:student_id>")
def logout_student(student_id):
    student = db.session.get(
        Student,
        student_id
    )
    if not student:
        return {
            "success": False,
            "message": "Eleven hittades inte"
        }, 404
    db.session.execute(
        delete(RememberToken)
        .where(
            RememberToken.student_id == student.id
        )
    )
    db.session.commit()
    return {
        "success": True,
        "message": f"{student.name} är nu utloggad från alla enheter"
    }

# Route för logout (tar bort session och cookie).
@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    token = request.cookies.get("remember_token")
    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        db.session.execute(
            delete(RememberToken).where(
                RememberToken.token_hash == token_hash
            )
        )
        db.session.commit()
    session.clear()
    response = make_response(redirect(url_for("auth.login")))
    response.delete_cookie("remember_token")
    return response 