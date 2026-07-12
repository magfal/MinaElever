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
from app.models import InputType, TagType, MediaType, TemplateType, PointType
from app.models import QuestionTemplateLink
from app.models import Question, Template, Assignment, Response, User, Teacher, Student, Group, PointTransaction, Badge, Tag, Choice, RememberToken, Media 
from app.utils.student_utils import generate_student_code
from app.auth.service import create_remember_token 
from flask import current_app

auth_bp = Blueprint(
    "auth", 
    __name__,
    url_prefix="/auth"
)

# Route för login-sidan (elever loggar in med sin unika kod, genereras med "/admin/add_students".
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.student:
        return redirect(url_for("students.index"))
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        print(code)
        student = db.session.scalar(
            select(Student).where(Student.access_code == code)
        )
        if not student:
            flash("Ogiltig kod", "danger")
            return render_template("login.html")
        session.clear()
        session["student_id"] = student.id
        session.permanent = True
        token = create_remember_token(student)
        response = make_response(
            redirect(url_for("students.index"))
        )
        response.set_cookie(
            "remember_token",
            token,
            max_age=60 * 60 * 24 * 180,
            httponly=True,
            secure=not current_app.debug,
            samesite="Lax",
        )
        return response
    return render_template("login.html")

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