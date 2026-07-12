from ..extensions import db
from app.models import Tag

def get_or_create_tag(tag_name):
    tag = db.session.execute(
        db.select(Tag).filter_by(name=tag_name)
    ).scalar_one_or_none()

    if not tag:
        tag = Tag(name=tag_name)

    return tag