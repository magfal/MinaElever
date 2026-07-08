# starta programmet genom att i terminalen köra 
# sass --watch static/scss:static/css --load-path=node_modules/bootstrap/scss --quiet-deps
# python app.py

import os
import random
import string
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from rapidfuzz import fuzz
from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify, g, make_response 
from sqlalchemy import select, delete, and_, or_
from sqlalchemy.exc import IntegrityError
from flask_sqlalchemy import SQLAlchemy
from models import db, Subject, Group, QuestionType, Question, Student, Choice, Assignment, Tag, Response, RememberToken

MAX_TOKENS_PER_STUDENT = 5

load_dotenv() # Laddar inställningar lokalt från .env

### HJÄLPFUNKTIONER ###

# Konverterar datetime till UTC om den inte redan är det
def utcify(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

# Genererar en unik kod för varje elev (för inloggning)
def generate_student_code(length=6):
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# Skapar en "remember me"-token för en student och sparar den i databasen
def create_remember_token(student):
    # 1. Hämta alla tokens för eleven
    tokens = (
        db.session.query(RememberToken)
        .filter_by(student_id=student.id)
        .order_by(RememberToken.last_used.asc())
        .all()
    )
    # 2. Om vi har för många → ta bort de äldsta
    if len(tokens) >= MAX_TOKENS_PER_STUDENT:
        for t in tokens[: len(tokens) - MAX_TOKENS_PER_STUDENT + 1]:
            db.session.delete(t)
    # 3. Skapa ny token
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    remember = RememberToken(
        student_id=student.id,
        token_hash=token_hash,
        created_at=datetime.now(timezone.utc),
        last_used=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=180)
    )
    db.session.add(remember)
    db.session.commit()
    return token

app = Flask(__name__)

# SMART DATABASE URL:
# 1. Kolla om 'DATABASE_URL' finns (sätts av t.ex. Render, Heroku eller DigitalOcean)
# 2. Om inte, använd lokal sqlite-fil
default_db = 'sqlite:///mina_elever.db'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', default_db)
app.config['SECRET_KEY'] = 'en-valfri-hemlig-text-sträng'

# Öppnar upp databasen för appen
db.init_app(app)

# Skapa databasen genom att köra "flask create-db" i terminalen.
@app.cli.command("create-db")
def create_db():
    with app.app_context():
        db.create_all()
        print("Databasen är skapad!")

# Flask-funktion som körs innan varje request för att kolla om studenten är inloggad via session eller cookie.
@app.before_request
def load_logged_in_student():
    student_id = session.get("student_id")
    if student_id:
        g.student = db.session.get(Student, student_id)
        return
    g.student = None
    token = request.cookies.get("remember_token")
    if not token:
        return
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    remember = db.session.scalar(
        select(RememberToken).where(RememberToken.token_hash == token_hash)
    )
    if not remember:
        return
    print(remember.expires_at)
    print(remember.expires_at.tzinfo)
    print(datetime.now(timezone.utc))
    print("EXPIRES RAW:", remember.expires_at)
    print("TZINFO:", remember.expires_at.tzinfo)
    print("TYPE:", type(remember.expires_at))
    if utcify(remember.expires_at) < datetime.now(timezone.utc):
        db.session.delete(remember)
        db.session.commit()
        return
    student = db.session.get(Student, remember.student_id)
    if not student:
        return
    # logga in
    session["student_id"] = student.id
    g.student = student
    # uppdatera aktivitet
    remember.last_used = datetime.now(timezone.utc)
    db.session.commit()
    
# Hjälpfunktion för att hämta eller skapa taggar
def get_or_create_tag(tag_name):
    tag = db.session.execute(db.select(Tag).filter_by(name=tag_name)).scalar_one_or_none()
    if not tag:
        tag = Tag(name=tag_name)
    return tag

#################################
### HÄR BÖRJAR FLASK-ROUTERNA ###
#################################

# Route för startsidan (kollar om eleven är inloggad och visar deras uppgifter, annars skickas de till login-sidan).
@app.route("/")
def index():
    if not g.student:
        return redirect("/login")
    now = datetime.now(timezone.utc)
    query = (
        select(Assignment)
        .where(
            Assignment.group_id == g.student.group_id,
            Assignment.start_time < now,
            Assignment.end_time > now,
        )
    )
    assignments = db.session.scalars(query).all()
    return render_template("dashboard.html", student=g.student, assignments=assignments)

# Route för login-sidan (elever loggar in med sin unika kod, genereras med "/admin/add_students".
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        student = db.session.scalar(
            select(Student).where(Student.login_code == code)
        )
        if not student:
            flash("Ogiltig kod", "danger")
            return render_template("login.html")
        session.clear()
        session["student_id"] = student.id
        # skapa token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        remember = RememberToken(
            student_id=student.id,
            token_hash=token_hash,
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=180),
        )
        db.session.add(remember)
        db.session.commit()
        response = make_response(redirect(url_for("index")))
        response.set_cookie(
            "remember_token",
            token,
            max_age=60 * 60 * 24 * 180,
            httponly=True,
            secure=True,
            samesite="Lax",
        )
        return response
    return render_template("login.html")

# Route för logout (tar bort session och cookie).
@app.route("/logout")
def logout():
    token = request.cookies.get("remember_token")
    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        db.session.execute(
            delete(RememberToken).where(
                RememberToken.token_hash == token_hash
            )
        )
        db.session.commit()
    session.clear()
    response = make_response(redirect(url_for("login")))
    response.delete_cookie("remember_token")
    return response

#  Route för att lägga till grupper.
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

# Route för att lägga till elever (flera på en gång) i en grupp.
@app.route('/admin/add_students', methods=["GET","POST"])
def add_students():
    if request.method == "POST":
        raw_data = request.form.get('student_list')
        group_id = request.form.get('group_id')   
        if not raw_data:
            flash("Listan var tom!", "error")
            return redirect(url_for('add_students'))
        student_names = [name.strip() for name in raw_data.split('\n') if name.strip()]   
        added_count = 0
        errors = 0
        for name in student_names:
            code = generate_student_code()
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

# Route för att uppdatera en elevs inloggningskod (genererar en ny kod).
@app.route('/admin/update_student_code', methods=["GET", "POST"])
def update_student_code():
    if request.method == "POST":
        student_id = request.form.get("student_id")
        new_code = generate_student_code()
        student = db.session.get(Student, student_id)
        if student:
            student.login_code = new_code
            db.session.commit()
            flash(f"Ny inloggningskod för {student.name}: {new_code}", "success")
        else:
            flash("Elev inte hittad", "danger")
    students = db.session.scalars(select(Student)).all()
    return render_template(
        "update_student_code.html",
        students=students
    )

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

@app.route("/admin/questions")
def questions():
    query = select(Question).order_by(Question.id)
    questions = db.session.scalars(query).all()
    query = select(Subject).order_by(Subject.name)
    subjects = db.session.scalars(query).all()
    question_types = list(QuestionType)
    return render_template(
        "questions.html",
        questions=questions,
        subjects=subjects,
        question_types=question_types
    )

@app.route("/admin/create_question", methods=["POST"])
def create_question():
    data = request.json
    prompt = data.get('prompt')
    subject_id = data.get('subject_id')
    question_type_name = data.get('question_type')
    tags_string = data.get('tags', '') # Hämtar t.ex. "matte,ekvation"

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

# Uppdaterad sök-route för HTM
@app.route("/admin/search_questions_table")
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
@app.route("/admin/update_question_field", methods=["POST"])
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

@app.route("/admin/update_tags", methods=["POST"])
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

@app.route("/admin/tag_suggest")
def tag_suggest():
    text = request.args.get("text", "")
    if not text:
        return jsonify([])
    # Modern SQLAlchemy-syntax (istället för Tag.query)
    stmt = select(Tag).where(Tag.name.ilike(f"%{text}%")).limit(10)
    tags = db.session.execute(stmt).scalars().all()   
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