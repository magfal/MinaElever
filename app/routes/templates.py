from datetime import date, timedelta
from flask import Blueprint, render_template, request, g, abort, redirect, url_for, flash
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from app.extensions import db
from app.models import Template, AssignmentType, Question, Tag, TagType, QuestionTemplateLink
from app.services.auth import teacher_required
from app.routes.assignments import assignment_status
from app.routes.questions import question_action, get_question_form_data
from app.services.utils import utc_now, utcify

templates_bp = Blueprint(
    "templates",
    __name__,
    url_prefix="/templates",
)

# HJÄLPFUNKTIONER
def template_action(template):
    if not template.assignments:
        return "new"
    if any(
        assignment_status(assignment) == "Avslutad"
        for assignment in template.assignments
    ):
        return "locked"
    return "active"

# Routes
@templates_bp.get("/manage")
@teacher_required
def manage():
    search = request.args.get("search", "").strip()
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    tag_ids = request.args.getlist("tag_ids", type=int)
    selected_tag_ids = [str(tag_id) for tag_id in tag_ids]
    query = (
        select(Template)
        .options(
            selectinload(Template.question_links),
            selectinload(Template.assignments),
        )
    )
    if search:
        query = query.where(
            or_(
                Template.title.ilike(f"%{search}%"),
                Template.description.ilike(f"%{search}%"),
            )
        )
    #Från datum
    if date_from:
        try:
            date_from = date.fromisoformat(date_from)
        except ValueError:
            date_from = None
    if date_from:
        query = query.where(
            Template.created_at >= date_from
        )
    # Till datum
    if date_to:
        try:
            date_to = date.fromisoformat(date_to)
        except ValueError:
            date_to = None
    if date_to:
        query = query.where(
                Template.created_at
                < date_to + timedelta(days=1)
            )
    # Taggar
    for tag_id in tag_ids:
        query = query.where(
            Template.question_links.any(
                QuestionTemplateLink.question.has(
                    Question.tags.any(Tag.id == tag_id)
                )
            )
        )
    query = query.order_by(
        Template.created_at.desc()
    )
    tag_types = list(TagType)
    tags = db.session.scalars(
        select(Tag).order_by(Tag.name)
        ).all()
    templates = db.session.scalars(query).all()
    if request.headers.get("HX-Request"):
        return render_template(
            "templates/_templates_table.html",
            templates=templates,
            template_action=template_action,
        )
    return render_template(
        "templates/manage.html",
        templates=templates,
        template_types=list(AssignmentType),
        search=search,
        template_action=template_action,
        date_from=date_from,
        date_to=date_to,
        tag_types=tag_types,
        tags=tags,
        selected_tag_ids=selected_tag_ids,
    )

@templates_bp.route("/new", methods=["GET", "POST"])
@teacher_required
def new():
    if request.method == "GET":
        selected_question_ids = set(
            request.args.getlist("selected_question_ids", type=int)
        )

        # Hämta frågor som ska visas i de två tabellerna
        selected_questions = db.session.scalars(
            select(Question)
            .where(Question.id.in_(selected_question_ids))
            .order_by(Question.created_at.desc())
        ).all() if selected_question_ids else []

        available_questions = db.session.scalars(
            select(Question)
            .where(~Question.id.in_(selected_question_ids))
            .order_by(Question.created_at.desc())
        ).all()

        question_types, tag_types, tags = get_question_form_data()
        today = utc_now().strftime("%Y-%m-%d")

        return render_template(
            "questions/manage.html",
            page_mode="template_new",
            template=None,
            selected_questions=selected_questions,
            available_questions=available_questions,
            selected_question_ids=selected_question_ids,
            question_types=question_types,
            tag_types=tag_types,
            tags=tags,
            today=today,
            question_action=question_action,
        ) 
    # POST – skapa mallen
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
    selected_question_ids = {
        link.question_id
        for link in template.question_links
    }
    selected_questions = db.session.scalars(
        select(Question)
        .where(Question.id.in_(selected_question_ids))
        .order_by(Question.created_at.desc())
    ).all() if selected_question_ids else []
    available_questions = db.session.scalars(
        select(Question)
        .where(~Question.id.in_(selected_question_ids))
        .order_by(Question.created_at.desc())
    ).all()
    question_types, tag_types, tags = get_question_form_data()
    today = utc_now().strftime("%Y-%m-%d")
    return render_template(
        "questions/manage.html",
        page_mode="template_edit",
        template=template,
        selected_questions=selected_questions,
        available_questions=available_questions,
        selected_question_ids=selected_question_ids,
        question_types=question_types,
        tag_types=tag_types,
        tags=tags,
        today=today,
        question_action=question_action,
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

    if template_action(template) == "locked":
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

@templates_bp.get("/<int:template_id>/copy")
@teacher_required
def copy(template_id):
    template = db.session.get(Template, template_id)

    if template is None:
        abort(404)

    new_template = Template(
        author_id=g.user.id,
        title=f"{template.title} - kopia",
        description=template.description,
    )

    db.session.add(new_template)
    db.session.flush()

    for link in template.question_links:
        new_template.question_links.append(
            QuestionTemplateLink(
                question_id=link.question_id,
                order_index=link.order_index,
                required=link.required,
                extra_data=link.extra_data,
            )
        )

    db.session.commit()

    return redirect(
        url_for(
            "templates.edit",
            template_id=new_template.id,
        )
    )

@templates_bp.post("/delete/<int:template_id>")
@teacher_required
def delete(template_id):
    template = db.session.get(Template, template_id)

    if template is None:
        abort(404)

    if template_action(template) != "new":
        abort(403)

    db.session.delete(template)
    db.session.commit()

    flash(
        "Mallen togs bort.",
        "success",
    )

    return redirect(
        url_for("templates.manage")
    )