from flask import request
from sqlalchemy import select
from app.extensions import db
from app.models import Tag, TagType
from app.extensions import db

def get_or_create_tag(tag_name):
    tag = db.session.execute(
        db.select(Tag).filter_by(name=tag_name)
    ).scalar_one_or_none()
    if not tag:
        tag = Tag(name=tag_name)
        db.session.add(tag)
        db.session.commit()
    return tag

def get_selected_tags():
    tag_ids = request.form.getlist("tag_ids")
    selected_tags = []
    for value in tag_ids:
        value = value.strip()
        if not value or not value.isdigit():
            continue
        tag = db.session.get(Tag, int(value))
        if tag is not None:
            selected_tags.append(tag)
    return selected_tags

def get_selected_media_tags():
    values = request.form.getlist("tag_ids")
    selected_tags = []
    for value in values:
        value = value.strip()
        if not value or not value.isdigit():
            continue
        tag = db.session.get(Tag, int(value))
        if tag is not None:
            selected_tags.append(tag)
    return selected_tags