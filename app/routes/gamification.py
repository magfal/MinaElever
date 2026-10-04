from flask import Blueprint
from app.services.auth import teacher_required

gamification_bp = Blueprint(
    "gamification",
    __name__,
    url_prefix="/gamification"
)

@gamification_bp.route("/manage")
@teacher_required
def manage_rules():
    return "Ändra regler"