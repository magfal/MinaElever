from flask import Blueprint, render_template, request, g, abort, redirect, url_for, flash
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.extensions import db
from app.models import Template, AssignmentType, Question, QuestionTemplateLink
from app.services.utils import utc_now, utcify
from app.services.auth import teacher_required

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
@teacher_required
def manage():
    search = request.args.get("search", "").strip()
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
        template_types=list(AssignmentType),
        search=search,
        template_is_locked=template_is_locked,
    )

@templates_bp.get("/new")
@teacher_required
def new():
    questions = db.session.scalars(
        select(Question)
        .order_by(Question.created_at.desc())
    ).all()
    return render_template(
        "templates/new.html",
        template=None,
        template_types=list(AssignmentType),
        questions=questions,
        table_mode="template",
        selected_question_ids=set(),
    )

@templates_bp.post("/new")
@teacher_required
def create():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    if not title:
        flash("Mallen måste ha en titel.", "warning")
        return redirect(url_for("templates.new"))
    template = Template(
        title=title,
        description=description or None,
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
@teacher_required
def edit(template_id):
    template = db.session.get(Template, template_id)
    if template is None:
        abort(404)
    questions = db.session.scalars(
        select(Question)
        .order_by(Question.created_at.desc())
    ).all()
    selected_question_ids = {
        link.question_id
        for link in template.question_links
    }
    return render_template(
        "templates/new.html",
        template=template,
        template_types=list(AssignmentType),
        questions=questions,
        template_is_locked=template_is_locked(template),
        table_mode="template",
        selected_question_ids=selected_question_ids,
    )

@templates_bp.post("/edit/<int:template_id>")
@teacher_required
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
    template.title = title
    template.description = description or None
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

@templates_bp.get("/manage/<int:template_id>")
@teacher_required
def manage_template(template_id):
    template = db.session.scalar(
        select(Template)
        .options(
            selectinload(Template.question_links)
            .selectinload(QuestionTemplateLink.question)
        )
        .where(Template.id == template_id)
    )

    if template is None:
        abort(404)

    question_links = sorted(
        template.question_links,
        key=lambda link: link.order_index,
    )

    return render_template(
        "templates/manage_template.html",
        template=template,
        question_links=question_links,
    )