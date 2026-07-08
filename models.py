from __future__ import annotations
import enum
from datetime import datetime, timezone
from typing import List, Optional
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON, Column, Table, String, Integer, Enum, Boolean, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# -------------------------------------------------
# BASE
# -------------------------------------------------

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# -------------------------------------------------
# ENUMS
# -------------------------------------------------

class InputType(enum.Enum):
    TEXT = "Text"
    NUMBER = "Tal"
    BOOLEAN = "Boolean"
    DATE = "Datum"
    FORMULA = "Formel"
    SLIDER = "Slider"
    SINGLE_CHOICE = "Enkelvalsvar"
    MULTIPLE_CHOICE = "Flervalssvar"
    FILE_UPLOAD = "Filuppladdning"
    CSV_IMPORT = "CSV import"

class TagType(enum.Enum):
    SUBJECT = "Ämne"
    AREA = "Område"
    DECK = "Kortlek"
    GENERAL = "Generell"

class MediaType(enum.Enum):
    IMAGE = "Bild"
    VIDEO = "Video"
    AUDIO = "Ljud"
    DOCUMENT = "Text"

class TemplateType(enum.Enum):
    TASK = "Uppgift"            # Uppgift elev gör under lektion elle hemma (med hjälpmedel)
    TEST = "Test"               # Uppgift elev gör i skolan utan hjälp
    DIAGNOSTIC = "Diagnos"      # Uppgift eleven gör i skolan men som inte bedöms
    FLASHCARD = "Flashcard"     # Uppgift elev får att öva på
    REFLECTION = "Reflexion"    # Elevreflexion eller utvärdering 
    OBSERVATION = "Observation" # Observation lärare gör av elevs förmåga
    NOTE = "Notering"           # Notering av elevs beteende som lärare gör

class PointType(enum.Enum):
    ASSIGNMENT_SUBMITTED = "Assignment submitted"
    EARLY_SUBMISSION = "Early submission"
    CORRECT_ANSWER = "Correct answer"
    FLASHCARD = "Flashcard practice"
    STREAK_BONUS = "Streak bonus"
    TEACHER_REWARD = "Teacher reward"
    MANUAL_ADJUSTMENT = "Manual adjustment"
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

student_assignment_link = Table(
    "student_assignment_link",
    Base.metadata,
    Column("assignment_id", ForeignKey("assignments.id"), primary_key=True),
    Column("student_id", ForeignKey("students.id"), primary_key=True),
)

response_choice_link = Table(
    "response_choice_link",
    Base.metadata,
    Column("response_id", ForeignKey("responses.id"), primary_key=True),
    Column("choice_id", ForeignKey("choices.id"), primary_key=True)
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
    points: Mapped[Optional[int]] = mapped_column(Integer)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)
    # Relationer
    template: Mapped["Template"] = relationship(back_populates="question_links")
    question: Mapped["Question"] = relationship(back_populates="question_links")

# ------------------------------------------------------
# CORE TABLES (QUESTION, TEMPLATE, ASSIGNMENT, RESPONSE
# ------------------------------------------------------

class Question(Base):
    __tablename__ = 'questions'
    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    input_type: Mapped[InputType] = mapped_column(Enum(InputType), default=InputType.TEXT)
    expected_answer: Mapped[Optional[dict]] = mapped_column(JSON)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))    
    # Relationer
    choices: Mapped[List["Choice"]] = relationship(back_populates="question", cascade="all, delete-orphan")
    question_links: Mapped[List["QuestionTemplateLink"]] = relationship(back_populates="question")
    responses: Mapped[List["Response"]] = relationship(back_populates="question")
    tags: Mapped[List["Tag"]] = relationship(secondary=question_tag_link, back_populates="questions")
    media: Mapped[list["Media"]] = relationship(secondary=question_media_link, back_populates="questions")

class Template(Base):
    __tablename__ = "templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[Optional[str]] = mapped_column(Text)
    template_type: Mapped[TemplateType] = mapped_column(Enum(TemplateType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Relationer
    question_links: Mapped[List["QuestionTemplateLink"]] = relationship(back_populates="template", cascade="all, delete-orphan")
    assignments: Mapped[List["Assignment"]] = relationship(back_populates="template")
    responses: Mapped[List["Response"]] = relationship(back_populates="template")

class Assignment(Base):
    __tablename__ = "assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), index=True)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Relationer
    template: Mapped["Template"] = relationship(back_populates="assignments")
    students: Mapped[List["Student"]] = relationship(secondary=student_assignment_link, back_populates="assignments")

class Response(Base):
    __tablename__ = "responses"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[Optional[int]] = mapped_column(ForeignKey("students.id"), nullable=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"),index=True)
    text_ans: Mapped[Optional[str]] = mapped_column(Text)
    numeric_ans: Mapped[Optional[int]] = mapped_column(Integer)
    boolean_ans: Mapped[Optional[bool]] = mapped_column(Boolean)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)
    is_private: Mapped[bool] = mapped_column(default=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ip_address: Mapped[Optional[str]] = mapped_column(String(100))
    device: Mapped[Optional[str]] = mapped_column(String(300))
    # Relationer
    template: Mapped["Template"] = relationship(back_populates="responses")
    question: Mapped["Question"] = relationship(back_populates="responses")
    student: Mapped["Student"] = relationship(back_populates="responses")
    choices: Mapped[List["Choice"]] = relationship(secondary=response_choice_link, back_populates="responses")
    media: Mapped[list["Media"]] = relationship(secondary=response_media_link, back_populates="responses")
    point_transactions: Mapped[List["PointTransaction"]] = relationship(back_populates="response",cascade="all, delete-orphan")

# -------------------------------------------------
# INDIVIDS
# -------------------------------------------------

class Group(Base):
    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    # Relationer
    students: Mapped[List["Student"]] = relationship(back_populates="group", order_by="Student.name")

class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    name: Mapped[str] = mapped_column(String(120))
    login_code: Mapped[str] = mapped_column(String(20), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    # Relationer
    group: Mapped["Group"] = relationship(back_populates="students")
    responses: Mapped[List["Response"]] = relationship(back_populates="student")
    remember_tokens: Mapped[List["RememberToken"]] = relationship(back_populates="student")
    assignments: Mapped[List["Assignment"]] = relationship(secondary=student_assignment_link, back_populates="students")
    point_transactions: Mapped[List["PointTransaction"]] = relationship(back_populates="student",cascade="all, delete-orphan")
    badges: Mapped[List["Badge"]] = relationship(secondary=student_badge_link, back_populates="students", passive_deletes=True)
    student_progress: Mapped["StudentProgress"] = relationship(
    back_populates="student", uselist=False, cascade="all, delete-orphan")
    # Denna regel säger att kombinationen (namn + grupp_id) måste vara unik.
    __table_args__ = (UniqueConstraint('name', 'group_id', name='_name_group_uc'),)

# -------------------------------------------------
# HELP TABLES
# -------------------------------------------------

class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    tag_type: Mapped[TagType] = mapped_column(Enum(TagType), nullable=False)
    # Relationer
    questions: Mapped[List["Question"]] = relationship(secondary=question_tag_link, back_populates="tags")

class Choice(Base): 
    __tablename__ = 'choices'
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey('questions.id'))
    text: Mapped[str] = mapped_column(String(200))
    is_correct: Mapped[bool] = mapped_column(default=False)
    # Relationer
    question: Mapped["Question"] = relationship(back_populates="choices")
    responses: Mapped[List["Response"]] = relationship(secondary=response_choice_link, back_populates="choices")

class RememberToken(Base):
    __tablename__ = "remember_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"),index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc) )
    # Relationer
    student: Mapped["Student"] = relationship(back_populates="remember_tokens")

class Media(Base):
    __tablename__ = "media"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str]
    filepath: Mapped[str]
    media_type: Mapped[MediaType]
    mime_type: Mapped[str | None]
    size_bytes: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Relationer
    questions: Mapped[list["Question"]] = relationship(secondary=question_media_link, back_populates="media")
    responses: Mapped[list["Response"]] = relationship(secondary=response_media_link, back_populates="media")

class PointTransaction(Base):
    __tablename__ = "point_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    response_id: Mapped[Optional[int]] = mapped_column(ForeignKey("responses.id"), nullable=True)
    xp: Mapped[int] = mapped_column(default=0)
    reason: Mapped[PointType] = mapped_column(Enum(PointType), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Relationer
    student: Mapped["Student"] = relationship(back_populates="point_transactions")
    response: Mapped[Optional["Response"]] = relationship(back_populates="point_transactions")

class StudentProgress(Base):
    __tablename__ = "student_progress"
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), primary_key=True)
    total_xp: Mapped[int] = mapped_column(default=0)
    current_streak: Mapped[int] = mapped_column(default=0)
    longest_streak: Mapped[int] = mapped_column(default=0)
    last_activity: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Relationer
    student: Mapped["Student"] = relationship(back_populates="student_progress")

class Badge(Base):
    __tablename__ = "badges"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon: Mapped[Optional[str]] = mapped_column(String(100))
    xp_reward: Mapped[int] = mapped_column(default=0)
    #Relationer
    students: Mapped[List["Student"]] = relationship(secondary=student_badge_link, back_populates="badges")