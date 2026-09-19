import os
import uuid
import re
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename
from datetime import date, timedelta
from thefuzz import fuzz, process
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g, make_response, abort, current_app, send_file
from sqlalchemy import select, case
from sqlalchemy.dialects.mysql import match
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Media, Tag, TagType, QuestionType, Question, Choice, MediaType 
from app.services.htmx import toast
from app.services.auth import logout_everywhere, generate_code
from app.services.utils import utc_now, save_image
from app.services.tags import get_selected_tags

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

def get_media_from_question_text(text):
    names = re.findall(r"\[([^\[\]:]+)(?::\d+)?\]", text)
    if not names:
        return []
    return (
        db.session.query(Media)
        .filter(
            Media.name.in_(names),
            Media.media_type == MediaType.IMAGE,
        )
        .all()
    )

def question_is_locked(question):
    now = utc_now()
    return any(
        assignment.end_time is not None
        and assignment.end_time < now
        for link in question.template_links
        for assignment in link.template.assignments
    )

def populate_question_answer(question):
    question_type = question.question_type
    # --------------------------------
    # TEXT
    # --------------------------------
    if question_type == QuestionType.TEXT:
        answers = [
            answer.strip()
            for answer in request.form.getlist(
                "correct_answers"
            )
            if answer.strip()
        ]
        question.expected_answer = (
            {"answers": answers}
            if answers
            else None
        )
    # --------------------------------
    # NUMBER
    # --------------------------------
    elif question_type == QuestionType.NUMBER:
        value = request.form.get(
            "correct_number",
            ""
        ).strip()
        if value:
            try:
                question.expected_answer = {
                    "answer": float(value)
                }
            except ValueError:
                raise ValueError(
                    "Rätt svar måste vara ett tal."
                )
        else:
            question.expected_answer = None
    # --------------------------------
    # BOOLEAN
    # --------------------------------
    elif question_type == QuestionType.BOOLEAN:
        value = request.form.get("correct_boolean")
        if value is not None:
            question.expected_answer = {
                "answer": value == "true"
            }
        else:
            question.expected_answer = None
    # --------------------------------
    # DATE
    # --------------------------------
    elif question_type == QuestionType.DATE:
        value = request.form.get(
            "correct_date",
            ""
        ).strip()
        if value:
            try:
                parsed_date = date.fromisoformat(value)
                question.expected_answer = {
                    "answer": parsed_date.isoformat()
                }
            except ValueError:
                raise ValueError(
                    "Ogiltigt datum."
                )
        else:
            question.expected_answer = None
    # --------------------------------
    # SLIDER
    # --------------------------------
    elif question_type == QuestionType.SLIDER:
        value = request.form.get(
            "correct_number",
            ""
        ).strip()
        if value:
            try:
                question.expected_answer = {
                    "answer": float(value)
                }
            except ValueError:
                raise ValueError(
                    "Rätt svar måste vara ett tal."
                )
        else:
            question.expected_answer = None
    # --------------------------------
    # SINGLE CHOICE
    # --------------------------------
    elif question_type == QuestionType.SINGLE_CHOICE:
        choice_options = [
            value.strip()
            for value in request.form.getlist(
                "choice_options"
            )
            if value.strip()
        ]
        correct_index = request.form.get(
            "correct_choice_index"
        )
        if correct_index is not None:
            try:
                correct_index = int(correct_index)
            except ValueError:
                correct_index = None
        question.choices.clear()
        for index, choice_text in enumerate(choice_options):
            question.choices.append(
                Choice(
                    text=choice_text,
                    is_correct=(
                        correct_index == index
                    )
                )
            )
        question.expected_answer = None
    # --------------------------------
    # MULTIPLE CHOICE
    # --------------------------------
    elif question_type == QuestionType.MULTIPLE_CHOICE:
        choice_options = [
            value.strip()
            for value in request.form.getlist(
                "choice_options"
            )
            if value.strip()
        ]
        correct_indexes = {
            int(value)
            for value in request.form.getlist(
                "correct_choice_indexes"
            )
            if value.isdigit()
        }
        question.choices.clear()
        for index, choice_text in enumerate(choice_options):
            question.choices.append(
                Choice(
                    text=choice_text,
                    is_correct=(
                        index in correct_indexes
                    )
                )
            )
        question.expected_answer = None
    # --------------------------------
    # FILE UPLOAD
    # --------------------------------
    elif question_type == QuestionType.FILE_UPLOAD:
        question.expected_answer = None

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
    media_id = request.args.get("media_id", type=int)
    query = select(Question)
    if media_id:
        query = query.where(
            Question.media.any(Media.id == media_id)
        )
    if tag_id:
        query = query.where(
            Question.tags.any(Tag.id == tag_id)
        )
    if tag_type_name:
        try:
            tag_type = TagType[tag_type_name]
        except KeyError:
            tag_type = None
        if tag_type:
            query = query.where(
                Question.tags.any(Tag.tag_type == tag_type)
            )
    if question_type_name:
        try:
            question_type = QuestionType[question_type_name]
        except KeyError:
            question_type = None
        if question_type:
            query = query.where(
                Question.question_type == question_type
            )
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
    if search:
        terms = [
            term.strip()
            for term in search.split()
            if len(term.strip()) >= 2
            ]
        if terms:
            score = sum(
                case(
                    (Question.text.ilike(f"%{term}%"), 1),
                    else_=0,
                )
                for term in terms
            )
            query = (
                query
                .where(score > 0)
                .order_by(score.desc())
                .limit(100)
            )
            query = query
        else:
            query = query.limit(100)
    else:
        query = query.order_by(Question.created_at.desc()).limit(100)
    
    questions = db.session.scalars(query).all()
    
    if request.headers.get("HX-Request"):
        return render_template(
            "questions/_questions_table.html",
            questions=questions,
        )
    
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
        tag_id=tag_id,
        tag_type_name=tag_type_name,
        question_type_name=question_type_name,
        created_from=created_from,
        created_to=created_to,
        search=search,
        media_id=media_id,
    )

# -------------------------------------------------
# NY FRÅGA
# -------------------------------------------------
@questions_bp.get("/new")
def new_form():
    question_types, tags = get_question_form_data()

    media = (
        db.session.query(Media)
        .filter(Media.media_type == MediaType.IMAGE)
        .order_by(Media.created_at.desc())
        .all()
    )

    media_tags = (
        db.session.query(Tag)
        .order_by(Tag.name)
        .all()
    )

    media_map = {
        item.name: item.id
        for item in media
    }

    return render_template(
        "questions/new.html",
        question=None,
        question_types=question_types,
        tags=tags,
        question_data=None,
        media=media,
        media_tags=media_tags,
        media_map=media_map,
    )

@questions_bp.post("/new")
def create_question():
    text = request.form.get("text", "").strip() 
    question_type_name = request.form.get("question_type", QuestionType.TEXT.name).strip()    
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

    question.media = get_media_from_question_text(question.text)
    # -------------------------------------------------
    # TAGGAR
    # -------------------------------------------------
    question.tags = get_selected_tags()   
    try:
        populate_question_answer(question)
    except ValueError as error:
        flash(str(error), "danger")
        return redirect(
            url_for("questions.new_form")
        )    
    db.session.add(question)
    db.session.commit()
    flash(
        "Frågan har sparats.",
        "success"
    )
    return redirect(
        url_for(
            "questions.manage"
        )
    )

# -------------------------------------------------
# KOPIERA FRÅGA
# -------------------------------------------------
@questions_bp.post("/copy/<int:question_id>")
def copy_question(question_id):
    source = db.session.get(
        Question,
        question_id,
    )

    if source is None:
        abort(404)

    text = request.form.get(
        "text",
        "",
    ).strip()

    question_type_name = request.form.get(
        "question_type",
        "",
    ).strip()

    if not text:
        flash(
            "Frågan måste innehålla text.",
            "warning",
        )
        return redirect(
            url_for(
                "questions.edit_question",
                question_id=source.id,
            )
        )

    try:
        question_type = QuestionType[
            question_type_name
        ]
    except KeyError:
        flash(
            "Ogiltig svarstyp.",
            "danger",
        )
        return redirect(
            url_for(
                "questions.edit_question",
                question_id=source.id,
            )
        )

    # Ny fråga
    question = Question(
        text=text,
        question_type=question_type,
        author_id=g.user.id,
    )

    # Taggar från formuläret
    question.tags = get_selected_tags()

    # Facit och svarsalternativ från formuläret
    try:
        populate_question_answer(question)
    except ValueError as error:
        flash(
            str(error),
            "danger",
        )
        return redirect(
            url_for(
                "questions.edit_question",
                question_id=source.id,
            )
        )

    # Återanvänd samma Media-poster som originalfrågan
    question.media = get_media_from_question_text(question.text)
    db.session.add(question)
    db.session.commit()

    flash(
        "Frågan kopierades.",
        "success",
    )

    return redirect(url_for("questions.manage"))

# -------------------------------------------------
# REDIGERA FRÅGA
# -------------------------------------------------
@questions_bp.get("/edit/<int:question_id>")
def edit_question(question_id):
    question = db.session.get(Question, question_id)
    if question is None:
        abort(404)
    question_types, tags = get_question_form_data()
    media = (
        db.session.query(Media)
        .filter(Media.media_type == MediaType.IMAGE)
        .order_by(Media.created_at.desc())
        .all()
    )
    media_tags = (
        db.session.query(Tag)
        .order_by(Tag.name)
        .all()
    )
    media_map = {
        item.name: item.id
        for item in media
    }
    return render_template(
        "questions/new.html",
        question=question,
        question_is_locked=question_is_locked(question),
        question_types=question_types,
        tags=tags,
        question_data={
            "expected_answer": question.expected_answer,
            "choices": [
                {
                    "text": choice.text,
                    "is_correct": choice.is_correct,
                }
                for choice in question.choices
            ],
        },
        media=media,
        media_tags=media_tags,
        media_map=media_map,
    )

@questions_bp.post("/edit/<int:question_id>")
def update_question(question_id):
    question = db.session.get(
        Question,
        question_id,
    )
    if question is None:
        abort(404)
    if question_is_locked(question):
        abort(403)
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
    question.media = get_media_from_question_text(text)
    question.question_type = question_type
    question.tags = get_selected_tags()
    try:
        populate_question_answer(question)
    except ValueError as error:
        flash(str(error), "danger")
        return redirect(
            url_for(
                "questions.edit_question",
                question_id=question.id
            )
        )
    db.session.commit()
    flash("Frågan uppdaterades.", "success")
    return redirect(
        url_for("questions.manage")
    )



# -------------------------------------------------
# REDIGERA FRÅGA
# -------------------------------------------------
@questions_bp.post("/delete_question/<int:question_id>")
def delete_question(question_id):
    question = db.session.get(Question, question_id)

    if not question:
        flash("Frågan hittades inte.", "danger")
        return redirect(url_for("questions.manage"))

    if question.template_links:
        flash(
            "Frågan används i en mall och kan därför inte tas bort.",
            "danger"
        )
        return redirect(url_for("questions.manage"))

    if question.responses:
        flash(
            "Frågan har elevsvar och kan därför inte tas bort permanent.",
            "danger"
        )
        return redirect(url_for("questions.manage"))

    db.session.delete(question)
    db.session.commit()

    flash("Frågan togs bort permanent.", "success")
    return redirect(url_for("questions.manage"))