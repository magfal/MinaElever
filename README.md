När appen utveckla måstwe sass köras: 
sass --watch static/scss:static/css --load-path=node_modules/bootstrap/scss --quiet-deps

För att installera en sqlite db körs:
flask create-db

Appen startas med:
python run.py

För att öppna den globala settings.json:
Tryck Ctrl+Shift+P.
Skriv
Preferences: Open User Settings (JSON)

app/
│
├── __init__.py
├── base.py
├── config.py
├── extensions.py
├── models.py
│
├── services/
│   ├── __init__.py
│   ├── auth.py
│   ├── htmx.py
│   ├── students.py
│   ├── tags.py
│   └── utils.py
│
├── routes/
    ├── __init__.py.py
    ├── assignments.py
    ├── auth.py
    ├── dashboard.py
    ├── gamification.py
    ├── groups.py
    ├── media.py
    ├── questions.py
    ├── responses.py
    ├── statistics.py
    ├── students.py
    └── templates.py

Appen MinaElever är tänkt som ett sätt att samla omdömen om elever på ett samlat ställe. Omdömena kan göras i form av "assignments" som eleverna ser när det loggar in från sin egen enhet, eller "observations" som är lärarens verktyg för att kontinuerligt följa upp elever. Elevernas inloggningen görs första gången med en elevunik kod. Därefter sparas en cookie i elevens browser som gör så att hen loggar in automatiskt nästa gång webbsidan öppnas. 

TODO:
Först lokalt:
   Installera Alembic.
   Skapa första migrationen.
   Testa att databasen kan byggas från migrationerna.

Sedan HostUp:
   Kontrollera vilken Python-version HostUps Flask/Passenger-miljö erbjuder.
   Skapa Python-applikationen i cPanel.
   Klona GitHub-repot.
   Skapa virtual environment.
   Installera requirements.txt.
   Skapa MySQL-databasen och användaren i cPanel.
   Konfigurera .env på servern, inte i GitHub.
   Kör Alembic mot den nya databasen.
   Konfigurera upload/media-katalogen.
   Starta Flask via Passenger.
   Skapa ett lärarkonto och ett elevkonto.
   Testa det befintliga flödet på riktigt.

Elevvyn
Jag ser framför mig:

Hej Anna!

XP: 320
Nivå: 4
Aktuell streak: 5 dagar

--------------------------------

Mina uppgifter

[Algebra vecka 32]
[Starta]

--------------------------------

Fråga klassen

"Jag förstår inte varför..."

Svar:
Oskar:
"Jag tänkte så här..."

--------------------------------

Min progression

Du har förbättrat:
✓ Algebra
✓ Funktioner

Öva mer:
△ Geometri

