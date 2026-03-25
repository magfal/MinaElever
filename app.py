import os
from sqlalchemy import select
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from flask import Flask, render_template, request, redirect, session, url_for, flash
from datetime import datetime
from models import db, Subject, Group, QuestionType, Question, Student, Choice, Assignment, Response
from dotenv import load_dotenv
import random
import string

def generate_student_code(length=6):
    # Kombinerar små bokstäver och siffror
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

db.init_app(app)

@app.cli.command("create-db")
def create_db():
    """Skapar databasen och tabellerna genom att köra "flask create-db" i terminalen."""
    with app.app_context():
        db.create_all()
        print("Databasen är skapad!")

@app.route('/')
def hello():
    return render_template("index.html")

@app.route("/admin/add_group", methods=["GET", "POST"])
def add_group():
    if request.method == "POST":
        group_name = request.form.get("name")
        if not group_name:
            return "Gruppnamn saknas!", 400
        new_group = Group(name=group_name)
        if group_name:
            new_group = Group(name=group_name)          
            try:
                db.session.add(new_group)
                db.session.commit()
                flash(f'Gruppen "{group_name}" har skapats!', 'success')
                return redirect(url_for('add_students'))
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
        flash(f"Klart! {added_count} elever skapades.", "success")
        if errors > 0:
            flash(f"{errors} elever kunde inte läggas till (kanske dubbletter).", "warning")        
        return redirect(url_for('view_group', group_id=group_id))
    groups = db.session.execute(db.select(Group)).scalars().all()
    return render_template("add_students.html", groups=groups)

@app.route('/admin/view_group/<int:group_id>')
def view_group(group_id):
    # Hämta gruppen, eller kasta en 404-sida om den inte finns
    group_query = select(Group).where(Group.id == group_id)
    group = db.session.execute(group_query).scalar_one_or_none()
    # Här hämtar vi eleverna. Om du har definierat en relation i din modell 
    # (t.ex. students: Mapped[List["Student"]] = relationship(back_populates="group"))
    # så kan du bara använda group.students i din template.
    return render_template('view_group.html', group=group)

@app.route("/admin/add_student", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        # Hämta data från formuläret
        name = request.form.get("name")
        login_code = request.form.get("login_code")
        group_id = request.form.get("group_id")

        # Skapa ett nytt student-objekt (Modern syntax)
        new_student = Student(
            name=name,
            login_code=login_code,
            group_id=int(group_id)
        )

        try:
            db.session.add(new_student)
            db.session.commit()
            return f"Studenten {name} har lagts till!"
        except Exception as e:
            db.session.rollback() # Om något går fel (t.ex. dubblett av login_code)
            return f"Ett fel uppstod: {e}"

    # Om det är GET: hämta alla grupper så vi kan välja en i en dropdown
    groups = db.session.execute(db.select(Group)).scalars().all()
    return render_template("add_student.html", groups=groups)

@app.route("/index")
def index():

   if "student_id" not in session:
       return redirect("/login")

   student = Student.query.get(session["student_id"])

   assignments = Assignment.query.filter(
       Assignment.class_id == student.class_id,
       Assignment.start_time < datetime.now(),
       Assignment.end_time > datetime.now()
   ).all()

   return render_template(
       "dashboard.html",
       student=student,
       assignments=assignments
   )

@app.route("/login", methods=["GET", "POST"])
def login():
   if request.method == "POST":
       code = request.form["code"]
       student = Student.query.filter_by(
           login_code=code
       ).first()
       if student:
           session["student_id"] = student.id
           return render_template("dashboard.html", student=student)
   return render_template("login.html")

@app.route("/assignment/<int:id>", methods=["GET", "POST"])
def assignment(id):
   if "student_id" not in session:
       return redirect("/login")
   assignment = Assignment.query.get(id)
   if request.method == "POST":
       student_id = session["student_id"]
       ip = request.remote_addr
       device = request.headers.get("User-Agent")
       response = Response(
           student_id=student_id,
           assignment_id=id,
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
       "assignment.html",
       assignment=assignment,
       choices=choices
   )

if __name__ == '__main__':
    app.run(debug=True)