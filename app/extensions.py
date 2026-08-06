# app/extensions.py
#
# Här skapas Flask-tillägg som används av hela applikationen.
#
# Tillägg ska skapas här utan att kopplas till en specifik Flask-app.
# De kopplas senare i create_app() genom init_app().
#
# Detta gör att applikationen följer Flask-factory-mönstret:
#
#     skapa app
#          |
#          v
#     initiera extensions
#          |
#          v
#     registrera routes
#
# Fördelen är att databasen kan användas i tester,
# flera app-inställningar kan skapas och importproblem undviks.
#

from flask_sqlalchemy import SQLAlchemy
from .base import Base

# SQLAlchemy-instansen som används av alla modeller.
# model_class=Base gör att våra modeller använder
# SQLAlchemy 2.0 DeclarativeBase.

db = SQLAlchemy(model_class=Base)