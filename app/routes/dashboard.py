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

dashboard_bp = Blueprint(
    "dashboard", 
    __name__,
    url_prefix="/dashboard"
)

# Route för elevdashboard (kollar om eleven är inloggad och visar deras uppgifter, annars skickas de till login-sidan).
@dashboard_bp.route("/")
def index():
    if not g.student:
        return redirect("/auth/login")
    return render_template(
        "dashboard.html",
        student=g.student,
        assignments=g.student.active_assignments
    )

@dashboard_bp.route("/student_view/<int:student_id>")
def student_view(student_id):
    student = db.session.scalar(
        select(Student).where(Student.id == student_id))
    return render_template(
        "dashboard.html",
        student=student,
        assignments=student.active_assignments
    )