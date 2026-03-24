
from datetime import datetime, timezone
from typing import List, Optional
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime
from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# 1. Definiera en bas-klass (nytt i modern SQLAlchemy)
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# 2. MODELLER

class Group(db.Model):
    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    
    # Relationer
    students: Mapped[List["Student"]] = relationship(back_populates="groups")
    assignments: Mapped[List["Assignment"]] = relationship(back_populates="groups")

class Subject(db.Model):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))

    # Relationer
    questions: Mapped[List["Question"]] = relationship(back_populates="subjects")

class QuestionType(enum.Enum):
    TEXT = "text"
    SLIDER = "slider"
    MULTIPLE_CHOICE = "multiple_choice"
    CSV_IMPORT = "csv_import"
    OBSERVATION = "observation"

class Question(db.Model):
    __tablename__ = 'questions'
    id: Mapped[int] = mapped_column(primary_key=True)
    prompt: Mapped[str] = mapped_column(Text)
    question_type: Mapped[QuestionType] = mapped_column(default=QuestionType.TEXT)
    subject_id: Mapped[int] = mapped_column(ForeignKey('subjects.id'))
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationer
    choices: Mapped[list["Choice"]] = relationship(back_populates="question")
    subject: Mapped["Subject"] = relationship(back_populates="questions")

class Student(db.Model):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    login_code: Mapped[str] = mapped_column(String(20), unique=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationer
    group: Mapped["Group"] = relationship(back_populates="students")
    responses: Mapped[List["Response"]] = relationship(back_populates="student")

class Choice(db.Model):
    __tablename__ = 'choices'
    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(String(200))
    is_correct: Mapped[bool] = mapped_column(default=False)
    question_id: Mapped[int] = mapped_column(ForeignKey('questions.id'))
    
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
    text_answer: Mapped[Optional[str]] = mapped_column(Text)
    slider_value: Mapped[Optional[int]] = mapped_column(Integer)
    choice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("choices.id"))
    is_private: Mapped[bool] = mapped_column(default=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address: Mapped[Optional[str]] = mapped_column(String(100))
    device: Mapped[Optional[str]] = mapped_column(String(300))

    # Relationer
    student: Mapped["Student"] = relationship(back_populates="responses")
    assignment: Mapped["Assignment"] = relationship(back_populates="responses")