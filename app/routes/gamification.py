from flask import Blueprint

gamification_bp = Blueprint(
    "gamification",
    __name__,
    url_prefix="/gamification"
)

@gamification_bp.route("/manage")
def manage_rules():
    return "Ändra regler"