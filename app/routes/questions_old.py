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

questions_bp = Blueprint(
    "questions",
    __name__,
    url_prefix="/questions"
)

@questions_bp.route("/create")
def create_question():
    data = request.json
    prompt = data.get('prompt')
    subject_id = data.get('subject_id')
    question_type_name = data.get('question_type')
    tags_string = data.get('tags', '')

    try:
        # 1. Skapa frågan
        new_q = Question(
            prompt=prompt,
            subject_id=subject_id,
            question_type=question_type_name
        )
        
        # 2. Bearbeta taggar
        if tags_string:
            # Gör om strängen till en lista: ["matte", "ekvation"]
            tag_names = [t.strip() for t in tags_string.split(',') if t.strip()]
            
            for name in tag_names:
                # Sök efter befintlig tagg med db.session.get eller query
                tag = db.session.query(Tag).filter_by(name=name).first()
                if not tag:
                    tag = Tag(name=name)
                    db.session.add(tag)
                
                # Lägg till taggen i frågans tagg-lista
                new_q.tags.append(tag)

        # 3. Spara allt i ett svep
        db.session.add(new_q)
        db.session.commit()
        
        return jsonify({"status": "ok", "id": new_q.id})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating question: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@questions_bp.route("/show")
def questions():
    query = select(Question).order_by(Question.id)
    questions = db.session.scalars(query).all()
    query = select(Tag).order_by(Tag.name)
    tags = db.session.scalars(query).all()
    question_types = list(QuestionType)
    return render_template(
        "questions.html",
        questions=questions,
        tags=tags,
        question_types=question_types
    )

@questions_bp.route("/update", methods=["POST"])
def update_question():
    data = request.json
    q = db.session.get(Question, data["id"])
    field = data["field"]
    value = data["value"]
    if field == "question_type":
        value = QuestionType[value]
    setattr(q, field, value)
    db.session.commit()
    return {"success": True}

# Uppdaterad sök-route för HTM
@questions_bp.route("/search")
def search_questions_table():
    text = request.args.get("text", "").strip().lower() 
    # Hämta alla frågor (eller begränsa om databasen är enorm)
    all_questions = db.session.scalars(select(Question)).all()
    if not text:
        results = all_questions
    else:
        # Fuzzy search med din befintliga logik
        scored_results = []
        for q in all_questions:
            # Kolla prompt ELLER taggar
            tag_text = " ".join([t.name.lower() for t in q.tags])
            score = max(
                fuzz.partial_ratio(text, q.prompt.lower()),
                fuzz.partial_ratio(text, tag_text)
            )
            if score > 60: # Tröskelvärde
                scored_results.append((score, q))
        # Sortera på poäng
        scored_results.sort(key=lambda x: x[0], reverse=True)
        results = [r[1] for r in scored_results]
    # Returnera enbart rader (en partial template)
    return render_template("partials/question_rows.html", questions=results)

# Route för att uppdatera ett fält (HTM-vänlig)
@questions_bp.route("update_question_field", methods=["POST"])
def update_question_field():
    q_id = request.form.get("id")
    field = request.form.get("field")
    value = request.form.get("value")
    q = db.session.get(Question, q_id)
    if field == "question_type":
        value = QuestionType[value]
    setattr(q, field, value)
    db.session.commit()
    return "", 200 # HTM behöver inget svar om vi bara vill uppdatera tyst

@questions_bp.route("/update_tags", methods=["POST"])
def update_tags():
    data = request.json
    question_id = data.get('id')
    tags_string = data.get('tags', '')
    # Modern syntax istället för Question.query.get()
    question = db.session.get(Question, question_id)
    if not question:
        return {"success": False, "error": "Frågan hittades inte"}, 404
    # Rensa befintliga kopplingar
    question.tags = []
    if tags_string:
        # Dela upp strängen till en lista av namn
        tag_names = [t.strip() for t in tags_string.split(',') if t.strip()]
        for name in tag_names:
            # Här använder vi db.session.query istället för Tag.query
            tag = db.session.query(Tag).filter_by(name=name).first()
            if not tag:
                # Om taggen inte finns, skapa den
                tag = Tag(name=name)
                db.session.add(tag)
            # Koppla taggen till frågan
            question.tags.append(tag)
    try:
        db.session.commit()
        return {"success": True}
    except Exception as e:
        db.session.rollback()
        print(f"Error saving tags: {e}")
        return {"success": False, "error": str(e)}, 500

@questions_bp.route("/tag_suggest")
def tag_suggest():
    text = request.args.get("text", "")
    if not text:
        return jsonify([])
    # Modern SQLAlchemy-syntax (istället för Tag.query)
    stmt = select(Tag).where(Tag.name.ilike(f"%{text}%")).limit(10)
    tags = db.session.execute(stmt).scalars().all()   
    return jsonify([t.name for t in tags])

@questions_bp.route("/search_2")
def search_questions_2():
    text = request.args.get("text", "").strip()
    if not text:
        return jsonify([])
    base_query = Question.query
    db_matches = base_query.filter(
        or_(
            Question.prompt.ilike(f"%{text}%"),
            Question.tags.any(Tag.name.ilike(f"%{text}%"))
        )
    ).all()
    results = {q.id: {"id": q.id, "text": q.prompt, "subject_id": q.subject_id, "score": 100}
               for q in db_matches}
    all_questions = base_query.all()
    for q in all_questions:
        score = fuzz.partial_ratio(text.lower(), q.prompt.lower())
        if score > 70:
            results[q.id] = {"id": q.id, "text": q.prompt, "subject_id": q.subject_id, "score": score}
    sorted_results = sorted(results.values(), key=lambda x: x["score"], reverse=True)
    return jsonify(sorted_results)