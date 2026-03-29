# starta genom att i terminalen köra 
# sass --watch static/scss:static/css --load-path=node_modules/bootstrap/scss --quiet-deps
# python app.py

import os
from sqlalchemy import select, and_
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from datetime import datetime, timedelta, timezone
from models import db, Subject, Group, QuestionType, Question, Student, Choice, Assignment, Tag, Response
from dotenv import load_dotenv
import random
import string
from sqlalchemy import or_
from rapidfuzz import fuzz


# Genererar en unik kod för varje elev (för inloggning)
def generate_student_code(length=6):
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# Laddar inställningar lokalt från .env
load_dotenv()

app = Flask(__name__)

# SMART DATABASE URL:
# 1. Kolla om 'DATABASE_URL' finns (sätts av t.ex. Render, Heroku eller DigitalOcean)
# 2. Om inte, använd lokal sqlite-fil
default_db = 'sqlite:///mina_elever.db'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', default_db)
app.config['SECRET_KEY'] = 'en-valfri-hemlig-text-sträng'

# Öppnar upp databasen för appen
db.init_app(app)

# Skapar databasen genom att köra "flask create-db" i terminalen.
@app.cli.command("create-db")
def create_db():
    """Skapar databasen och tabellerna genom att köra "flask create-db" i terminalen."""
    with app.app_context():
        db.create_all()
        print("Databasen är skapad!")

# Här börjar våra routes (webbsidor)

@app.route("/")
def index():
    if "student_id" not in session:
        return redirect("/login")
    student = db.session.get(Student, session["student_id"])   
    if not student:
        return redirect("/login")
    now = datetime.now(timezone.utc)   
    query = (
        select(Assignment)
        .where(
            Assignment.group_id == student.group_id,
            Assignment.start_time < now,
            Assignment.end_time > now
        )
    )
    assignments = db.session.scalars(query).all()  
    print(assignments)
    return render_template("dashboard.html", student=student, assignments=assignments)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        code = request.form.get("code")
        print(code)
        query = select(Student).where(Student.login_code == code)
        student = db.session.scalar(query)
        if student:
            print(f"Loggar in student: {student.name}")
            session["student_id"] = student.id
            return redirect(url_for("index")) 
        flash("Ogiltig kod, försök igen.", "danger")       
    return render_template("login.html")

@app.route("/admin/add_group", methods=["GET", "POST"])
def add_group():
    if request.method == "POST":
        group_name = request.form.get("name")
        if not group_name:
            return "Gruppnamn saknas!", 400
        new_group = Group(name=group_name)       
        try:
            db.session.add(new_group)
            db.session.commit()
            flash(f'Gruppen "{group_name}" har skapats.', 'success')
            return redirect(url_for('add_group'))
        except IntegrityError:
            db.session.rollback()
            flash(f'Gruppen "{group_name}" finns redan!', 'error')
            return redirect(url_for('add_group'))
        except Exception as e:
            db.session.rollback()
            flash(f"Ett oväntat fel uppstod: {e}", 'error')
            return redirect(url_for('add_group'))
    return render_template("add_group.html")

@app.route('/admin/add_students', methods=["GET","POST"])
def add_students():
    if request.method == "POST":
        raw_data = request.form.get('student_list')
        group_id = request.form.get('group_id')   
        if not raw_data:
            flash("Listan var tom!", "error")
            return redirect(url_for('add_students'))
        # Dela upp texten vid varje radbrytning och rensa bort tomma rader
        student_names = [name.strip() for name in raw_data.split('\n') if name.strip()]   
        added_count = 0
        errors = 0
        for name in student_names:
            # Skapa en unik kod för varje elev
            code = generate_student_code()
            # Skapa elev-objektet (anpassa efter din modell)
            new_student = Student(
                name=name, 
                login_code=code, 
                group_id=group_id
            )
            try:
                db.session.add(new_student)
                db.session.commit()
                added_count += 1
            except IntegrityError:
                db.session.rollback()
                errors += 1
        query = select(Group.name).where(Group.id == group_id)
        group_name = db.session.scalar(query)
        if added_count == 1:
            flash(f"{added_count} elev har lagts till grupp {group_name}.", "success")
        else:
            flash(f"{added_count} elever har lagts till grupp {group_name}.", "success")
        if errors > 0:
            flash(f"{errors} elever kunde inte läggas till (kanske dubbletter).", "warning")        
        return redirect(url_for('view_group', group_id=group_id))
    query = select(Group).order_by(Group.name)
    groups = db.session.scalars(query).all()
    return render_template("add_students.html", groups=groups)

@app.route('/admin/view_group/<int:group_id>')
def view_group(group_id):
    group = db.session.get(Group, group_id)
    return render_template('view_group.html', group=group)

@app.route("/admin/add_subject", methods=["GET", "POST"])
def add_subject():
    if request.method == "POST":
        subject_name = request.form.get("name")
        if not subject_name:
            return "Ämnesnamn saknas!", 400
        new_subject = Subject(name=subject_name)
        try:
            db.session.add(new_subject)
            db.session.commit()
            flash(f'Ämnet "{subject_name}" har skapats.', 'success')
            return redirect(url_for('add_subject'))
        except IntegrityError:
            db.session.rollback()
            flash(f'Ämnet "{subject_name}" finns redan!', 'error')
            return redirect(url_for('add_subject'))
        except Exception as e:
            db.session.rollback()
            flash(f"Ett oväntat fel uppstod: {e}", 'error')
            return redirect(url_for('add_subject'))
    return render_template("add_subject.html")

@app.route("/admin/view_subjects")
def view_subjects():
    subjects = db.session.scalars(select(Subject).order_by(Subject.name)).all()
    return render_template('view_subjects.html', subjects=subjects)

@app.route("/admin/view_questions")
def view_questions():
    questions = db.session.scalars(
        select(Question).order_by(Question.id)
    ).all()

    subjects = db.session.scalars(
        select(Subject).order_by(Subject.name)
    ).all()

    # Enum-lista
    question_types = list(QuestionType)

    return render_template(
        "view_questions.html",
        questions=questions,
        subjects=subjects,
        question_types=question_types
    )

@app.route("/admin/update_question", methods=["POST"])
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

@app.route("/admin/update_tags", methods=["POST"])
def update_tags():
    data = request.json
    q = db.session.get(Question, data["id"])

    tag_names = [t.strip() for t in data["tags"].split(",") if t.strip()]

    # Rensa gamla taggar
    q.tags.clear()

    # Lägg till nya (skapa om de inte finns)
    for name in tag_names:
        tag = Tag.query.filter_by(name=name).first()
        if not tag:
            tag = Tag(name=name)
            db.session.add(tag)
        q.tags.append(tag)

    db.session.commit()
    return {"success": True}

@app.route("/admin/tag_suggest")
def tag_suggest():
    text = request.args.get("text", "")
    tags = Tag.query.filter(Tag.name.ilike(f"%{text}%")).all()
    return jsonify([t.name for t in tags])

@app.route("/admin/add_assignment")
def add_assignment():
    question_id = request.args.get("question_id", type=int)

    subjects = db.session.scalars(select(Subject)).all()
    groups = db.session.scalars(select(Group)).all()

    now = datetime.now().replace(second=0, microsecond=0)
    one_hour_later = now + timedelta(hours=1)

    selected_question = None
    if question_id:
        selected_question = db.session.get(Question, question_id)

    question_types = [qt for qt in QuestionType]
    
    return render_template(
        "add_assignment.html",
        subjects=subjects,
        groups=groups,
        now=now.isoformat(),
        one_hour_later=one_hour_later.isoformat(),
        selected_question=selected_question,
        question_types=question_types
    )

@app.route("/admin/search_questions")
def search_questions():
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


@app.route("/admin/add_assignment", methods=["POST"])
def add_assignment_post():
    subject_id = request.form.get("subject_id", type=int)
    group_id = request.form.get("group_id", type=int)
    start_time = request.form.get("start_time")
    end_time = request.form.get("end_time")

    selected_question_id = request.form.get("selected_question_id")
    new_question_text = request.form.get("new_question_text")

    # Question type (default TEXT)
    qt_str = request.form.get("question_type") or "TEXT"
    question_type = QuestionType[qt_str]

    # 1. Skapa ny fråga
    if selected_question_id == "" and new_question_text:
        new_question = Question(
            prompt=new_question_text,
            subject_id=subject_id,
            question_type=question_type,
            created_at=datetime.now()
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

@app.route("/response/<int:id>", methods=["GET", "POST"])
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

if __name__ == '__main__':
    app.run(debug=True)