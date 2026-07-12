from flask import Blueprint

templates_bp = Blueprint(
    "templates",
    __name__,
    url_prefix="/templates"
)

@templates_bp.route("/create")
def create_template():
    return "Skapa templat"