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
from sqlalchemy.orm import joinedload
from flask_sqlalchemy import SQLAlchemy
from app.extensions import db
from app.models import QuestionType, TagType, MediaType, AssignmentType, PointType, ResponseType
from app.models import QuestionTemplateLink, ResponseStatus
from app.models import Question, Template, Assignment, Response, User, Teacher, Student, Group, PointTransaction, Badge, Tag, Choice, RememberToken, Media 
from app.services.utils import utc_now, local_to_utc, utcify, SWEDEN_TZ

student_bp = Blueprint(
    "student", 
    __name__,
    url_prefix="/student"
)

def get_student(student_id):
    if isinstance(g.user, Teacher):
        student = db.session.get(Student, student_id)
        if student is None:
            abort(404)
        return student
    if isinstance(g.user, Student):
        if g.user.id != student_id:
            abort(403)
        return g.user
    abort(403)

def get_active_assignments(student_id):
    now = utc_now()
    # Öppna assignments vars starttid har passerat.
    prepared_responses = db.session.scalars(
        select(Response)
        .join(Response.assignment)
        .where(
            Response.student_id == student_id,
            Response.response_type == ResponseType.ASSIGNMENT,
            Response.status == ResponseStatus.PREPARED,
            Assignment.start_time.is_not(None),
            Assignment.start_time <= now,
        )
    ).all()
    for response in prepared_responses:
        response.status = ResponseStatus.OPEN
    if prepared_responses:
        db.session.commit()
    # Hämta elevens aktiva assignments.
    responses = db.session.scalars(
        select(Response)
        .join(Response.assignment)
        .options(
            joinedload(Response.assignment)
            .joinedload(Assignment.template)
        )
        .where(
            Response.student_id == student_id,
            Response.response_type == ResponseType.ASSIGNMENT,
            Response.status.in_(
                [
                    ResponseStatus.OPEN,
                    ResponseStatus.SAVED,
                ]
            ),
            (
                Assignment.end_time.is_(None)
                | (Assignment.end_time > now)
            ),
        )
        .order_by(Assignment.end_time)
    ).all()

    return [
        response.assignment
        for response in responses
        if response.assignment is not None
    ]

@student_bp.route("/")
def index():
    if not isinstance(g.user, Student):
        abort(403)
    return redirect(url_for(
        "student.student_view",
        student_id=g.user.id)
    )

@student_bp.route("/student_view/<int:student_id>")
def student_view(student_id):
    student = get_student(student_id)
    teacher_view = isinstance(g.user, Teacher)
    assignments = get_active_assignments(student.id)
    return render_template(
        "student/dashboard.html",
        student=student,
        assignments=assignments,
        teacher_view=teacher_view
    )

@student_bp.route("/questions/<int:student_id>")
def questions(student_id):
    return redirect(url_for(
        "student.index")
    )

@student_bp.route("/old_assignments/<int:student_id>")
def old_assignments(student_id):
    return redirect(url_for(
        "student.index")
    )
@student_bp.route("/xp/<int:student_id>")
def xp(student_id):
    return redirect(url_for(
        "student.index")
    )

@student_bp.route("/assignment/<int:assignment_id>")
def assignment(assignment_id):
    if not g.student:
        return redirect("/auth/login")

    # Hämta assignmenten
    assignment = db.session.scalar(
        select(Assignment)
        .options(
            joinedload(Assignment.template)
        )
        .where(
            Assignment.id == assignment_id
        )
    )

    if assignment is None:
        abort(404)

    # Kontrollera att eleven faktiskt har denna assignment.
    student_response = db.session.scalar(
        select(Response)
        .where(
            Response.student_id == g.student.id,
            Response.assignment_id == assignment.id,
            Response.response_type == ResponseType.ASSIGNMENT,
        )
    )

    if student_response is None:
        abort(404)

    # Hämta frågorna i mallens ordning.
    questions = db.session.scalars(
        select(Question)
        .join(
            QuestionTemplateLink,
            QuestionTemplateLink.question_id == Question.id,
        )
        .where(
            QuestionTemplateLink.template_id == assignment.template_id
        )
        .order_by(
            QuestionTemplateLink.position
        )
    ).all()

    return render_template(
        "student/assignment.html",
        assignment=assignment,
        student_response=student_response,
        questions=questions,
        student=g.student,
    )