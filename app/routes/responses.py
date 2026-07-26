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

responses_bp = Blueprint(
    "responses", 
    __name__,
    url_prefix="/responses"
)

#Sparar response
@responses_bp.route("/add_observation", methods=["GET", "POST"])
def add_observation():
    pass

#Sparar response
@responses_bp.route("/add_note", methods=["GET", "POST"])
def add_note():
    pass

#Sparar response
@responses_bp.route("/save", methods=["GET", "POST"])
def save_response():
    student_ids = request.form.getlist("student_ids")
    text = request.form.get("text")
    response_type = request.form.get("response_type")
    for student_id in student_ids:
        response = Response(
            student_id=student_id,
            student_question=None,
            comment=text,
            extra_data={
                "type": response_type
            },
            submitted_at=datetime.now(timezone.utc)
        )
        db.session.add(response)
    db.session.commit()
    flash("Sparat!", "success")
    return redirect(url_for("students"))

@responses_bp.route("/response/<int:id>", methods=["GET", "POST"])
def response(id):
   if "student_id" not in session:
       return redirect("/login")
   question = Question.query.get(id)
   if request.method == "POST":
       student_id = session["student_id"]
       ip = request.remote_addr
       device = request.headers.get("User-Agent")
       response = Response(
           student_id=student_id,
           question_id=id,
           text_answer=request.form.get("text"),
           slider_value=request.form.get("slider"),
           choice_id=request.form.get("choice"),
           ip_address=ip,
           device=device
       )
       db.session.add(response)
       db.session.commit()
       return redirect("/")
   choices = Choice.query.filter_by(
       assignment_id=id
   ).all()
   return render_template(
       "response.html",
        question=question,
        choices=choices
   )

