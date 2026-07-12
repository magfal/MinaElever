from flask import Blueprint

statistics_bp = Blueprint(
    "statistics",
    __name__,
    url_prefix="/statistics"
)

@statistics_bp.route("/show")
def show_statistics():
    return "Visa statistik"