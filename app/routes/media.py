import os
import uuid
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename
from datetime import date, timedelta
from thefuzz import fuzz, process
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_file
from sqlalchemy import select, case, and_, func
from sqlalchemy.dialects.mysql import match
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Media, Tag, TagType, QuestionType, Question, Choice, MediaType 
from app.services.htmx import toast
from app.services.auth import logout_everywhere, generate_code
from app.services.utils import utc_now
from app.services.utils import save_image
from app.services.tags import get_selected_media_tags

media_bp = Blueprint(
    "media",
    __name__,
    url_prefix="/media",
)

@media_bp.get("/")
def manage():
    search = request.args.get("search", "").strip()
    selected_tag_ids = request.args.getlist("tag_ids")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    query = (
        db.session.query(Media)
        .filter(Media.media_type == MediaType.IMAGE)
    )

    # Sök på bildnamn
    if search:
        query = query.filter(
            Media.name.ilike(f"%{search}%")
        )

    # Alla valda taggar måste finnas på bilden
    for tag_id in selected_tag_ids:
        query = query.filter(
            Media.tags.any(Tag.id == int(tag_id))
        )

    # Från-datum
    if date_from:
        query = query.filter(
            func.date(Media.created_at) >= date_from
        )

    # Till-datum
    if date_to:
        query = query.filter(
            func.date(Media.created_at) <= date_to
        )

    media = (
        query
        .order_by(Media.created_at.desc())
        .all()
    )

    tags = (
        db.session.query(Tag)
        .order_by(Tag.name)
        .all()
    )

    # HTMX: returnera bara bildkorten
    if request.headers.get("HX-Request"):
        return render_template(
            "media/_grid.html",
            media=media,
            selectable=False,
            media_manage=True,
        )

    # Vanlig sidladdning
    return render_template(
        "media/manage.html",
        media=media,
        tags=tags,
        selected_tag_ids=[int(tag_id) for tag_id in selected_tag_ids],
        search=search,
        date_from=date_from,
        date_to=date_to,
    )

@media_bp.get("/grid")
def grid():
    search = request.args.get("search", "").strip()
    selected_tag_ids = request.args.getlist("tag_ids")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    query = (
        db.session.query(Media)
        .filter(Media.media_type == MediaType.IMAGE)
    )

    if search:
        query = query.filter(
            Media.name.ilike(f"%{search}%")
        )

    for tag_id in selected_tag_ids:
        query = query.filter(
            Media.tags.any(Tag.id == int(tag_id))
        )

    if date_from:
        query = query.filter(
            func.date(Media.created_at) >= date_from
        )

    if date_to:
        query = query.filter(
            func.date(Media.created_at) <= date_to
        )

    media = (
        query
        .order_by(Media.created_at.desc())
        .all()
    )

    return render_template(
        "media/_grid.html",
        media=media,
        selectable=True,
        media_manage=False,
    )

@media_bp.post("/upload")
def upload():
    image_file = request.files.get("image")

    if image_file is None:
        flash("Ingen bild valdes.", "danger")
        return redirect(url_for("media.manage"))

    try:
        media_data = save_image(image_file)
    except ValueError as error:
        flash(str(error), "danger")
        return redirect(url_for("media.manage"))

    if media_data is None:
        flash("Ingen bild valdes.", "danger")
        return redirect(url_for("media.manage"))

    media = Media(
        name=media_data["name"],
        filepath=media_data["filepath"],
        media_type=MediaType.IMAGE,
        mime_type=media_data["mime_type"],
        size_bytes=media_data["size_bytes"],
    )

    db.session.add(media)
    db.session.commit()

    flash("Bilden laddades upp.", "success")

    return redirect(url_for("media.manage"))

@media_bp.get("/file/<int:media_id>")
def media_file(media_id):
    media = db.session.get(Media, media_id)
    if media is None:
        abort(404)
    if media.media_type != MediaType.IMAGE:
        abort(404)
    return send_file(
        media.filepath,
        mimetype=media.mime_type,
        download_name=media.name,
    )

@media_bp.post("/<int:media_id>/edit")
def edit(media_id):
    media = db.session.get(Media, media_id)

    if media is None:
        abort(404)

    media.name = request.form.get("name", "").strip()

    if not media.name:
        flash("Bilden måste ha ett namn.", "danger")
        return redirect(url_for("media.manage"))

    media.tags = get_selected_media_tags()

    db.session.commit()

    flash("Bilden uppdaterades.", "success")

    return redirect(url_for("media.manage"))

@media_bp.post("/<int:media_id>/delete")
def delete(media_id):
    media = db.session.get(Media, media_id)
    if media is None:
        abort(404)
    questions = (
        db.session.query(Question)
        .filter(
            db.or_(
                Question.text.contains(f"[{media.name}]"),
                Question.text.contains(f"[{media.name}:"),
            )
        )
        .all()
    )
    if questions:
        flash(
            "Bilden används i en eller flera frågor och kan inte tas bort.",
            "danger",
        )
        return redirect(url_for("media.manage"))
    filepath = media.filepath
    db.session.delete(media)
    db.session.commit()
    if os.path.exists(filepath):
        os.remove(filepath)
    return redirect(url_for("media.manage"))