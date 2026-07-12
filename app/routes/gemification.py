from flask import Blueprint

gemification_bp = Blueprint(
    "gemification",
    __name__,
    url_prefix="/gemification"
)

@gemification_bp.route("/manage")
def manage_rules():
    return "Ändra regler"