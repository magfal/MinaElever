# app/base.py
#
# Gemensam basklass för alla SQLAlchemy-modeller.
#
# SQLAlchemy 2.0 använder DeclarativeBase som grund
# för moderna ORM-modeller med type hints (Mapped, mapped_column).
#
# Alla modeller i app/models.py ärver indirekt från denna klass
# genom db = SQLAlchemy(model_class=Base) i extensions.py.
#
# Håll denna fil minimal. Den ska bara definiera ORM-basens
# gemensamma funktionalitet.
#

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass