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
    tag_groups = {
        TagType.SUBJECT: request.form.getlist("subject_tag_ids"),
        TagType.AREA: request.form.getlist("area_tag_ids"),
        TagType.DECK: request.form.getlist("deck_tag_ids"),
        TagType.OTHER: request.form.getlist("other_tag_ids"),
    }

    selected_tags = []

    for tag_type, values in tag_groups.items():
        for value in values:
            value = value.strip()

            if not value:
                continue

            # Befintlig tagg
            if value.isdigit():
                tag = db.session.get(Tag, int(value))

                if tag is not None:
                    selected_tags.append(tag)

                continue

            # Ny tagg
            tag = db.session.scalar(
                select(Tag).where(Tag.name == value)
            )

            if tag is None:
                tag = Tag(
                    name=value,
                    tag_type=tag_type
                )
                db.session.add(tag)

            selected_tags.append(tag)

    return selected_tags

def get_selected_media_tags():
    values = request.form.getlist("tag_ids")

    selected_tags = []

    for value in values:
        value = value.strip()

        if not value:
            continue

        # Befintlig tagg
        if value.isdigit():
            tag = db.session.get(Tag, int(value))

            if tag is not None:
                selected_tags.append(tag)

            continue

        # Ny tagg
        tag = db.session.scalar(
            select(Tag).where(Tag.name == value)
        )

        if tag is None:
            tag = Tag(
                name=value,
                tag_type=TagType.OTHER
            )
            db.session.add(tag)

        selected_tags.append(tag)

    return selected_tags