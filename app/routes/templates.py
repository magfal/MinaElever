from flask import Blueprint, render_template, request, g, abort, redirect, url_for, flash
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.extensions import db
from app.models import Template, TemplateType, Question, QuestionTemplateLink
from app.services.utils import utc_now, utcify

templates_bp = Blueprint(
    "templates",
    __name__,
    url_prefix="/templates",
)

# HJÄLPFUNKTIONER
def template_is_locked(template):
    now = utc_now()
    return any(
        assignment.end_time is not None
        and utcify(assignment.end_time) < now
        for assignment in template.assignments
    )

# Routes
@templates_bp.get("/manage")
def manage():
    search = request.args.get("search", "").strip()
    template_type_name = request.args.get("template_type", "").strip()
    query = (
        select(Template)
        .options(
            selectinload(Template.question_links),
            selectinload(Template.assignments),
        )
    )
    if search:
        query = query.where(
            Template.title.ilike(f"%{search}%")
        )
    if template_type_name:
        try:
            template_type = TemplateType[template_type_name]
        except KeyError:
            template_type = None
        if template_type:
            query = query.where(
                Template.template_type == template_type
            )
    query = query.order_by(
        Template.created_at.desc()
    )
    templates = db.session.scalars(query).all()
    if request.headers.get("HX-Request"):
        return render_template(
            "templates/_templates_table.html",
            templates=templates,
            template_is_locked=template_is_locked,
        )
    return render_template(
        "templates/manage.html",
        templates=templates,
        template_types=list(TemplateType),
        template_type_name=template_type_name,
        search=search,
        template_is_locked=template_is_locked,
    )

@templates_bp.get("/new")
def new():
    questions = db.session.scalars(
        select(Question)
        .order_by(Question.created_at.desc())
    ).all()
    return render_template(
        "templates/new.html",
        template=None,
        template_types=list(TemplateType),
        questions=questions,
    )

@templates_bp.post("/new")
def create():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    template_type_name = request.form.get("template_type", "").strip()
    if not title:
        flash("Mallen måste ha en titel.", "warning")
        return redirect(url_for("templates.new"))
    try:
        template_type = TemplateType[template_type_name]
    except KeyError:
        flash("Ogiltig malltyp.", "danger")
        return redirect(url_for("templates.new"))
    template = Template(
        title=title,
        description=description or None,
        template_type=template_type,
        author_id=g.user.id,
    )
    db.session.add(template)
    question_ids = request.form.getlist("question_ids")
    selected_questions = []
    for question_id in question_ids:
        question = db.session.get(
            Question,
            int(question_id),
        )
        if question is None:
            continue
        try:
            order_index = int(
                request.form.get(
                    f"order_{question.id}",
                    "999999",
                )
            )
        except ValueError:
            order_index = 999999
        selected_questions.append(
            (order_index, question)
        )
    selected_questions.sort(
        key=lambda item: item[0]
    )
    for order_index, question in enumerate(
        question for _, question in selected_questions
    ):
        template.question_links.append(
            QuestionTemplateLink(
                question=question,
                order_index=order_index,
                required=(
                    request.form.get(
                        f"required_{question.id}"
                    ) == "on"
                ),
            )
        )
    db.session.commit()
    flash("Mallen skapades.", "success")
    return redirect(
        url_for(
            "templates.edit",
            template_id=template.id,
        )
    )

@templates_bp.get("/edit/<int:template_id>")
def edit(template_id):
    template = db.session.get(Template, template_id)
    if template is None:
        abort(404)
    questions = db.session.scalars(
        select(Question)
        .order_by(Question.created_at.desc())
    ).all()
    return render_template(
        "templates/new.html",
        template=template,
        template_types=list(TemplateType),
        questions=questions,
        template_is_locked=template_is_locked(template),
    )

@templates_bp.post("/edit/<int:template_id>")
def update(template_id):
    template = db.session.get(
        Template,
        template_id,
    )
    if template is None:
        abort(404)
    if template_is_locked(template):
        abort(403)
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    template_type_name = request.form.get("template_type", "").strip()
    if not title:
        flash(
            "Mallen måste ha en titel.",
            "warning",
        )
        return redirect(
            url_for(
                "templates.edit",
                template_id=template.id,
            )
        )
    try:
        template_type = TemplateType[
            template_type_name
        ]
    except KeyError:
        flash(
            "Ogiltig malltyp.",
            "danger",
        )
        return redirect(
            url_for(
                "templates.edit",
                template_id=template.id,
            )
        )
    template.title = title
    template.description = description or None
    template.template_type = template_type
    question_ids = request.form.getlist(
        "question_ids"
    )
    selected_questions = []
    for question_id in question_ids:
        question = db.session.get(
            Question,
            int(question_id),
        )
        if question is None:
            continue
        try:
            order_index = int(
                request.form.get(
                    f"order_{question.id}",
                    "999999",
                )
            )
        except ValueError:
            order_index = 999999
        selected_questions.append(
            (order_index, question)
        )
    selected_questions.sort(
        key=lambda item: item[0]
    )
    template.question_links.clear()
    for order_index, question in enumerate(
        question for _, question in selected_questions
    ):
        template.question_links.append(
            QuestionTemplateLink(
                question=question,
                order_index=order_index,
                required=(
                    request.form.get(
                        f"required_{question.id}"
                    ) == "on"
                ),
            )
        )
    db.session.commit()
    flash(
        "Mallen uppdaterades.",
        "success",
    )
    return redirect(
        url_for(
            "templates.edit",
            template_id=template.id,
        )
    )