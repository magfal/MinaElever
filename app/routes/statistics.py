from flask import Blueprint
from app.services.auth import teacher_required

statistics_bp = Blueprint(
    "statistics",
    __name__,
    url_prefix="/statistics"
)

@statistics_bp.route("/show")
@teacher_required
def show_statistics():
    return "Visa statistik"