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

assignments_bp = Blueprint(
    "assignments", 
    __name__,
    url_prefix="/assignments"
)

@assignments_bp.route("/add", methods=["POST"])
def add_assignment_post():
    subject_id = request.form.get("subject_id", type=int)
    group_id = request.form.get("group_id", type=int)
    start_time = request.form.get("start_time")
    end_time = request.form.get("end_time")

    selected_question_id = request.form.get("selected_question_id")
    new_question_text = request.form.get("new_question_text")
    expected_answer = request.form.get("expected_answer"),
    extra_data = request.form.get("extra_data"),
    
    # Question type (default TEXT)
    qt_str = request.form.get("input_type") or "TEXT"
    input_type = InputType[qt_str]

    # 1. Skapa ny fråga
    if selected_question_id == "" and new_question_text:
        new_question = Question(
            text = new_question_text,
            input_type = input_type,
            expected_answer = expected_answer,
            extra_data = extra_data, 
            created_at = datetime.now()
        )
        db.session.add(new_question)
        db.session.commit()
        question_id = new_question.id

    # 2. Använd befintlig fråga
    else:
        question_id = int(selected_question_id)

    # 3. Skapa assignment
    assignment = Assignment(
        question_id=question_id,
        subject_id=subject_id,
        group_id=group_id,
        start_time=start_time,
        end_time=end_time
    )

    db.session.add(assignment)
    db.session.commit()

    flash("Assignment skapades!", "success")
    return redirect(url_for("view_assignments"))