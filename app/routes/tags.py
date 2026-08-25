from flask import Blueprint
from flask import render_template, request, redirect, url_for, flash, jsonify, g, make_response, abort
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Response, Student, Group, Team, Tag, TagType
from app.services.htmx import toast
from app.services.auth import logout_everywhere, generate_code

tags_bp = Blueprint("tags", __name__, url_prefix="/tags")

@tags_bp.get("/manage")
def manage():
    tags = db.session.scalars(
        select(Tag)
        .order_by(Tag.name)
    ).all()
    return render_template(
        "tags/manage.html",
        tags=tags,
    )

@tags_bp.get("/create_tag")
def new_tag_modal():
    return render_template(
        "tags/_tags_new_form.html",
        tag=None,
        action=url_for("tags.create_tag"),
        title="Nya taggar",  
        tag_types = list(TagType)  
    )

@tags_bp.post("/create_tag")
def create_tag():
    tag_list = request.form.get("tag_list", "").strip()
    tag_type = request.form.get("tag_type", "")
    if not tag_list:
        flash("Tagglistan får inte var tomt", "warning")
        response = make_response("", 204)
        response.headers["HX-Redirect"] = url_for("tags.manage")
        return response
    new_tags = []
    for line in tag_list.split("\n"):
        line = line.strip()
        if not line:
            continue
        if "," in line:
            name, description = line.split(",", 1)
            new_tags.append((name.strip(), description.strip(), tag_type))
        else:
            new_tags.append((line, "", tag_type))
    existing_names = db.session.scalars(select(Tag.name)).all()
    try:
        for name, description, tag_type  in new_tags:
            if name in existing_names:
                db.session.rollback()
                response = make_response("")
                toast(response, f"Taggen {name} finns redan.", "warning", reswap="none")
                return response
            db.session.add(
                Tag(
                    name=name,
                    description=description,
                    tag_type=tag_type))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        response = make_response("")
        toast(response, f"Databasfel", "warning", reswap="none")
        return response
    tags = db.session.scalars(
        select(Tag)
        .order_by(Tag.name)
        ).all()
    print(tags)
    response = make_response(render_template(
        "tags/_tags_table.html", 
        tags=tags)) 
    toast(response, f"Taggen {", ".join(tag for tag, _, _ in new_tags)} skapades")
    return response

@tags_bp.get("/edit_tag/<int:tag_id>")
def edit_tag_modal(tag_id):    
    tag = db.session.get(Team, tag_id)
    if not tag:
        response = make_response("")
        toast(response,f"Taggen hittades inte i databasen.", "warning")
        return response
    return render_template( 
        "tags/_tag_change_form.html",
        tag=tag,
        action=url_for("tags.edit_tag", tag_id=tag.id),
        title="Ändra Tagg"    
        )

@tags_bp.post("/edit_tag/<int:tag_id>")
def edit_tag(tag_id):
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    if not name:
        response = make_response("")
        toast(response, "Namnet får inte var tomt", "warning", reswap="none")
        return response
    tag = db.session.get(Tag, tag_id)
    if not tag:
        response = make_response("")
        toast(response,f"Taggen finns inte i databasen.", "warning")
        return response
    old_name = tag.name
    try:
        tag.name = name
        tag.description = description
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        response = make_response("")
        toast(response, f"Gruppen {name} finns redan.", "warning", reswap="none")
        return response        
    tags = db.session.scalars(
        select(Tag)
        .order_by(Tag.name)
        ).all()
    response = make_response(render_template(
        "groups/_tags_table.html", 
        tags=tags)) 
    toast(response, f"{old_name} ändrades till {name}")
    return response

@tags_bp.post("/delete_tag/<int:tag_id>")
def delete_tag(tag_id):
    tag = db.session.get(Tag, tag_id)
    if not tag:
        flash("Taggen hittades inte.", "danger")
        return redirect(url_for("tags.manage"))
    if len(tag.students) > 0:
        flash("En tagg somm tillhör en fråga kan inte tas bort permanent.", "danger")
        return redirect(url_for("tags.manage_tags"))
    db.session.delete(tag)
    db.session.commit()
    flash(f"Taggen {tag.name} togs bort permanent.", "success")
    return redirect(url_for("tags.manage"))