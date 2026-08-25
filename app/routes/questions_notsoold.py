from datetime import date, timedelta
from flask import Blueprint
from flask import render_template, request, redirect, url_for, flash, jsonify, g, make_response, abort
from sqlalchemy import select
from sqlalchemy.dialects.mysql import match
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Response, Student, Group, Team, Tag, TagType, QuestionType, Question 
from app.services.htmx import toast
from app.services.auth import logout_everywhere, generate_code
from app.services.utils import utc_now
from thefuzz import fuzz, process

questions_bp = Blueprint(
    "questions",
    __name__,
    url_prefix="/questions"
)

@questions_bp.get("/manage")
def manage():
    search = request.args.get("search", "").strip().lower() 
    tag_id = request.args.get("tag_id", type=int)
    tag_type_id = request.args.get("tag_type_id", type=int)
    q_type_id = request.args.get("q_type_id", type=int)
    created_from = request.args.get("created_from")
    created_to = request.args.get("created_to")
    query = select(Question)
    # Tag
    if tag_id:
        query = query.where(Question.tags.any(Tag.id == tag_id))
    # Tag type
    if tag_type_id:
        query = query.where(Question.tags.any(Tag.tag_type_id == tag_type_id))
    # Question type
    if q_type_id:
        query = query.where(Question.question_type_id == q_type_id)
    # Datum
    if created_to:
        created_to_date = date.fromisoformat(created_to)
        query = query.where(
            Question.created_at < created_to_date + timedelta(days=1))
    if created_to:
        created_to_date = date.fromisoformat(created_to)
        query = query.where(
            Question.created_at < created_to_date + timedelta(days=1))
    # Fritextsökning
    if search:
        match_expr = match(Question.text, search)
        query = query.where(match_expr)
        query = query.order_by(match_expr.desc())
        query = query.limit(1000)
    questions = db.session.scalars(query).all()    
    if search:
        questions_alike = []
        for q in questions:
            score = fuzz.token_set_ratio(search, q.text.lower())
            if score > 60:
                questions_alike.append((score, q))
        questions_alike.sort(key=lambda x: x[0], reverse=True)
        questions = [question for score, question in questions_alike[:100]]
        questions = [q for score, q in questions_alike]
    if request.headers.get("HX-Request"):
        return render_template(
            "questions/_questions_table.html",
            questions=questions_alike
        )
    question_types = list(QuestionType)
    tag_types = list(TagType)
    tags = db.session.scalars(
        db.select(Tag)
        .order_by(Tag.name)
    ).all()
    today = utc_now().strftime("%Y-%m-%d")
    return render_template(
        "questions/manage.html",
        questions=questions,
        tags=tags,
        tag_types=tag_types,
        today=today,
        question_types=question_types
        )

@questions_bp.get("/new")
def new_form():
    question_types = list(QuestionType)
    tags = db.session.scalars(
        db.select(Tag)
        .order_by(Tag.name)
    ).all()
    return render_template(
        "questions/new.html",
        question = "",
        tags = tags,
        question_types = question_types)

@questions_bp.post("/new")
def new_question():
    question_id = request.args.get("question_id", type=int)
    question_types = list(QuestionType)
    question = db.session.get(Question, question_id)
    tags = db.session.scalars(
        db.select(Tag)
        .order_by(Tag.name)
    ).all()
    return render_template(
        "questions/new.html",
        tags = tags,
        question_types = question_types)

@questions_bp.post("/edit")
def edit_question():
    
    question_types = list(QuestionType)
    tags = db.session.scalars(
        db.select(Tag)
        .order_by(Tag.name)
    ).all()
    return render_template(
        "questions/new.html",
        question = "",
        tags = tags,
        question_types = question_types)
    return

@questions_bp.post("/new")
def new_add():
    return

@questions_bp.post("/add_tag")
def add_tag():
    return

@questions_bp.get("/search")
def search():
    return