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
from app.services.auth import generate_code, create_remember_token
from flask import current_app

student_bp = Blueprint(
    "student", 
    __name__,
    url_prefix="/student"
)

# Route för elevdashboard (kollar om eleven är inloggad och visar deras uppgifter, annars skickas de till login-sidan).
@student_bp.route("/")
def index():
    if not g.student:
        return redirect("/auth/login")
    return render_template(
        "dashboard.html",
        student=g.student,
        assignments=g.student.active_assignments
    )

@student_bp.route("/student_view/<int:student_id>")
def student_view(student_id):
    student = db.session.scalar(
        select(Student).where(Student.id == student_id))
    return render_template(
        "dashboard.html",
        student=student,
        assignments=student.active_assignments
    )