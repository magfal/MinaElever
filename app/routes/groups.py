from flask import Blueprint, render_template, g, request, redirect, url_for, flash, make_response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Group, Team
from app.services.htmx import toast
from app.services.auth import logout_everywhere, generate_code

groups_bp = Blueprint("groups", __name__, url_prefix="/groups")       

@groups_bp.get("/manage")
def manage():
    groups = db.session.scalars(
        select(Group)
        .where(Group.is_active == True)
        .where(Group.author_id == g.user.id)
        .order_by(Group.name)
    ).all()
    archived_groups = db.session.scalars(
        select(Group)
        .where(Group.is_active == False)
        .where(Group.author_id == g.user.id)
        .order_by(Group.name)
    ).all()
    teams = db.session.scalars(
        select(Team)
        .where(Team.author_id == g.user.id)
        .order_by(Team.name)
    ).all()
    return render_template(
        "groups/manage.html",
        groups=groups,
        archived_groups=archived_groups,
        teams=teams
    )

@groups_bp.get("/create_group")
def new_group_modal():
    return render_template(
        "groups/_group_form.html",
        group=None,
        action=url_for("groups.create_group"),
        title="Ny klass"    
    )

@groups_bp.post("/create_group")
def create_group():
    name = request.form.get("name", "").strip()
    archived = request.form.get("archived") is not None
    if not name:
        response = make_response("")
        toast(response, "Namnet får inte var tomt", "warning", reswap="none")
        return response
    try:
        new_group = Group(author_id=g.user.id, name=name, is_active=not archived)
        db.session.add(new_group)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        response = make_response("")
        toast(response, f"Klassen {name} finns redan.", "warning", reswap="none")
        return response
    if archived:
        flash(f"Klassen {name} skapades", "success")
        response = make_response("", 204)
        response.headers["HX-Redirect"] = url_for("groups.manage")
        return response
    groups = db.session.scalars(
        select(Group)
        .where(Group.is_active == True)
        .where(Group.author_id == g.user.id)
        .order_by(Group.name)
        ).all()
    response = make_response(render_template(
        "groups/_groups_table.html", 
        groups=groups)) 
    toast(response, f"Klassen {name} skapades")
    return response
    
@groups_bp.get("/edit_group/<int:group_id>")
def edit_group_modal(group_id):
    group = db.session.get(Group, group_id)
    if not group:
        response = make_response("")
        toast(response,f"Klassen hittades inte.", "warning")
        return response
    return render_template( 
        "groups/_group_form.html",
        group=group,
        action=url_for("groups.edit_group", group_id=group.id),
        title="Ändra klass"    
        )

@groups_bp.post("/edit_group/<int:group_id>")
def edit_group(group_id):
    name = request.form.get("name", "").strip()
    archived = request.form.get("archived") is not None
    if not name:
        response = make_response("")
        toast(response, "Namnet får inte var tomt", "warning", reswap="none")
        return response
    group = db.session.get(Group, group_id)
    if not group:
        response = make_response("")
        toast(response,f"Klassen finns inte i databasen.", "warning")
        return response
    old_name = group.name
    old_is_active = group.is_active
    try:
        group.name = name
        group.is_active = not archived
        if old_is_active != group.is_active:
            if group.is_active == True:
                for student in group.students:
                    student.login_code = generate_code()
                    student.is_active = True
            else:
                for student in group.students:
                    logout_everywhere(student.id)
                    student.is_active = False
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        response = make_response("")
        toast(response, f"Klassen {name} finns redan.", "warning", reswap="none")
        return response        
    messages = []
    if old_is_active != group.is_active:
        messages.append("arkiverades" if archived else "återaktiverades")
    if old_name != group.name:
        messages.append(f"namnet ändrades till {group.name}")
    if messages:
        flash(f"{old_name} " + " och ".join(messages), "success")
    response = make_response("", 204)
    response.headers["HX-Redirect"] = url_for("groups.manage")
    return response

@groups_bp.post("/delete_group/<int:group_id>")
def delete_group(group_id):
    group = db.session.get(
        Group,
        group_id
    )
    if not group:
        flash("Klassen hittades inte.", "danger")
        return redirect(url_for("groups.manage"))
    if len(group.students) > 0:
        flash("En klass med elever kan inte tas bort permanent.", "danger")
        return redirect(url_for("groups.manage"))
    db.session.delete(group)
    db.session.commit()
    flash(f"Klassen {group.name} togs bort permanent.", "success")
    return redirect(url_for("groups.manage"))

@groups_bp.get("/create_team")
def new_team_modal():
    return render_template(
        "groups/_team_form.html",
        team=None,
        action=url_for("groups.create_team"),
        title="Ny grupp"    
    )

@groups_bp.post("/create_team")
def create_team():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    if not name:
        response = make_response("")
        toast(response, "Namnet får inte var tomt", "warning", reswap="none")
        return response
    try:
        new_team = Team(author_id=g.user.id, name=name, description=description)
        db.session.add(new_team)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        response = make_response("")
        toast(response, f"Gruppen {name} finns redan.", "warning", reswap="none")
        return response
    teams = db.session.scalars(
        select(Team)
        .order_by(Team.name)
        .where(Team.author_id == g.user.id)
        ).all()
    response = make_response(render_template(
        "groups/_teams_table.html", 
        teams=teams)) 
    toast(response, f"Gruppen {name} skapades")
    return response

@groups_bp.get("/edit_team/<int:team_id>")
def edit_team_modal(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        response = make_response("")
        toast(response,f"Gruppen hittades inte.", "warning")
        return response
    return render_template( 
        "groups/_team_form.html",
        team=team,
        action=url_for("groups.edit_team", team_id=team.id),
        title="Ändra Grupp"    
        )

@groups_bp.post("/edit_team/<int:team_id>")
def edit_team(team_id):
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    if not name:
        response = make_response("")
        toast(response, "Namnet får inte var tomt", "warning", reswap="none")
        return response
    team = db.session.get(Team, team_id)
    if not team:
        response = make_response("")
        toast(response,f"Gruppen finns inte i databasen.", "warning")
        return response
    old_name = team.name
    try:
        team.name = name
        team.description = description
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        response = make_response("")
        toast(response, f"Gruppen {name} finns redan.", "warning", reswap="none")
        return response        
    teams = db.session.scalars(
        select(Team)
        .order_by(Team.name)
        ).all()
    response = make_response(render_template(
        "groups/_teams_table.html", 
        teams=teams)) 
    toast(response, f"{old_name} ändrades till {name}")
    return response

@groups_bp.post("/delete_team/<int:team_id>")
def delete_team(team_id):
    team = db.session.get(
        Team,
        team_id
    )
    if not team:
        flash("Gruppen hittades inte.", "danger")
        return redirect(url_for("groups.manage"))
    if len(team.students) > 0:
        flash("En grupp med elever kan inte tas bort permanent.", "danger")
        return redirect(url_for("groups.manage_teams"))
    db.session.delete(team)
    db.session.commit()
    flash(f"Klassen {team.name} togs bort permanent.", "success")
    return redirect(url_for("groups.manage"))