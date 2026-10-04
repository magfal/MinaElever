from flask import Blueprint
from flask import render_template, request, redirect, url_for, flash, jsonify, g, make_response, abort
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Response, Student, Group, Team
from app.services.htmx import toast
from app.services.auth import logout_everywhere, generate_code, teacher_required

students_bp = Blueprint(
    "students",
    __name__,
    url_prefix="/students"
)

@students_bp.get("/manage")
@teacher_required
def manage():
    search = request.args.get("search", "").strip()
    group_id = request.args.get("group_id", type=int)
    team_id = request.args.get("team_id", type=int)
    # Aktiva elever visas som standard
    include_inactive = request.args.get("include_inactive") == "true"
    query = db.select(Student)
    if not include_inactive:
        query = query.where(Student.is_active.is_(True))
    else:
        query = query.where(Student.is_active.is_(False))
    if search:
        query = query.where(
            Student.name.ilike(f"%{search}%")
        )
    if group_id:
        query = query.where(
            Student.group_id == group_id
        )
    if team_id:
        query = query.join(Student.teams).where(
            Team.id == team_id
        )
    students = db.session.scalars(
        query.order_by(Student.name)
    ).all()
    if not include_inactive:
        groups = db.session.scalars(
            db.select(Group)
            .where(Group.is_active.is_(True))
            .order_by(Group.name)
        ).all()
    else:
        groups = db.session.scalars(
            db.select(Group)
            .order_by(Group.name)
        ).all()
    teams = db.session.scalars(
        db.select(Team)
        .order_by(Team.name)
    ).all()
    # HTMX uppdaterar bara tabellen
    if request.headers.get("HX-Request"):
        return render_template(
            "students/_students_table.html",
            students=students
        )
    # Första sidladdningen
    return render_template(
        "students/manage.html",
        students=students,
        groups=groups,
        teams=teams,
        selected_group_id=group_id,
        selected_team_id=team_id
    )

@students_bp.get("/new_code")
@teacher_required
def generate_student_code_api():
    return jsonify({
        "code": generate_code()
    })

@students_bp.get("/add")
@teacher_required
def add():
    groups = db.session.scalars(
        select(Group).order_by(Group.name)
    ).all()
    return render_template(
        "/students/add.html",
        groups=groups
    )

@students_bp.post("/add")
@teacher_required
def add_update():
    student_list = request.form.get("student_list", "")
    group_id = request.form.get("group_id")
    if not student_list.strip():
        flash("Elevlistan var tom!", "error")
        return redirect(url_for("students.add"))
    group = db.session.get(Group, group_id)
    if not group:
        flash("Ingen giltig grupp vald.", "error")
        return redirect(url_for("students.add"))
    student_names = [
        name.strip()
        for name in student_list.split("\n")
        if name.strip()]
    doubles = []
    existing = {
        name
        for (name,) in db.session.execute(
            select(Student.name)
            .where(Student.group_id == group_id))}
    for name in student_names:
        if name in existing:
            doubles.append(name)
            continue
        db.session.add(
            Student(
                name=name,
                login_code=generate_code(),
                group_id=group_id,
                type="student",
                is_active=True,
            )
        )
    db.session.commit()
    students_added = len(student_names) - len(doubles)
    if students_added == 1:
        sing_plur = "elev"
    else:
        sing_plur = "elever"
    message = f"Klass {group.name} utökades med {students_added} {sing_plur}."
    status = "success"
    if students_added < len(student_names):
        message += f" {', '.join(doubles)} finns redan."
        status = "warning"
    flash(message, status)
    return redirect(url_for("students.manage"))
    
@students_bp.get("/edit/<int:student_id>")
@teacher_required
def new_student_modal(student_id):
    student = db.session.get(Student, student_id)
    if student is None:
        abort(404)
    groups = db.session.scalars(
        select(Group).order_by(Group.name)
        ).all()
    teams = db.session.scalars(
        select(Team).order_by(Team.name)
        ).all()
    return render_template( 
        "students/_student_form.html",
        student=student,
        groups=groups,
        teams=teams,
        action=url_for("students.update_student", student_id=student.id),
        title="Ändra elev"
    )

@students_bp.post("/edit/<int:student_id>")
@teacher_required
def edit_student_modal(student_id):
    student = db.session.get(Student, student_id)
    if student is None:
        abort(404)
    team_value = request.form.get("team")
    team_id = request.form.get("team_id", type=int)
    action = request.form.get("action")
    team = None
    if team_id:
        team = db.session.get(Team, team_id)
    if team_value:
        if team_value.isdigit():
            team = db.session.get(Team, int(team_value))
        else:
            if "," in team_value:
                name, description = team_value.split(",", 1)
            else:
                name, description = team_value.strip(), ""
            team = db.session.scalar(
                select(Team)
                .where(Team.name == team_value.strip())
            )
            if team is None:
                team = Team(
                    author_id=g.user.id,
                    name=name,
                    description=description
                )
                db.session.add(team)
                db.session.flush()
    if action in ["add_team", "remove_team"]:
        if team is None:
            abort(404)
        if action == "add_team":
            if team not in student.teams:
                student.teams.append(team)
        elif action == "remove_team":
            if team in student.teams:
                student.teams.remove(team)
        db.session.commit()
    elif action == "new_code":
        student.login_code = generate_code()
        db.session.commit()
    groups = db.session.scalars(
        select(Group).order_by(Group.name)
    ).all()
    teams = db.session.scalars(
        select(Team).order_by(Team.name)
    ).all()
    return render_template(
        "students/_student_form.html",
        student=student,
        teams=teams,
        groups=groups,
        action=url_for("students.update_student", student_id=student.id),
        title="Ändra elev"
    )

@students_bp.post("/update/<int:student_id>")
@teacher_required
def update_student(student_id):
    name = request.form.get("name", "").strip()
    group_id = request.form.get("group_id", type=int)
    login_code = request.form.get("login_code")
    is_active = request.form.get("is_active") is not None
    if not name or not login_code:
        response = make_response("")
        toast(response, "Fält får inte var tomt", "warning", reswap="none")
        return response
    student = db.session.get(Student, student_id)
    if not student:
        response = make_response("")
        toast(response,f"Eleven finns inte i databasen.", "warning")
        return response
    old_login_code = student.login_code
    old_is_active = student.is_active
    student.name = name
    student.group_id = group_id
    student.login_code = login_code
    student.is_active = is_active
    should_logout = (
        old_login_code != login_code or
        (old_is_active and not is_active)
        )
    if should_logout:
        logout_everywhere(student.id)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        response = make_response("")
        toast(response, f"IntegrityError.", "warning", reswap="none")
        return response
    flash(f"{name} har uppdaterats", "success")
    response = make_response("", 204)
    response.headers["HX-Redirect"] = url_for("students.manage")
    return response

@students_bp.get("/edit_students")
@teacher_required
def edit_students():
    student_ids = request.args.getlist("students_ids")
    students = db.session.scalars(
        select(Student)
        .where(Student.id.in_(student_ids))
    ).all()
    groups = db.session.scalars(
        select(Group)
        .where(Group.is_active.is_(True))
        .order_by(Group.name)
    ).all()
    teams = db.session.scalars(
        select(Team)
        .order_by(Team.name)
    ).all()
    current_teams = sorted(
        {team for student in students for team in student.teams},
        key=lambda t: t.name)
    return render_template(
        "students/_students_form.html",
        students=students,
        groups=groups,
        teams=teams,
        current_teams=current_teams,
        action=url_for("students.update_students")
    )

@students_bp.post("/edit_students")
@teacher_required
def edit_students_action():
    action = request.form.get("action")
    team_id = request.form.get("team_id", type=int)
    team_value = request.form.get("team")
    student_ids = request.form.getlist("student_ids")
    students = db.session.scalars(
        select(Student)
        .where(Student.id.in_(student_ids))
    ).all()
    team = None
    if team_id:
        team = db.session.get(Team, team_id)
    if team_value:
        if team_value.isdigit():
            team = db.session.get(Team, int(team_value))
        else:
            if "," in team_value:
                name, description = team_value.split(",", 1)
            else:
                name, description = team_value.strip(), ""
            team = db.session.scalar(
                select(Team)
                .where(Team.name == team_value.strip())
            )
            if team is None:
                team = Team(
                    author_id=g.user.id,
                    name=name,
                    description=description
                )
                db.session.add(team)
                db.session.flush()
    if action in ["add_team", "remove_team"]:
        if team is None:
            abort(404)
        for student in students:
            if action == "add_team":
                if team not in student.teams:
                    student.teams.append(team)
            elif action == "remove_team":
                if team in student.teams:
                    student.teams.remove(team)
        db.session.commit()
        current_team_ids = set()
        for student in students:
            for team in student.teams:
                current_team_ids.add(team.id)
        current_teams = db.session.scalars(
            select(Team)
            .where(Team.id.in_(current_team_ids))
            .order_by(Team.name)
        ).all() if current_team_ids else []

        groups = db.session.scalars(
            select(Group)
            .order_by(Group.name)
        ).all()

        teams = db.session.scalars(
            select(Team)
            .order_by(Team.name)
        ).all()
        return render_template(
            "students/_students_form.html",
            students=students,
            groups=groups,
            teams=teams,
            current_teams=current_teams,
            action=url_for("students.update_students")
        )


@students_bp.post("/update_students")
@teacher_required
def update_students():
    student_ids = request.form.getlist("student_ids")
    students = db.session.scalars(
        select(Student)
        .where(Student.id.in_(student_ids))
    ).all()
    if not students:
        response = make_response("")
        toast(response,"Inga elever valda.", "warning", reswap="none")
        return response
    group_id = request.form.get("group_id", type=int)  
    new_code = (request.form.get("new_code") is not None)
    active_action = request.form.get("active_action")
    try:
        for student in students:
            old_login_code = student.login_code
            old_is_active = student.is_active
            if group_id:
                student.group_id = group_id
            if new_code:
                student.login_code = generate_code()
            if active_action == "activate":
                student.is_active = True
            elif active_action == "deactivate":
                student.is_active = False
            should_logout = (old_login_code != student.login_code
                             or (old_is_active and not student.is_active))
            if should_logout:
                logout_everywhere(student.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        response = make_response("")
        toast(response, "Ett fel uppstod när eleverna skulle uppdateras.", "warning",reswap="none")
        return response
    response = make_response("", 204)
    response.headers["HX-Redirect"] = url_for("students.manage")
    return response


@students_bp.route("/create_response", methods=["POST"])
@teacher_required
def create_admin_response():
    student_ids = request.form.getlist("student_ids")
    response_type = request.form.get("type")
    if not student_ids:
        flash("Du måste välja minst en elev", "warning")
        return redirect(url_for("students.manage"))
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

@students_bp.route("/timeline/<int:student_id>")
@teacher_required
def student_timeline(student_id):
    student = db.session.get(Student, student_id)
    if student is None:
        abort(404)
    responses = db.session.scalars(
        select(Response).
        where(Response.student_id == student_id).
        order_by(Response.submitted_at.desc())
        ).all()
    return render_template(
        "students/timeline.html",
        student=student,
        responses=responses
        )