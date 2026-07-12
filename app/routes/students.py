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

students_bp = Blueprint(
    "students",
    __name__,
    url_prefix="/students"
)       

@students_bp.route("/manage")
def manage_students():
    search = request.args.get("search", "")
    group_id = request.args.get("group_id", type=int)
    query = select(Student)
    if group_id:
        query = query.where(
            Student.group_id == group_id
        )
    if search:
        query = query.where(
            Student.name.ilike(f"%{search}%")
        )
    students = db.session.scalars(
        query.order_by(Student.name)
    ).all()
    groups = db.session.scalars(
        select(Group)
        .order_by(Group.name)
    ).all()
    return render_template(
        "admin/students.html",
        students=students,
        groups=groups,
        selected_group=group_id,
        search=search
    )

# UPDATE STUDENT
@students_bp.post("/admin/student/<int:student_id>/update")
def update_student(student_id):
    student = db.session.get(
        Student,
        student_id
    )
    if not student:
        flash(
            "Eleven hittades inte",
            "danger"
        )
        return redirect(url_for("students.manage_students"))
    student.name = request.form.get(
        "name"
    ).strip()
    student.group_id = request.form.get(
        "group_id",
        type=int
    )
    db.session.commit()
    flash(
        "Elev uppdaterad",
        "success"
    )
    return redirect(url_for("students.manage_students"))

# NEW LOGIN CODE
@students_bp.post("/admin/student/<int:student_id>/new_code")
def new_student_code(student_id):
    student = db.session.get(
        Student,
        student_id
    )
    student.access_code = generate_student_code()
    db.session.commit()
    flash(
        f"Ny kod skapad för {student.name}",
        "success"
    )
    return redirect(url_for("students.manage_students"))



@students_bp.route("/import", methods=["GET", "POST"])
def import_students():
    if request.method == "POST":
        raw_data = request.form.get("student_list", "")
        group_id = request.form.get("group_id")
        new_group_name = request.form.get("new_group_name", "").strip()
        if not raw_data.strip():
            flash("Elevlistan var tom!", "error")
            return redirect(url_for("students.import_students"))
        # 1. Hitta eller skapa grupp
        if new_group_name:
            # Kontrollera om gruppen redan finns
            group = db.session.scalar(
                select(Group).where(Group.name == new_group_name)
            )
            if not group:
                group = Group(name=new_group_name)
                db.session.add(group)
                db.session.flush()  # ger gruppen ett id
            group_id = group.id
        else:
            group = db.session.get(Group, group_id)
            if not group:
                flash("Ingen giltig grupp vald.", "error")
                return redirect(url_for("students.import_students"))
        # 2. Dela upp elevlistan
        student_names = [
            name.strip()
            for name in raw_data.split("\n")
            if name.strip()
        ]
        duplicate_count = 0
        added_students = []
        # 3. Skapa elever
        try:
            for name in student_names:
                # Kontrollera om eleven redan finns i gruppen
                existing_student = db.session.scalar(
                    select(Student)
                    .where(
                        Student.name == name,
                        Student.group_id == group_id
                    )
                )
                if existing_student:
                    duplicate_count += 1
                    continue
                new_student = Student(
                    name=name,
                    access_code=generate_student_code(),
                    group_id=group_id
                )
                db.session.add(new_student)
                added_students.append(name)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"Ett fel uppstod: {e}", "error")
            return redirect(url_for("students.import_students"))
        # 4. Feedback
        if duplicate_count:
            flash(
                f"{duplicate_count} elever fanns redan i gruppen.",
                "warning"
            )
        if added_students:
            flash(
                f", ".join(added_students) + f" har lagts till i gruppen {group.name}")
        return redirect(url_for("students.manage_students"))
    # GET - visa sidan
    groups = db.session.scalars(
        select(Group).order_by(Group.name)
    ).all()
    return render_template(
        "/admin/import_students.html",
        groups=groups
    )

@students_bp.route("/create_response")
def create_admin_response():

    student_ids = request.form.getlist("student_ids")
    response_type = request.form.get("type")


    if not student_ids:
        flash("Du måste välja minst en elev", "warning")
        return redirect(url_for("students"))


    students = (
        db.session.scalars(
            select(Student)
            .where(Student.id.in_(student_ids))
            .order_by(Student.name)
        ).all()
    )


    return render_template(
        "/admin/create_response.html",
        students=students,
        response_type=response_type
    )


# Show student view
@students_bp.route("/view/<int:student_id>")
def student_view(student_id):

    student = db.session.get(Student, student_id)

    if not student:
        abort(404)

    return render_template(
        "student/view.html",
        student=student
    )

# Visa elevresponser
@students_bp.route("/responses/<int:student_id>")
def admin_responses(student_id):

    student = db.session.get(Student, student_id)

    if not student:
        abort(404)

    return f"Progression för {student.name}"


