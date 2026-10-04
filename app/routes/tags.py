import json
from flask import Blueprint
from flask import render_template, request, redirect, url_for, flash, make_response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Tag, TagType
from app.services.htmx import toast
from app.services.auth import teacher_required

tags_bp = Blueprint("tags", __name__, url_prefix="/tags")

@tags_bp.get("/manage")
@teacher_required
def manage():
    tag_type_name = request.args.get("tag_type", "").strip()
    query = select(Tag)
    if tag_type_name:
        try:
            tag_type = TagType[tag_type_name]
        except KeyError:
            tag_type = None
        if tag_type:
            query = query.where(
                Tag.tag_type == tag_type
            )
    tags = db.session.scalars(query).all()
    if request.headers.get("HX-Request"):
        return render_template(
            "tags/_tags_table.html",
            tags=tags,
        )
    tag_types = list(TagType)
    return render_template(
        "tags/manage.html",
        tag_types=tag_types,
        tags=tags
    )

@tags_bp.get("/create_tag")
@teacher_required
def new_tag_modal():
    from_media = request.args.get("from") == "media"
    return render_template(
        "tags/_tags_new_form.html",
        tag=None,
        action=url_for(
            "tags.create_tag",
            **({"from": "media"} if from_media else {})
        ),
        title="Ny tagg",
        tag_types=list(TagType),
        from_media=from_media,
    )

@tags_bp.post("/create_tag")
@teacher_required
def create_tag():
    tag_list = request.form.get("tag_list", "").strip()
    tag_type_name = request.form.get("tag_type", "").strip()
    if not tag_list:
        flash("Tagglistan får inte vara tom.", "warning")
        response = make_response("", 204)
        response.headers["HX-Redirect"] = url_for("tags.manage")
        return response
    try:
        tag_type = TagType[tag_type_name]
    except KeyError:
        response = make_response("")
        toast(response, "Ogiltig taggtyp.", "warning", reswap="none")
        return response
    new_tags = []
    for new_tag in tag_list.split("\n"):
        name = new_tag.strip()
        if not name:
            continue
        new_tags.append((name, tag_type))
    existing_tags = db.session.scalars(
        select(Tag)).all()
    try:
        for name, tag_type in new_tags:
            if any(
                tag.name == name
                and tag.tag_type == tag_type
                for tag in existing_tags
            ):
                db.session.rollback()
                response = make_response("")
                toast(response, f"Taggen {name} finns redan.", "warning", reswap="none")
                return response
            db.session.add(
                Tag(name=name, tag_type=tag_type))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        response = make_response("")
        toast(response, "Databasfel när taggarna skulle skapas.", "warning", reswap="none")
        return response
    # Ny tagg skapad från media- eller frågevy
    if request.args.get("from") in ("media", "question"):
        if len(new_tags) != 1:
            response = make_response("")
            toast(response, "Här kan bara en tagg skapas åt gången.", "warning", reswap="none")
            return response
        name, tag_type = new_tags[0]
        tag = db.session.scalar(
            select(Tag).where(
                Tag.name == name,
                Tag.tag_type == tag_type,
            )
        )
        response = make_response("", 204)
        response.headers["HX-Trigger"] = json.dumps({
            "tag-created": {
                "id": tag.id,
                "name": tag.name,
                "tag_type": tag.tag_type.value,
            }
        })
        toast(response, f"Taggen {tag.name} skapades.", "success")
        return response
    # Vanlig tagghantering
    tags = db.session.scalars(
        select(Tag).order_by(Tag.name)
        ).all()
    response = make_response(
        render_template(
            "tags/_tags_table.html",
            tags=tags)
            )
    toast(response, f"Taggen/arna {', '.join(name for name, _ in new_tags)} skapades.", "success")
    return response

@tags_bp.get("/edit_tag/<int:tag_id>")
@teacher_required
def edit_tag_modal(tag_id):

    tag = db.session.get(Tag, tag_id)
    tag_types = list(TagType)

    if not tag:
        response = make_response("")
        toast(
            response,
            "Taggen hittades inte i databasen.",
            "warning"
        )
        return response

    return render_template(
        "tags/_tag_change_form.html",
        tag=tag,
        tag_types=tag_types,
        action=url_for(
            "tags.edit_tag",
            tag_id=tag.id
        ),
        title="Ändra tagg"
    )

@tags_bp.post("/edit_tag/<int:tag_id>")
@teacher_required
def edit_tag(tag_id):
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    tag_type = request.form.get("tag_type", "").strip()
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
        tag.tag_type = tag_type
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        response = make_response("")
        toast(response, f"Taggenen {name} finns redan.", "warning", reswap="none")
        return response        
    tags = db.session.scalars(
        select(Tag)
        .order_by(Tag.name)
        ).all()
    response = make_response(render_template(
        "tags/_tags_table.html", 
        tags=tags)) 
    toast(response, f"{old_name} ändrades till {name}")
    return response

@tags_bp.post("/delete_tag/<int:tag_id>")
@teacher_required
def delete_tag(tag_id):
    tag = db.session.get(Tag, tag_id)
    if not tag:
        flash("Taggen hittades inte.", "danger")
        return redirect(url_for("tags.manage"))
    if tag.questions or tag.media:
        flash(
            "En tagg som används av en fråga eller mediabild kan inte tas bort permanent.",
            "danger"
        )
        return redirect(url_for("tags.manage"))
    db.session.delete(tag)
    db.session.commit()
    flash(f"Taggen {tag.name} togs bort permanent.", "success")
    return redirect(url_for("tags.manage"))

@tags_bp.get("/create_media_tag")
@teacher_required
def create_media_tag_modal():

    name = request.args.get("name", "").strip()

    return render_template(
        "tags/_media_tag_new_form.html",
        name=name,
        tag_types=list(TagType),
    )

@tags_bp.post("/create_media_tag")
@teacher_required
def create_media_tag():

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    tag_type_name = request.form.get("tag_type", "").strip()

    if not name:
        response = make_response("")
        toast(
            response,
            "Namnet får inte vara tomt.",
            "warning",
            reswap="none",
        )
        return response

    try:
        tag_type = TagType[tag_type_name]
    except KeyError:
        response = make_response("")
        toast(
            response,
            "Ogiltig taggtyp.",
            "warning",
            reswap="none",
        )
        return response

    existing = db.session.scalar(
        select(Tag).where(Tag.name == name)
    )

    if existing is not None:
        response = make_response("")
        toast(
            response,
            f"Taggen {name} finns redan.",
            "warning",
            reswap="none",
        )
        return response

    tag = Tag(
        name=name,
        description=description,
        tag_type=tag_type,
    )

    db.session.add(tag)
    db.session.commit()

    response = make_response("")
    response.headers["HX-Trigger"] = json.dumps({
        "media-tag-created": {
            "id": tag.id,
            "name": tag.name,
            "tag_type": tag.tag_type.name,
        }
    })

    return response
