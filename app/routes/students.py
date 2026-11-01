from flask import (Blueprint, abort, flash, g, jsonify, make_response, redirect, render_template, request, url_for)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Response, Student, Group, Team
from app.services.auth import (generate_code, logout_everywhere, teacher_required)
from app.services.htmx import toast

students_bp = Blueprint(
    "students",
    __name__,
    url_prefix="/students"
)

# ---------------------------------------------------------
# Hjälpfunktioner
# ---------------------------------------------------------
def get_teacher_groups():
    """Hämtar grupper som läraren har tillgång till."""
    return db.session.scalars(
        select(Group)
        .where(Group.teachers.any(id=g.user.id))
        .order_by(Group.name)
    ).all()

def get_teacher_teams():
    """Hämtar team som läraren själv har skapat."""
    return db.session.scalars(
        select(Team)
        .where(Team.author_id == g.user.id)
        .order_by(Team.name)
    ).all()

def get_selected_students(student_ids):
    """Hämtar valda elever som läraren har tillgång till."""
    if not all(student_id.isdigit() for student_id in student_ids):
        abort(400)
    valid_ids = {int(student_id) for student_id in student_ids}
    if not valid_ids:
        return []
    students = db.session.scalars(
        select(Student)
        .where(
            Student.id.in_(valid_ids),
            Student.group.has(Group.teachers.any(id=g.user.id))
        )
        .order_by(Student.name)
    ).all()
    if len(students) != len(valid_ids):
        abort(404)
    return students

def update_student_login_code(student, new_code):
    """Byter inloggningskod och loggar ut elevens aktiva sessioner."""
    if student.login_code != new_code:
        student.login_code = new_code
        logout_everywhere(student.id)

def validate_group(group_id):
    """Kontrollerar att gruppen tillhör en grupp läraren har tillgång till."""
    if not group_id:
        return None
    group = db.session.scalar(
        select(Group)
        .where(
            Group.id == group_id,
            Group.teachers.any(id=g.user.id)
        )
    )
    if group is None:
        abort(404)
    return group

def validate_teams(team_ids):
    """Hämtar endast team som läraren själv äger."""
    valid_ids = {
        int(team_id)
        for team_id in team_ids
        if team_id.isdigit()
    }
    if not valid_ids:
        return []
    return db.session.scalars(
        select(Team)
        .where(
            Team.id.in_(valid_ids),
            Team.author_id == g.user.id
        )
    ).all()

# ---------------------------------------------------------
# Elevlista
# ---------------------------------------------------------
@students_bp.get("/manage")
@teacher_required
def manage():
    search = request.args.get("search", "").strip()
    group_id = request.args.get("group_id", type=int)
    team_id = request.args.get("team_id", type=int)
    show_archived = request.args.get("archived") == "1"
    query = (
        select(Student)
        .join(Student.group)
        .where(Group.teachers.any(id=g.user.id))
        )
    if show_archived:
        query = query.where(Student.is_active.is_(False))
    else:
        query = query.where(Student.is_active.is_(True))
    if search:
        query = query.where(
            Student.name.ilike(f"%{search}%")
        )
    if group_id:
        query = query.where(Student.group_id == group_id)
    if team_id:
        query = (
            query
            .join(Student.teams)
            .where(Team.id == team_id)
        )
    students = db.session.scalars(
        query
        .distinct()
        .order_by(Student.name)
    ).all()
    groups = get_teacher_groups()
    teams = get_teacher_teams()
    if request.headers.get("HX-Request"):
        return render_template(
            "students/_students_table.html",
            students=students
        )
    return render_template(
        "students/manage.html",
        students=students,
        groups=groups,
        teams=teams,
        selected_group_id=group_id,
        selected_team_id=team_id,
        archived=show_archived
    )

# ---------------------------------------------------------
# Generera inloggningskod
# ---------------------------------------------------------
@students_bp.get("/new_code")
@teacher_required
def generate_student_code_api():
    return jsonify({
        "code": generate_code()
    })

# ---------------------------------------------------------
# Lägg till elever
# ---------------------------------------------------------
@students_bp.route("/add", methods=["GET", "POST"])
@teacher_required
def add():
    if request.method == "GET":
        return render_template(
            "students/add.html",
            groups=get_teacher_groups()
        )
    student_list = request.form.get("student_list", "")
    group_id = request.form.get("group_id", type=int)
    if not student_list.strip():
        flash("Elevlistan var tom!", "error")
        return redirect(url_for("students.add"))
    group = validate_group(group_id)
    if group is None:
        flash("Ingen giltig grupp vald.", "error")
        return redirect(url_for("students.add"))
    student_names = [
        name.strip()
        for name in student_list.splitlines()
        if name.strip()
    ]
    existing = {
        name
        for (name,) in db.session.execute(
            select(Student.name)
            .where(Student.group_id == group.id)
        )
    }
    added = 0
    duplicates = []
    for name in student_names:
        if name in existing:
            duplicates.append(name)
            continue
        db.session.add(
            Student(
                name=name,
                login_code=generate_code(),
                group_id=group.id,
                type="student",
                is_active=True,
            )
        )
        added += 1
        existing.add(name)
    db.session.commit()
    if added == 1:
        message = f"Klass {group.name} utökades med 1 elev."
    else:
        message = f"Klass {group.name} utökades med {added} elever."
    status = "success"
    if duplicates:
        message += f" {', '.join(duplicates)} finns redan."
        status = "warning"
    flash(message, status)
    return redirect(url_for("students.manage"))

# ---------------------------------------------------------
# Redigera en eller flera elever – gemensam formulärroute
# ---------------------------------------------------------
@students_bp.route("/edit-students", methods=["GET", "POST"])
@teacher_required
def edit_students_modal():
    # -----------------------------------------------------
    # Hämta valda elever
    # -----------------------------------------------------
    if request.method == "GET":
        student_ids = request.args.getlist("student_ids")
    else:
        student_ids = request.form.getlist("student_ids")
    students = get_selected_students(student_ids)
    if not students:
        abort(400)
    # -----------------------------------------------------
    # GET – visa rätt formulär
    # -----------------------------------------------------
    if request.method == "GET":
        if len(students) == 1:
            return render_template(
                "students/_student_form.html",
                student=students[0],
                groups=get_teacher_groups(),
                teams=get_teacher_teams(),
                action=url_for("students.edit_students_modal"),
                title="Ändra elev"
            )
        common_teams = set(students[0].teams)
        for student in students[1:]:
            common_teams.intersection_update(student.teams)
        common_teams = sorted(
            common_teams,
            key=lambda team: team.name.lower()
        )
        return render_template(
            "students/_students_form.html",
            students=students,
            groups=get_teacher_groups(),
            teams=get_teacher_teams(),
            common_teams=common_teams,
            action=url_for("students.edit_students_modal")
        )
    # -----------------------------------------------------
    # POST – spara ändringar
    # -----------------------------------------------------
    single_student = len(students) == 1
    try:
        # -------------------------------------------------
        # Namn – endast vid redigering av en elev
        # -------------------------------------------------
        if single_student and "name" in request.form:
            name = request.form.get("name", "").strip()
            if not name:
                response = make_response("")
                toast(
                    response,
                    "Elevens namn får inte vara tomt.",
                    "warning",
                    reswap="none"
                )
                return response
            students[0].name = name
        # -------------------------------------------------
        # Klass
        # -------------------------------------------------
        group_id = request.form.get("group_id", type=int)
        if group_id:
            group = validate_group(group_id)

            for student in students:
                student.group_id = group.id
        # -------------------------------------------------
        # Team
        # -------------------------------------------------
        selected_teams = validate_teams(
            request.form.getlist("team_ids")
        )
        if single_student:
            # För en elev ersätts hela teamlistan.
            student = students[0]
            selected_team_ids = {team.id for team in selected_teams}

            for team in list(student.teams):
                if team.author_id == g.user.id and team.id not in selected_team_ids:
                    student.teams.remove(team)

            for team in selected_teams:
                if team not in student.teams:
                    student.teams.append(team)
        else:
            # För flera elever ändras endast skillnaden
            # mellan gemensamma team före och efter redigering.
            original_team_ids = {
                int(team_id)
                for team_id in request.form.getlist("original_team_ids")
                if team_id.isdigit()
            }
            selected_team_ids = {
                team.id
                for team in selected_teams
            }
            removed_team_ids = (
                original_team_ids - selected_team_ids
            )
            added_team_ids = (
                selected_team_ids - original_team_ids
            )
            teams_by_id = {
                team.id: team
                for team in selected_teams
            }
            for team_id in removed_team_ids:
                team = db.session.scalar(
                    select(Team)
                    .where(
                        Team.id == team_id,
                        Team.author_id == g.user.id
                    )
                )
                if team is None:
                    continue
                for student in students:
                    if team in student.teams:
                        student.teams.remove(team)
            for team_id in added_team_ids:
                team = teams_by_id.get(team_id)
                if team is None:
                    continue
                for student in students:
                    if team not in student.teams:
                        student.teams.append(team)
        # -------------------------------------------------
        # Inloggningskoder
        # -------------------------------------------------
        if request.form.get("new_codes"):
            for student in students:
                update_student_login_code(
                    student,
                    generate_code()
                )
        elif single_student:
            # En elev kan även få en manuellt angiven kod.
            login_code = request.form.get("login_code","").strip()
            if login_code:
                update_student_login_code(
                    students[0],
                    login_code
                )
        # -------------------------------------------------
        # Aktiv / arkiverad
        # -------------------------------------------------
        student_status = request.form.get("student_status")
        if student_status == "active":
            for student in students:
                student.is_active = True
        elif student_status == "archived":
            for student in students:
                if student.is_active:
                    student.is_active = False
                    logout_everywhere(student.id)
        # -------------------------------------------------
        # Spara
        # -------------------------------------------------
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        response = make_response("")
        toast(
            response,
            "Ändringen kunde inte sparas.",
            "warning",
            reswap="none"
        )
        return response
    if single_student:
        message = f"{students[0].name} har uppdaterats."
    else:
        message = f"{len(students)} elever har uppdaterats."
    flash(message, "success")
    response = make_response("", 204)
    response.headers["HX-Redirect"] = url_for("students.manage")
    return response

# ---------------------------------------------------------
# Skapa administrativt elevsvar
# ---------------------------------------------------------
@students_bp.post("/create_response")
@teacher_required
def create_admin_response():
    student_ids = request.form.getlist("student_ids")
    response_type = request.form.get("type")
    if not student_ids:
        flash("Du måste välja minst en elev", "warning")
        return redirect(url_for("students.manage"))
    students = get_selected_students(student_ids)
    return render_template(
        "admin/create_response.html",
        students=students,
        response_type=response_type
    )

# ---------------------------------------------------------
# Elevens tidslinje
# ---------------------------------------------------------
@students_bp.get("/timeline/<int:student_id>")
@teacher_required
def student_timeline(student_id):
    student = db.session.scalar(
        select(Student)
        .where(
            Student.id == student_id,
            Student.group.has(Group.teachers.any(id=g.user.id))
        )
    )
    if student is None:
        abort(404)
    responses = db.session.scalars(
        select(Response)
        .where(Response.student_id == student_id)
        .order_by(Response.submitted_at.desc())
    ).all()
    return render_template(
        "students/timeline.html",
        student=student,
        responses=responses
    )