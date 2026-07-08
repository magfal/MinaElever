Appen MinaElever är tänkt som ett sätt att samla omdömen om elever på ett samlat ställe. Omdömena kan göras i form av "assignments" som eleverna ser när det loggar in från sin egen enhet, eller "observations" som är lärarens verktyg för att kontinuerligt följa upp elever. Läraren skapar "assignments" och "observations" via routrarna /admins/add_assignment och admin/add_observation Elevernas inloggningen görs första gången med en elevunik kod. Därefter sparas en cookie i elevens browser som gör så att hen loggar in automatiskt nästa gång webbsidan öppnas. Det finns flera olika typer av "assignments" och "observations":

Assignments:
Fritext, slider, flerval (ett rätt svar), flerval (valfritt antal val), flashcard

Observations:
Fritext, slider, flerval (ett rätt svar), flerval (valfritt antal val)

Starta programmet genom att när då är i rätt mapp i terminalen köra 
sass --watch static/scss:static/css --load-path=node_modules/bootstrap/scss --quiet-deps

Öppna sedan en annan terminal och kör app.py
python app.py



För att öppna den globala settings.json:
Tryck Ctrl+Shift+P.
Skriv
Preferences: Open User Settings (JSON)


Flöde:

Question Bank
│
├── Subject
├── Tag
├── Question
└── Choice


Activities
│
├── Assignment
├── Observation
└── (fler typer senare?)


Activity
│
├── består av flera frågor
├── ordning
├── poäng
└── required


Publish
│
└── Publicera aktivitet till grupp(er)


People
│
├── Teacher
├── Group
└── Student


Responses
│
└── Student- och lärarsvar