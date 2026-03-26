from app import app # Importera din Flask-app
from sqlalchemy import select
from models import db, Assignment

# 1. Se till att appen är konfigurerad (pekar på rätt SQLITE/Postgres-fil)
# Om db.init_app(app) redan finns i din app.py räcker det att importera app.

# 2. Skapa kontexten
with app.app_context():
    # 3. Skapa frågan
    query = select(Assignment)

    # 4. Exekvera
    assignments = db.session.scalars(query).all()

    # 5. Printa resultatet
    if not assignments:
        print("Tabellen är tom.")
    else:
        for a in assignments:
            # Eftersom vi är i en kontext kan du även nå relationer:
            print(f"ID: {a.id} | Grupp: {a.group.name} | Fråga: {a.question_id} | Start: {a.start_time} | Slut: {a.end_time}")