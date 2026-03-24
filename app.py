import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from models import db, Student, Assignment, Response, Choice, Class
from dotenv import load_dotenv

# Laddar inställningar från en fil som heter .env (endast lokalt)
load_dotenv()

app = Flask(__name__)

# SMART DATABASE URL:
# 1. Kolla om 'DATABASE_URL' finns (sätts av t.ex. Render, Heroku eller DigitalOcean)
# 2. Om inte, använd lokal sqlite-fil
default_db = 'sqlite:///mina_elever.db'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', default_db)
app.config['SECRET_KEY'] = 'en-valfri-hemlig-text-sträng'

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def hello():
    return render_template("index.html")

@app.route("/admin/add_class", methods=["GET", "POST"])
def add_class():
    if request.method == "POST":
        class_name = request.form.get("name")
        
        if class_name:
            # Skapa det nya klass-objektet
            new_class = Class(name=class_name)
            
            try:
                db.session.add(new_class)
                db.session.commit()
                return redirect("/admin/add_student") # Gå direkt till att lägga till elever!
            except Exception as e:
                db.session.rollback()
                return f"Kunde inte skapa klassen: {e}"              
    return render_template("add_class.html")

@app.route("/admin/add_student", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        # Hämta data från formuläret
        name = request.form.get("name")
        login_code = request.form.get("login_code")
        class_id = request.form.get("class_id")

        # Skapa ett nytt student-objekt (Modern syntax)
        new_student = Student(
            name=name,
            login_code=login_code,
            class_id=int(class_id)
        )

        try:
            db.session.add(new_student)
            db.session.commit()
            return f"Studenten {name} har lagts till!"
        except Exception as e:
            db.session.rollback() # Om något går fel (t.ex. dubblett av login_code)
            return f"Ett fel uppstod: {e}"

    # Om det är GET: hämta alla klasser så vi kan välja en i en dropdown
    classes = db.session.execute(db.select(Class)).scalars().all()
    return render_template("add_student.html", classes=classes)

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