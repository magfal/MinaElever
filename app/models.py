from __future__ import annotations
import enum
from datetime import datetime, timezone, timedelta
from sqlalchemy import JSON, Column, Table, String, Enum, Boolean, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from .services.utils import utc_now, utcify

# -------------------------------------------------
# ENUMS
# -------------------------------------------------

class QuestionType(enum.Enum):
    TEXT = "Text"
    NUMBER = "Tal"
    BOOLEAN = "Sant/Falskt"
    DATE = "Datum"
    SLIDER = "Slider"
    SINGLE_CHOICE = "Enkelvalsvar"
    MULTIPLE_CHOICE = "Flervalssvar"
    FILE_UPLOAD = "Filuppladdning"

class TagType(enum.Enum):
    SUBJECT = "Ämne"
    AREA = "Område"
    DECK = "Kortlek"
    OTHER = "Allmän"

class MediaType(enum.Enum):
    IMAGE = "Bild"
    VIDEO = "Video"
    AUDIO = "Ljud"
    DOCUMENT = "Dokument"

class TemplateType(enum.Enum):
    TASK = "Uppgift"                # Uppgift elev gör under lektion eller hemma (med hjälpmedel)
    INQUIRY = "Undersökande fråga"  # Uppmaning till elev att ställa fråga
    TEST = "Test"                   # Uppgift elev gör i skolan utan hjälp
    DIAGNOSTIC = "Diagnos"          # Uppgift eleven gör i skolan men som inte bedöms
    FLASHCARD = "Flashcard"         # Uppgift elev får att öva på
    REFLECTION = "Reflexion"        # Elevreflexion eller utvärdering 
    OBSERVATION = "Observation"     # Observation lärare gör av elevs förmåga
    NOTE = "Notering"               # Notering av elevs beteende som lärare gör

class PointType(enum.Enum):
    CORRECT_ANSWER = "Rätt svar"
    ASSIGNMENT_SUBMITTED = "Inlämnad uppgift"
    EARLY_SUBMISSION = "Tidig inlämning"
    WRITTEN_QUESTION = "Skrivit fråga"
    ANSWERED_QUESTION = "Svarat på fråga"
    FLASHCARD = "Flashcard"
    STREAK_BONUS = "Streak bonus"
    TEACHER_REWARD = "Lärare"
    BADGE_REWARD = "Badge reward"

# -------------------------------------------------
# ASSOCIATION + JOINT ENTITY TABLES 
# -------------------------------------------------

question_tag_link = Table(
    "question_tag_link",
    Base.metadata,
    Column("question_id", ForeignKey("questions.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)

media_tag_link = Table(
    "media_tag_link",
    Base.metadata,
    Column("media_id", ForeignKey("media.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)

student_team_link = Table(
    "student_team_link",
    Base.metadata,
    Column("team_id", ForeignKey("teams.id"), primary_key=True),
    Column("student_id", ForeignKey("students.id"), primary_key=True),
)

student_assignment_link = Table(
    "student_assignment_link",
    Base.metadata,  
    Column("assignment_id", ForeignKey("assignments.id"), primary_key=True),
    Column("student_id", ForeignKey("students.id"), primary_key=True),
)

question_media_link = Table(
    "question_media_link",
    Base.metadata,
    Column("question_id", ForeignKey("questions.id"), primary_key=True),
    Column("media_id", ForeignKey("media.id"), primary_key=True),
)

response_media_link = Table(
    "response_media_link",
    Base.metadata,
    Column("response_id", ForeignKey("responses.id"), primary_key=True),
    Column("media_id", ForeignKey("media.id"), primary_key=True),
)

student_badge_link = Table(
    "student_badge_link",
    Base.metadata,
    Column("student_id", ForeignKey("students.id"), primary_key=True),
    Column("badge_id", ForeignKey("badges.id"), primary_key=True),
)

class QuestionTemplateLink(Base):
    __tablename__ = "question_template_link"
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), primary_key=True)
    order_index: Mapped[int] = mapped_column(default=0)
    required: Mapped[bool] = mapped_column(default=True)
    extra_data: Mapped[dict|None] = mapped_column(JSON)
    # Relationer
    template: Mapped["Template"] = relationship(back_populates="question_links")
    question: Mapped["Question"] = relationship(back_populates="template_links")

# ------------------------------------------------------
# CORE TABLES (QUESTION, TEMPLATE, ASSIGNMENT, RESPONSE
# ------------------------------------------------------

class Question(Base):
    __tablename__ = 'questions'
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType), default=QuestionType.TEXT, nullable=False)
    expected_answer: Mapped[dict|None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)    
    # Relationer
    author: Mapped[User] = relationship(back_populates="questions_created", foreign_keys=[author_id])
    choices: Mapped[list["Choice"]] = relationship(back_populates="question", cascade="all, delete-orphan")
    template_links: Mapped[list["QuestionTemplateLink"]] = relationship(back_populates="question", cascade="all, delete-orphan")
    responses: Mapped[list["Response"]] = relationship(back_populates="question")
    tags: Mapped[list[Tag]] = relationship(secondary=question_tag_link, back_populates="questions")
    media: Mapped[list[Media]] = relationship(secondary=question_media_link, back_populates="questions")

class Template(Base):
    __tablename__ = "templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str|None] = mapped_column(Text)
    template_type: Mapped[TemplateType] = mapped_column(Enum(TemplateType),  default=TemplateType.TASK, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    # Relationer
    author: Mapped[User] = relationship(back_populates="templates_created", foreign_keys=[author_id])
    question_links: Mapped[list["QuestionTemplateLink"]] = relationship(back_populates="template", cascade="all, delete-orphan")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="template")
    responses: Mapped[list["Response"]] = relationship(back_populates="template")

class Assignment(Base):
    __tablename__ = "assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), index=True)
    label: Mapped[str | None] = mapped_column(String(20), nullable=True,)
    start_time: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable = True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    # Relationer
    author: Mapped[User] = relationship(back_populates="assignments_created", foreign_keys=[author_id])
    template: Mapped[Template] = relationship(back_populates="assignments")
    responses: Mapped[list[Response]] = relationship(back_populates="assignment")
    students: Mapped[list[Student]] = relationship(secondary=student_assignment_link, back_populates="assignments")

class Response(Base):
    __tablename__ = "responses"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=True)
    assignment_id: Mapped[int|None] = mapped_column(ForeignKey("assignments.id"), nullable=True, index=True)
    parent_response_id: Mapped[int|None] = mapped_column(ForeignKey("responses.id"),nullable=True)
    answer:Mapped[dict|None] = mapped_column(JSON)
    student_question: Mapped[str|None] = mapped_column(Text)
    comment: Mapped[str|None] = mapped_column(Text)
    is_private: Mapped[bool] = mapped_column(default=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ip_address: Mapped[str|None] = mapped_column(String(100))
    device: Mapped[str|None] = mapped_column(String(300))
    # Relationer
    student: Mapped[Student] = relationship(back_populates="responses", foreign_keys=[student_id])
    author: Mapped[User] = relationship(back_populates="responses_created", foreign_keys=[author_id])
    assignment: Mapped[Assignment|None] = relationship(back_populates="responses")
    template: Mapped[Template] = relationship(back_populates="responses")
    question: Mapped[Question] = relationship(back_populates="responses")
    media: Mapped[list[Media]] = relationship(secondary=response_media_link, back_populates="responses")
    point_transactions: Mapped[list[PointTransaction]] = relationship(back_populates="response",cascade="all, delete-orphan")
    parent: Mapped[Response|None] = relationship("Response", remote_side="Response.id", back_populates="children")
    children: Mapped[list[Response]] = relationship("Response", back_populates="parent")

# -------------------------------------------------
# INDIVIDS
# -------------------------------------------------

class Group(Base):
    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    #Relationer
    author: Mapped["User"] = relationship(back_populates="groups_created",foreign_keys=[author_id])
    students: Mapped[list["Student"]] = relationship(back_populates="group", foreign_keys="Student.group_id", order_by="Student.name")

class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)    
    name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str | None] = mapped_column(String(120))
    # Relationer
    author: Mapped[User] = relationship(back_populates="teams_created", foreign_keys=[author_id])
    students: Mapped[list["Student"]] = relationship(secondary=student_team_link, back_populates="teams")

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    login_code: Mapped[str] = mapped_column(String(20), unique=True)
    last_seen: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Relationer
    remember_tokens: Mapped[list[RememberToken]] = relationship(back_populates="user")
    groups_created: Mapped[list[Group]] = relationship(back_populates="author", foreign_keys="Group.author_id")
    teams_created: Mapped[list[Team]] = relationship(back_populates="author", foreign_keys="Team.author_id")
    questions_created: Mapped[list[Question]] = relationship(back_populates="author", foreign_keys="Question.author_id")
    templates_created: Mapped[list[Template]] = relationship(back_populates="author", foreign_keys="Template.author_id")
    assignments_created: Mapped[list[Assignment]] = relationship(back_populates="author", foreign_keys="Assignment.author_id")
    responses_created: Mapped[list[Response]] = relationship(back_populates="author", foreign_keys="Response.author_id")
    # Arv
    __mapper_args__ = {
        "polymorphic_identity": "user",
        "polymorphic_on": type}

class Teacher(User):
    __tablename__ = "teachers"
    id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    # Arv
    __mapper_args__ = {"polymorphic_identity": "teacher"}

class Student(User):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    group_id: Mapped[int|None] = mapped_column(ForeignKey("groups.id"), nullable=True)  
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Relationer
    group: Mapped["Group|None"] = relationship(back_populates="students", foreign_keys=[group_id])  
    teams: Mapped[list[Team]] = relationship(secondary=student_team_link, back_populates="students")
    responses: Mapped[list[Response]] = relationship(back_populates="student", foreign_keys="Response.student_id")
    assignments: Mapped[list[Assignment]] = relationship(secondary=student_assignment_link, back_populates="students")
    point_transactions: Mapped[list[PointTransaction]] = relationship(back_populates="student",cascade="all, delete-orphan")
    badges: Mapped[list[Badge]] = relationship(secondary=student_badge_link, back_populates="students", passive_deletes=True)
    # Arv
    __mapper_args__ = {"polymorphic_identity": "student"}
    __table_args__ = (UniqueConstraint("group_id", "name"),)

    @property
    def active_assignments(self):
        now = utc_now()
        return [
            assignment
            for assignment in self.assignments
            if (
                assignment.start_time is not None
                and utcify(assignment.start_time) <= now
                and (
                    assignment.end_time is None
                    or utcify(assignment.end_time) >= now
                )
            )
        ]

    @property
    def total_xp(self):
        return sum(p.xp for p in self.point_transactions)

    @property
    def xp_last_week(self):
        limit = datetime.now(timezone.utc)-timedelta(days=7)
        return sum(p.xp for p in self.point_transactions if p.earned_at >= limit)

    @property
    def last_response(self):
        if not self.responses:
            return None
        return max(r.submitted_at for r in self.responses)

# -------------------------------------------------
# GAMIFICATION TABLES
# -------------------------------------------------
class PointTransaction(Base):
    __tablename__ = "point_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    response_id: Mapped[int|None] = mapped_column(ForeignKey("responses.id"), nullable=True)
    xp: Mapped[int] = mapped_column(default=0)
    reason: Mapped[PointType] = mapped_column(Enum(PointType), nullable=False)
    comment: Mapped[str|None] = mapped_column(Text)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    # Relationer
    student: Mapped[Student] = relationship(back_populates="point_transactions")
    response: Mapped[Response|None] = relationship(back_populates="point_transactions")

class Badge(Base):
    __tablename__ = "badges"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str|None] = mapped_column(Text)
    icon: Mapped[str|None] = mapped_column(String(100))
    xp_reward: Mapped[int] = mapped_column(default=0)
    #Relationer
    students: Mapped[list["Student"]] = relationship(secondary=student_badge_link, back_populates="badges")

# -------------------------------------------------
# OTHER TABLES
# -------------------------------------------------

class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str | None] = mapped_column(String(120))
    tag_type: Mapped[TagType] = mapped_column(Enum(TagType), nullable=False)
    # Relationer
    questions: Mapped[list["Question"]] = relationship(secondary=question_tag_link, back_populates="tags")
    media: Mapped[list["Media"]] = relationship(secondary=media_tag_link, back_populates="tags")

class Choice(Base): 
    __tablename__ = 'choices'
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey('questions.id'))
    text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(default=False)
    # Relationer
    question: Mapped["Question"] = relationship(back_populates="choices")

class RememberToken(Base):
    __tablename__ = "remember_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"),index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ip_address: Mapped[str | None] = mapped_column(String(100))
    device: Mapped[str | None] = mapped_column(String(300))
    # Relationer
    user: Mapped[User] = relationship(back_populates="remember_tokens")

class Media(Base):
    __tablename__ = "media"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    filepath: Mapped[str] = mapped_column(String(500), nullable=False)
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType))
    mime_type: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int | None] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    # Relationer
    questions: Mapped[list[Question]] = relationship(secondary=question_media_link, back_populates="media")
    responses: Mapped[list[Response]] = relationship(secondary=response_media_link, back_populates="media")
    tags: Mapped[list["Tag"]] = relationship(secondary=media_tag_link, back_populates="media")