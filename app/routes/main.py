from flask import Blueprint, redirect, url_for, g
from app.models import Teacher, Student

main_bp = Blueprint("main", __name__)

@main_bp.get("/")
def index():
    if isinstance(g.user, Teacher):
        return redirect(url_for("students.manage"))
    if isinstance(g.user, Student):
        return redirect(url_for("student.index"))
    return redirect(url_for("auth.login_get"))