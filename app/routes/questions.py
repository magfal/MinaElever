from datetime import date, timedelta
from thefuzz import fuzz, process
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g, make_response, abort
from sqlalchemy import select
from sqlalchemy.dialects.mysql import match
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Response, Student, Group, Team, Tag, TagType, QuestionType, Question 
from app.services.htmx import toast
from app.services.auth import logout_everywhere, generate_code
from app.services.utils import utc_now

questions_bp = Blueprint(
    "questions",
    __name__,
    url_prefix="/questions",
)

# -------------------------------------------------
# HJÄLPFUNKTIONER
# -------------------------------------------------

def get_question_form_data():
    """Hämta data som behövs till frågeformuläret."""
    question_types = list(QuestionType)
    tags = db.session.scalars(
        select(Tag).order_by(Tag.name)
        ).all()
    return question_types, tags


def get_selected_tags():
    """
    Hämta valda taggar från formuläret.
    Formuläret skickar flera taggar med samma namn:
        tag_ids = [1, 4, 7, ...]
    """
    tag_ids = request.form.getlist("tag_ids")
    if not tag_ids:
        return []
    # Ta bort tomma värden och dubbletter
    tag_ids = {
        int(tag_id)
        for tag_id in tag_ids
        if tag_id.strip()
    }
    if not tag_ids:
        return []
    return db.session.scalars(
        select(Tag).where(Tag.id.in_(tag_ids))
        ).all()


# -------------------------------------------------
# HANTERA FRÅGOR
# -------------------------------------------------

@questions_bp.get("/manage")
def manage():
    search = request.args.get("search", "").strip()
    tag_id = request.args.get("tag_id", type=int)
    tag_type_name = request.args.get("tag_type", "").strip()
    question_type_name = request.args.get("question_type", "").strip()
    created_from = request.args.get("created_from", "").strip()
    created_to = request.args.get("created_to", "").strip()
    query = select(Question)
    # -------------------------------------------------
    # TAGG
    # -------------------------------------------------
    if tag_id:
        query = query.where(
            Question.tags.any(Tag.id == tag_id)
        )
    # -------------------------------------------------
    # TAGGTYP
    # -------------------------------------------------
    if tag_type_name:
        try:
            tag_type = TagType[tag_type_name]
        except KeyError:
            tag_type = None
        if tag_type:
            query = query.where(
                Question.tags.any(Tag.tag_type == tag_type)
            )
    # -------------------------------------------------
    # SVARSTYP
    # -------------------------------------------------
    if question_type_name:
        try:
            question_type = QuestionType[question_type_name]
        except KeyError:
            question_type = None
        if question_type:
            query = query.where(
                Question.question_type == question_type
            )
    # -------------------------------------------------
    # DATUM
    # -------------------------------------------------
    if created_from:
        try:
            created_from_date = date.fromisoformat(created_from)
            query = query.where(
                Question.created_at >= created_from_date
            )
        except ValueError:
            pass
    if created_to:
        try:
            created_to_date = date.fromisoformat(created_to)
            query = query.where(
                Question.created_at
                < created_to_date + timedelta(days=1)
            )
        except ValueError:
            pass
    # -------------------------------------------------
    # FRITEXTSÖKNING
    # -------------------------------------------------
    if search:
        match_expr = match(
            Question.text,
            search,
        )
        query = query.where(match_expr)
        query = query.order_by(match_expr.desc())
        # Begränsa hur många frågor vi skickar vidare
        # till fuzzy matching.
        query = query.limit(1000)
    else:
        query = query.order_by(
            Question.created_at.desc()
        )
    questions = db.session.scalars(query).all()
    # -------------------------------------------------
    # FUZZY MATCHING
    # -------------------------------------------------
    if search:
        questions_alike = []
        search_lower = search.lower()
        for question in questions:
            score = fuzz.token_set_ratio(
                search_lower,
                question.text.lower(),
            )
            if score >= 60:
                questions_alike.append(
                    (score, question)
                )
        questions_alike.sort(
            key=lambda item: item[0],
            reverse=True,
        )
        questions = [
            question
            for score, question
            in questions_alike[:100]
        ]
    # -------------------------------------------------
    # HTMX
    # -------------------------------------------------
    if request.headers.get("HX-Request"):
        return render_template(
            "questions/_questions_table.html",
            questions=questions,
        )
    # -------------------------------------------------
    # HELA SIDAN
    # -------------------------------------------------
    question_types, tags = get_question_form_data()
    tag_types = list(TagType)
    today = utc_now().strftime("%Y-%m-%d")
    return render_template(
        "questions/manage.html",
        questions=questions,
        tags=tags,
        tag_types=tag_types,
        question_types=question_types,
        today=today,
    )
# -------------------------------------------------
# NY FRÅGA
# -------------------------------------------------
@questions_bp.get("/new")
def new_form():
    question_types, tags = get_question_form_data()
    return render_template(
        "questions/new.html",
        question=None,
        question_types=question_types,
        tags=tags,
    )
@questions_bp.post("/new")
def create_question():
    text = request.form.get("text", "").strip()
    question_type_name = request.form.get("question_type","").strip()
    if not text:
        flash("Frågan måste innehålla text.", "warning")
        return redirect(
            url_for("questions.new_form")
        )
    try:
        question_type = QuestionType[question_type_name]
    except KeyError:
        flash("Ogiltig svarstyp.", "danger")
        return redirect(
            url_for("questions.new_form")
        )
    # -------------------------------------------------
    # SKAPA FRÅGA
    # -------------------------------------------------
    question = Question(
        text=text,
        question_type=question_type,
        author_id=g.user.id,
    )
    # -------------------------------------------------
    # TAGGAR
    # -------------------------------------------------
    question.tags = get_selected_tags()
    db.session.add(question)
    db.session.commit()
    flash("Frågan skapades.", "success")
    return redirect(
        url_for("questions.manage")
    )
# -------------------------------------------------
# REDIGERA FRÅGA
# -------------------------------------------------
@questions_bp.get("/edit/<int:question_id>")
def edit_question(question_id):
    question = db.session.get(
        Question,
        question_id,
    )
    if question is None:
        abort(404)
    question_types, tags = get_question_form_data()
    return render_template(
        "questions/new.html",
        question=question,
        question_types=question_types,
        tags=tags,
    )

@questions_bp.post("/edit/<int:question_id>")
def update_question(question_id):
    question = db.session.get(
        Question,
        question_id,
    )
    if question is None:
        abort(404)
    text = request.form.get("text", "").strip()
    question_type_name = request.form.get(
        "question_type",
        "",
    ).strip()
    if not text:
        flash("Frågan måste innehålla text.", "warning")
        return redirect(
            url_for(
                "questions.edit_question",
                question_id=question.id,
            )
        )
    try:
        question_type = QuestionType[
            question_type_name
        ]
    except KeyError:
        flash("Ogiltig svarstyp.", "danger")
        return redirect(
            url_for(
                "questions.edit_question",
                question_id=question.id,
            )
        )
    question.text = text
    question.question_type = question_type
    question.tags = get_selected_tags()
    db.session.commit()
    flash("Frågan uppdaterades.", "success")
    return redirect(
        url_for("questions.manage")
    )