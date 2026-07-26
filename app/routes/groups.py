from flask import Blueprint
from flask import render_template, request, redirect, url_for, flash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Group, Team

groups_bp = Blueprint("groups", __name__, url_prefix="/groups")       

# /manage                           manage_group())
# /create_group                     create_group()
# /edit_group                       edit_group()
# /delete_group/<int:group_id>      delete_group(group_id)
# /create_team                      create_team()
# /edit_team                        edit_team()
# /delete_team/<int:group_id>       delete_team(team_id)

@groups_bp.route("/manage")
def manage_groups():
    groups = db.session.scalars(
        select(Group)
        .where(Group.is_active == True)
        .order_by(Group.name)
    ).all()
    archived_groups = db.session.scalars(
        select(Group)
        .where(Group.is_active == False)
        .order_by(Group.name)
    ).all()
    teams = db.session.scalars(
        select(Team)
        .order_by(Team.name)
    ).all()
    return render_template(
        "groups_manage.html",
        groups=groups,
        archived_groups=archived_groups,
        teams=teams
    )

@groups_bp.route("/create_group", methods=["POST"])
def create_group():
    name = request.form.get("name").strip()
    next_page = request.form.get("next")
    existing = db.session.scalar(
        select(Group).where(Group.name == name)
    )
    if existing:
        flash(
            f"En klass med namnet {name} finns redan.",
            "danger"
        )
        return redirect(
            url_for("groups.manage_groups")
        )
    new_group = Group(
        name=name
    )
    db.session.add(new_group)
    db.session.commit()
    flash(
        f"Klassen {name} skapades.",
        "success"
    )
    if next_page in ["groups.manage_groups","students.manage"]:
        return redirect(url_for(next_page))
    return redirect(url_for("groups.manage_groups"))

@groups_bp.route("/edit_group", methods=["POST"])
def edit_group():
    group_id = request.form.get("group_id")
    group = db.session.get(
        Group,
        group_id
    )
    if not group:
        flash(
            "Klassen hittades inte.",
            "danger"
        )
        return redirect(
            url_for("groups.manage_groups")
        )
    name = request.form.get("name").strip()
    next_page = request.form.get("next")
    # Kontrollera om namnet redan används av en annan klass
    existing = db.session.scalar(
        select(Group).where(
            Group.name == name,
            Group.id != group.id
        )
    )
    if existing:
        flash(
            f"En klass med namnet {name} finns redan.",
            "danger"
        )
        return redirect(
            url_for("groups.manage_groups")
        )
    group.name = name
    # Checkboxen heter archived
    group.is_active = not (
        "archived" in request.form
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(
            "Kunde inte uppdatera klassen eftersom namnet redan finns.",
            "danger"
        )
        return redirect(
            url_for("groups.manage_groups")
        )
    flash(
        f"Klassen {name} uppdaterades.",
        "success"
    )
    if next_page in ["groups.manage_groups","students.manage"]:
        return redirect(url_for(next_page))
    return redirect(url_for("groups.manage_groups"))

@groups_bp.route("/delete_group/<int:group_id>", methods=["POST"])
def delete_group(group_id):
    group = db.session.get(
        Group,
        group_id
    )
    if not group:
        flash(
            "Klassen hittades inte.",
            "danger"
        )
        return redirect(
            url_for("groups.manage_groups")
        )
    # Säkerhetskontroll
    if len(group.students) > 0:
        flash(
            "En klass med elever kan inte tas bort permanent.",
            "danger"
        )
        return redirect(
            url_for("groups.manage_groups")
        )
    db.session.delete(group)
    db.session.commit()
    flash(
        f"Klassen {group.name} togs bort permanent.",
        "success"
    )
    return redirect(
        url_for("groups.manage_groups")
    )

@groups_bp.route("/create_team", methods=["GET"])
def create_team_form():

    next_page = request.args.get("next")

    return render_template(
        "create_team.html",
        next_page=next_page
    )

@groups_bp.route("/create_team", methods=["POST"])
def create_team():
    name = request.form.get("name")
    next_page = request.form.get("next")
    description = request.form.get("description")
    team = Team(
        name=name,
        description=description
    )
    db.session.add(team)
    db.session.commit()
    flash(
        f"Team {name} skapades",
        "success"
    ) 
    if next_page in ["groups.manage_groups","students.manage"]:
        return redirect(url_for(next_page))
    return redirect(url_for("groups.manage_groups"))
    
@groups_bp.route("/edit_team", methods=["POST"])
def edit_team():
    team_id = request.form.get("team_id")
    team = db.session.get(
        Team,
        team_id
    )
    if not team:
        flash(
            "Teamet hittades inte.",
            "danger"
        )
        return redirect(
            url_for("groups.manage_groups")
        )
    name = request.form.get("name").strip()
    next_page = request.form.get("next")
    existing = db.session.scalar(
        select(Team).where(
            Team.name == name,
            Team.id != team.id
        )
    )
    if existing:
        flash(
            f"Ett team med namnet {name} finns redan.",
            "danger"
        )
        return redirect(
            url_for("groups.manage_groups")
        )
    team.name = name
    team.description = (
        request.form.get("description")
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(
            "Teamet kunde inte uppdateras.",
            "danger"
        )
        return redirect(
            url_for("groups.manage_groups")
        )
    flash(
        f"Teamet {name} uppdaterades.",
        "success"
    )
    if next_page in ["groups.manage_groups","students.manage"]:
        return redirect(url_for(next_page))
    return redirect(url_for("groups.manage_groups"))

@groups_bp.route("/delete_team/<int:team_id>", methods=["POST"])
def delete_team(team_id):
    team = db.session.get(
        Team,
        team_id
    )
    if not team:
        flash(
            "Gruppen hittades inte.",
            "danger"
        )
        return redirect(
            url_for("groups.manage_groups")
        )
    # Säkerhetskontroll
    if len(team.students) > 0:
        flash(
            "En grupp med elever kan inte tas bort permanent.",
            "danger"
        )
        return redirect(
            url_for("groups.manage_teams")
        )
    db.session.delete(team)
    db.session.commit()
    flash(
        f"Klassen {team.name} togs bort permanent.",
        "success"
    )
    return redirect(
        url_for("groups.manage_groups")
    )