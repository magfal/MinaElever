
import enum
from datetime import datetime, timezone
from typing import List, Optional
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Table, String, Integer, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# 1. Definiera en bas-klass
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# 2.  Modeller för tabellerna

class Subject(db.Model):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    # Relationer
    questions: Mapped[List["Question"]] = relationship(back_populates="subject")

class Group(db.Model):
    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    # Relationer
    students: Mapped[List["Student"]] = relationship(back_populates="group")
    assignments: Mapped[List["Assignment"]] = relationship(back_populates="group")

question_tag_association = Table(
    "question_tag",
    Base.metadata,
    Column("question_id", ForeignKey("questions.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)

class QuestionType(enum.Enum):
    TEXT = "text"
    SLIDER = "slider"
    MULTIPLE_CHOICE = "multiple_choice"
    CSV_IMPORT = "csv_import"
    OBSERVATION = "observation"

class Question(db.Model):
    __tablename__ = 'questions'
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey('subjects.id'))
    prompt: Mapped[str] = mapped_column(Text, unique=True)
    question_type: Mapped[QuestionType] = mapped_column(default=QuestionType.TEXT)
    tags: Mapped[Optional[dict]] = mapped_column(JSON)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))    
    # Relationer
    choices: Mapped[list["Choice"]] = relationship(back_populates="question")
    subject: Mapped["Subject"] = relationship(back_populates="questions")
    tags: Mapped[List["Tag"]] = relationship(secondary=question_tag_association, back_populates="questions")

class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    # Relationer
    questions: Mapped[List["Question"]] = relationship(secondary=question_tag_association, back_populates="tags")

class Student(db.Model):
    __tablename__ = "students"
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    login_code: Mapped[str] = mapped_column(String(20), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    # Relationer
    group: Mapped["Group"] = relationship(back_populates="students")
    responses: Mapped[List["Response"]] = relationship(back_populates="student")
    # Denna regel säger att kombinationen (namn + grupp_id) måste vara unik.
    __table_args__ = (UniqueConstraint('name', 'group_id', name='_name_group_uc'),)

class Choice(db.Model):
    __tablename__ = 'choices'
    question_id: Mapped[int] = mapped_column(ForeignKey('questions.id'))    
    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(String(200))
    is_correct: Mapped[bool] = mapped_column(default=False)
    # Relationer
    question: Mapped["Question"] = relationship(back_populates="choices")

class Assignment(db.Model):
    __tablename__ = "assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime)  
    # Relationer
    group: Mapped["Group"] = relationship(back_populates="assignments")
    responses: Mapped[List["Response"]] = relationship(back_populates="assignment")

class Response(db.Model):
    __tablename__ = "responses"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"))
    choice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("choices.id"))
    text_answer: Mapped[Optional[str]] = mapped_column(Text)
    slider_value: Mapped[Optional[int]] = mapped_column(Integer)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)
    is_private: Mapped[bool] = mapped_column(default=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address: Mapped[Optional[str]] = mapped_column(String(100))
    device: Mapped[Optional[str]] = mapped_column(String(300))
    # Relationer
    student: Mapped["Student"] = relationship(back_populates="responses")
    assignment: Mapped["Assignment"] = relationship(back_populates="responses")