from flask import Blueprint
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, g, abort
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.extensions import db
from app.models import Template, Assignment, AssignmentType, Student, Group, Team, Response, ResponseStatus, ResponseType, ResponseSource
from app.services.utils import utc_now, local_to_utc, utcify, SWEDEN_TZ

assignments_bp = Blueprint(
    "assignments", 
    __name__,
    url_prefix="/assignments"
)

## Hjälpfunktioner
def assignment_status(assignment):
    now = utc_now()
    start_time = utcify(assignment.start_time)
    end_time = utcify(assignment.end_time)
    if start_time is None:
        return "Förberedd"
    if now < start_time:
        return "Förberedd"
    if end_time is not None and now > end_time:
        return "Avslutad"
    return "Pågående"

def update_assignment_response_status(student_id):
    now = utc_now()
    responses = db.session.scalars(
        select(Response)
        .join(Response.assignment)
        .where(
            Response.student_id == student_id,
            Response.response_type == ResponseType.ASSIGNMENT,
            Response.status == ResponseStatus.PREPARED,
            Assignment.start_time.is_not(None),
            Assignment.start_time <= now,
            Assignment.end_time.is_(None) |
            (Assignment.end_time > now),
        )
    ).all()

    changed = False

    for response in responses:
        response.status = ResponseStatus.OPEN
        changed = True

    if changed:
        db.session.commit()

# Routes
@assignments_bp.get("/manage")
def manage():
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    template_id = request.args.get("template_id", type=int)
    query = (
        select(Assignment)
        .options(
            selectinload(Assignment.template),
        )
        .order_by(
            Assignment.start_time.desc()
        )
    )
    if search:
        query = query.join(
            Assignment.template
        ).where(
            Template.title.ilike(
                f"%{search}%"
            )
        )
    if template_id:
        query = query.where(
            Assignment.template_id == template_id
        )
    assignments = db.session.scalars(query).all()
    # Filtrera status efter att objekten hämtats.
    if status:
        assignments = [
            assignment 
            for assignment in assignments 
            if assignment_status(assignment) == status]
    templates = db.session.scalars(
        select(Template)
        .order_by(Template.title)
    ).all()
    if request.headers.get("HX-Request"):
        return render_template(
            "assignments/_assignments_table.html",
            assignments=assignments,
            assignment_status=assignment_status,
            sweden_tz=SWEDEN_TZ,
        )
    return render_template(
        "assignments/manage.html",
        assignments=assignments,
        templates=templates,
        search=search,
        status=status,
        template_id=template_id,
        assignment_status=assignment_status,
        sweden_tz=SWEDEN_TZ,
    )

@assignments_bp.get("/new")
def new():
    # En elev från studentsidan:
    single_student_id = request.args.get("student_id", type=int)
    # Flera elever från studentsidans tabell:
    student_ids = request.args.getlist("student_ids", type=int)
    if single_student_id is not None:
        student_ids.append(single_student_id)
    templates = db.session.scalars(
        select(Template).order_by(Template.title)
    ).all()
    students = db.session.scalars(
        select(Student)
        .where(Student.is_active.is_(True))
        .order_by(Student.name)
    ).all()
    groups = db.session.scalars(
        select(Group)
        .where(Group.is_active.is_(True))
        .order_by(Group.name)
    ).all()
    teams = db.session.scalars(
        select(Team).order_by(Team.name)
    ).all()
    selected_student_ids = {
        student.id
        for student in students
        if student.id in student_ids
    }
    selected_students = [
        student
        for student in students
        if student.id in selected_student_ids
    ]
    selected_student = (
        selected_students[0]
        if len(selected_students) == 1
        else None
    )
    return render_template(
        "assignments/new.html",
        assignment=None,
        templates=templates,
        students=students,
        groups=groups,
        teams=teams,
        assignment_types=AssignmentType,
        selected_student=selected_student,
        selected_students=selected_students,
        selected_student_ids=selected_student_ids,
        sweden_tz=SWEDEN_TZ,
    )

@assignments_bp.get("/edit/<int:assignment_id>")
def edit(assignment_id):
    assignment = db.session.get(
        Assignment,
        assignment_id,
    )
    if assignment is None:
        abort(404)
    templates = db.session.scalars(
        select(Template)
        .order_by(Template.title)
    ).all()
    students = db.session.scalars(
        select(Student)
        .where(Student.is_active.is_(True))
        .order_by(Student.name)
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
    return render_template(
        "assignments/edit.html",
        assignment=assignment,
        templates=templates,
         assignment_types=AssignmentType,
        students=students,
        groups=groups,
        teams=teams,
        sweden_tz=SWEDEN_TZ,
        assignment_status=assignment_status,
    )

@assignments_bp.post("/new")
def create():
    template_id = request.form.get("template_id", type=int)
    start_time_text = request.form.get("start_time", "").strip()
    end_time_text = request.form.get("end_time", "").strip()
    student_ids = request.form.getlist("student_ids")
    label = request.form.get("label", "").strip() or None
    assignment_type_name = request.form.get("assignment_type", "").strip()
    try:
        assignment_type = AssignmentType[assignment_type_name]
    except KeyError:
        flash(
            "Ogiltig uppgiftstyp.",
            "warning",
        )
        return redirect(url_for("assignments.new"))
    # Kontrollera mall
    template = db.session.get(
        Template,
        template_id,
    )
    if template is None:
        flash(
            "Du måste välja en giltig mall.",
            "warning",
        )
        return redirect(
            url_for("assignments.new")
        )
    # Läs starttid
    if start_time_text:
        try:
            start_time = local_to_utc(
                datetime.fromisoformat(start_time_text)
            )
        except ValueError:
            flash(
                "Ogiltigt startdatum.",
                "warning",
            )
            return redirect(
                url_for("assignments.new")
            )
    else:
        start_time = None
    # Läs sluttid
    if end_time_text:
        try:
            end_time = local_to_utc(
                datetime.fromisoformat(
                    end_time_text
                )
            )
        except ValueError:
            flash(
                "Ogiltigt slutdatum.",
                "warning",
            )
            return redirect(
                url_for("assignments.new")
            )
    else:
        end_time = None
    # Kontrollera tider
    if (end_time is not None and end_time <= start_time):
        flash(
            "Sluttiden måste vara senare än starttiden.",
            "warning",
        )
        return redirect(
            url_for("assignments.new")
        )
    # Kontrollera elever
    students = []
    for student_id in student_ids:
        try:
            student_id = int(student_id)
        except ValueError:
            continue
        student = db.session.get(
            Student,
            student_id,
        )
        if (
            student is not None
            and student.is_active
        ):
            students.append(student)
    if not students:
        flash(
            "Du måste välja minst en elev.",
            "warning",
        )
        return redirect(
            url_for("assignments.new")
        )
    # Skapa assignment
    assignment = Assignment(
        author_id=g.user.id,
        template_id=template.id,
        assignment_type=assignment_type,
        label=label,
        start_time=start_time,
        end_time=end_time,
    )

    db.session.add(assignment)

    response_status = (
        ResponseStatus.OPEN
        if start_time is not None and start_time <= utc_now()
        else ResponseStatus.PREPARED
    )

    for student in students:
        response = Response(
            student=student,
            author_id=g.user.id,
            response_type=ResponseType.ASSIGNMENT,
            source=ResponseSource.ASSIGNMENT,
            status=response_status,
            assignment=assignment,
        )
        assignment.responses.append(response)

    db.session.commit()
    flash(
        "Uppgiften skapades.",
        "success",
    )
    return redirect(url_for("assignments.manage"))

@assignments_bp.post("/edit/<int:assignment_id>")
def update(assignment_id):
    assignment = db.session.get(Assignment, assignment_id)
    if assignment is None:
        abort(404)
    assignment_type_name = request.form.get("assignment_type", "").strip()
    try:
        assignment_type = AssignmentType[assignment_type_name]
    except KeyError:
            flash("Ogiltig uppgiftstyp.", "warning")
            return redirect(
                url_for(
                "assignments.edit",
                assignment_id=assignment.id,
            )
        )
    label = request.form.get("label", "").strip() or None
    start_time_text = request.form.get("start_time","").strip()
    end_time_text = request.form.get("end_time", "").strip()
    student_ids = request.form.getlist("student_ids")
    # Läs starttid
    try:
        start_time = local_to_utc(
            datetime.fromisoformat(
                start_time_text
            )
        )
    except ValueError:
        flash(
            "Ogiltigt startdatum.",
            "warning",
        )
        return redirect(
            url_for(
                "assignments.edit",
                assignment_id=assignment.id,
            )
        )
    # Läs sluttid
    if end_time_text:
        try:
            end_time = local_to_utc(
                datetime.fromisoformat(
                    end_time_text
                )
            )
        except ValueError:
            flash(
                "Ogiltigt slutdatum.",
                "warning",
            )
            return redirect(
                url_for(
                    "assignments.edit",
                    assignment_id=assignment.id,
                )
            )
    else:
        end_time = None
    # Kontrollera tider
    if (end_time is not None and end_time <= start_time):
        flash(
            "Sluttiden måste vara senare än starttiden.",
            "warning",
        )
        return redirect(
            url_for(
                "assignments.edit",
                assignment_id=assignment.id,
            )
        )
    # Hämta elever
    students = []
    for student_id in student_ids:
        try:
            student_id = int(student_id)
        except ValueError:
            continue
        student = db.session.get(
            Student,
            student_id,
        )
        if (student is not None and student.is_active):
            students.append(student)
    if not students:
        flash(
            "Du måste välja minst en elev.",
            "warning",
        )
        return redirect(
            url_for(
                "assignments.edit",
                assignment_id=assignment.id,
                label=label
            )
        )
    # Uppdatera
    assignment.start_time = start_time
    assignment.end_time = end_time
    assignment.assignment_type = assignment_type
    db.session.commit()
    flash(
        "Uppgiften ändrades.",
        "success",
    )
    return redirect(
        url_for(
            "assignments.edit",
            assignment_id=assignment.id,
            label=label,
        )
    )

@assignments_bp.post("/start/<int:assignment_id>")
def start(assignment_id):
    assignment = db.session.get(Assignment, assignment_id)
    if assignment is None:
        abort(404)
    duration = request.form.get("duration", type=int)
    allowed_durations = {1, 3, 5, 10, 30}
    if duration not in allowed_durations:
        flash(
            "Ogiltig tidslängd.",
            "warning",
        )
        return redirect(
            url_for(
                "assignments.edit",
                assignment_id=assignment.id,
            )
        )
    start_time = utc_now()
    end_time = start_time + timedelta(
        minutes=duration
    )
    assignment.start_time = start_time
    assignment.end_time = end_time
    db.session.commit()
    flash(
        f"Uppgiften startades och är öppen i {duration} minuter.",
        "success",
    )
    return redirect(
        url_for(
            "assignments.edit",
            assignment_id=assignment.id,
        )
    )