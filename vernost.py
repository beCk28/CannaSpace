import os
import qrcode
from io import BytesIO
import base64
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, g
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

app = Flask(__name__)

# Určíme cestu k databázovému souboru ve stejné složce jako skript
basedir = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(basedir, "vernost.db")
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base = declarative_base()

# Konfigurace relace (session)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --------- Tabulka zákazníků ---------
class Zakaznik(Base):
    __tablename__ = 'zakaznici'
    id = Column(Integer, primary_key=True, autoincrement=True)
    jmeno = Column(String)
    prijmeni = Column(String)
    email = Column(String)
    telefon = Column(String)
    typ_odmeny = Column(String)
    hodnota_odmeny = Column(Float)
    celkove_utraceno = Column(Float, default=0.0)
    datum_pridani = Column(DateTime, default=datetime.now)
    nakupy = relationship("Nakup", back_populates="zakaznik", cascade="all, delete-orphan")

# --------- Tabulka nákupů ---------
class Nakup(Base):
    __tablename__ = 'nakupy'
    id = Column(Integer, primary_key=True, autoincrement=True)
    zakaznik_id = Column(Integer, ForeignKey("zakaznici.id"))
    castka = Column(Float)
    odmena = Column(Float)
    datum = Column(DateTime, default=datetime.now)
    zakaznik = relationship("Zakaznik", back_populates="nakupy")

Base.metadata.create_all(engine)

# --------- Správa relací pro každý požadavek ---------
def get_db_session():
    """Získá databázovou relaci pro aktuální požadavek."""
    if 'db' not in g:
        g.db = SessionLocal()
    return g.db

@app.teardown_appcontext
def close_db_session(exception):
    """Automaticky uzavře databázovou relaci po každém požadavku."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --------- HTML šablony pro interní rozhraní ---------
TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<title>CannaSpace VIP</title>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
<style>
body { font-family: 'Roboto', sans-serif; background:#f5f0f7; color:#333; margin:0; padding:0; }
header { background: linear-gradient(90deg, #6c4298, #8a63b0); padding:25px; text-align:center; font-size:32px; font-weight:700; color:white; }
.logo-container { text-align: center; padding: 20px 0; }
.img-logo { max-width: 150px; height: auto; }
.container { width:90%; margin:20px auto; }
section { background:white; padding:20px; margin-bottom:20px; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1); }
h2 { color:#6c4298; margin-bottom:15px; }
table { width:100%; border-collapse:collapse; margin-top:15px; }
th, td { padding:12px; border-bottom:1px solid #ddd; text-align:left; }
th { background:#efeaf5; font-weight:500; }
tr:hover { background:#f5f0f7; }
input, select { padding:8px; margin-right:6px; border-radius:6px; border:1px solid #ccc; }
button { padding:8px 12px; border:none; border-radius:66px; background:#6c4298; color:white; cursor:pointer; transition:0.2s; }
button:hover { background:#5a3780; }
a { text-decoration:none; color:#6c4298; }
.qr-button { margin-top: 10px; }
</style>
</head>
<body>
<header>CannaSpace VIP</header>
<div class="logo-container">
<img srcset="https://cannaspace.s28.cdn-upgates.com/_cache/a/2/a2a6826dd7fd9b73163fdef2a2c557a2-cs-logo-2024.png 1x, https://cannaspace.s28.cdn-upgates.com/_cache/9/f/9ff50bc119e48a50f978fcd4100958bf-cs-logo-2024.png 2x" src="https://cannaspace.s28.cdn-upgates.com/_cache/a/2/a2a6826dd7fd9b73163fdef2a2c557a2-cs-logo-2024.png" width="304" height="77" class="img-fluid-2 img-logo" alt="CannaSpace VIP" title="CannaSpace VIP">
</div>
<div class="container">

<section>
<h2>Přidat zákazníka (pro personál)</h2>
<form method="post" action="/add">
<input type="text" name="jmeno" placeholder="Jméno" required>
<input type="text" name="prijmeni" placeholder="Příjmení" required>
<input type="text" name="email" placeholder="Email" required>
<input type="text" name="telefon" placeholder="Telefon" required>
<select name="typ_odmeny">
  <option value="Sleva">Sleva</option>
  <option value="Cashback">Cashback</option>
</select>
<input type="number" name="hodnota_odmeny" placeholder="Hodnota %" step="0.1" required>
<button type="submit">Přidat</button>
</form>
<a href="/qrcode"><button class="qr-button">Zobrazit QR kód pro registraci</button></a>
</section>

<section>
<h2>Seznam zákazníků</h2>
<table>
<tr>
<th>#</th><th>ID</th><th>Jméno</th><th>Příjmení</th><th>Email</th><th>Telefon</th>
<th>Typ odměny</th><th>Hodnota %</th><th>Celkové utraceno</th><th>Nasbíraná odměna</th><th>Datum přidání</th><th>Akce</th>
</tr>
{% for z in zakaznici %}
<tr>
<td>{{ loop.index }}</td>
<td>{{ z.id }}</td>
<td>{{ z.jmeno }}</td>
<td>{{ z.prijmeni }}</td>
<td>{{ z.email }}</td>
<td>{{ z.telefon }}</td>
<td>{{ z.typ_odmeny }}</td>
<td>{{ z.hodnota_odmeny }}</td>
<td>{{ "{:,.0f}".format(z.celkove_utraceno).replace(",", " ") }} Kč</td>
<td>{{ "{:,.0f}".format(z.nasbirana_odmena).replace(",", " ") }} Kč</td>
<td>{{ z.datum_pridani.strftime('%d.%m.%Y') }}</td>
<td>
<form method="post" action="/delete/{{ z.id }}" style="display:inline"><button type="submit">Smazat</button></form>
<form method="get" action="/detail/{{ z.id }}" style="display:inline"><button type="submit">Detail</button></form>
</td>
</tr>
{% endfor %}
</table>
</section>

</div>
</body>
</html>
"""

DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<title>Detail zákazníka - CannaSpace VIP</title>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
<style>
body { font-family: 'Roboto', sans-serif; background:#f5f0f7; color:#333; margin:0; padding:0; }
header { background:#6c4298; color:white; text-align:center; padding:20px; font-size:26px; font-weight:700; }
.logo-container { text-align: center; padding: 20px 0; }
.img-logo { max-width: 150px; height: auto; }
.container { width:90%; margin:20px auto; }
section { background:white; padding:20px; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1); margin-bottom:20px; }
table { width:100%; border-collapse:collapse; margin-top:15px; }
th, td { padding:12px; border-bottom:1px solid #ddd; text-align:left; }
th { background:#efeaf5; font-weight:500; }
tr:hover { background:#f5f0f7; }
input { padding:8px; margin-right:6px; border-radius:6px; border:1px solid #ccc; }
button { padding:8px 12px; border:none; border-radius:6px; background:#6c4298; color:white; cursor:pointer; transition:0.2s; }
button:hover { background:#5a3780; }
a { text-decoration:none; color:#6c4298; }
.warning-box {
    background-color: #ffe6e6;
    border: 2px solid #ff6666;
    color: #cc0000;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;
    text-align: center;
    font-weight: bold;
    animation: blink 1s step-start infinite;
}
@keyframes blink {
    50% { opacity: 0; }
}
</style>
</head>
<body>
<header>Detail zákazníka - CannaSpace VIP</header>
<div class="logo-container">
<img srcset="https://cannaspace.s28.cdn-upgates.com/_cache/a/2/a2a6826dd7fd9b73163fdef2a2c557a2-cs-logo-2024.png 1x, https://cannaspace.s28.cdn-upgates.com/_cache/9/f/9ff50bc119e48a50f978fcd4100958bf-cs-logo-2024.png 2x" src="https://cannaspace.s28.cdn-upgates.com/_cache/a/2/a2a6826dd7fd9b73163fdef2a2c557a2-cs-logo-2024.png" width="304" height="77" class="img-fluid-2 img-logo" alt="CannaSpace VIP" title="CannaSpace VIP">
</div>
<div class="container">

{% if zakaznik.typ_odmeny == 'Cashback' and zakaznik.nasbirana_odmena >= 500 %}
<div class="warning-box">
    Pozor! Zákazník má nasbíranou odměnu nad 500 Kč a může ji využít!
</div>
{% endif %}

<section>
<h2>{{ zakaznik.jmeno }} {{ zakaznik.prijmeni }}</h2>
<p>Email: {{ zakaznik.email }} | Telefon: {{ zakaznik.telefon }}</p>
<p>Typ odměny: {{ zakaznik.typ_odmeny }} | Hodnota %: {{ zakaznik.hodnota_odmeny }}</p>
<p>Celkové utraceno: {{ "{:,.0f}".format(zakaznik.celkove_utraceno).replace(",", " ") }} Kč</p>
<p>Celková nasbíraná odměna: {{ "{:,.0f}".format(zakaznik.nasbirana_odmena).replace(",", " ") }} Kč</p>
<p><a href="/edit/{{ zakaznik.id }}"><button>Upravit údaje</button></a></p>
</section>

<section>
<h2>Přidat nákup</h2>
<form method="post" action="/add_nakup/{{ zakaznik.id }}">
<input type="number" name="castka" placeholder="Částka nákupu" step="0.01" required>
<input type="number" name="vyuzita_odmena" placeholder="Použitá odměna (Kč)" step="0.01">
<button type="submit">Přidat nákup</button>
</form>
</section>

<section>
<h2>Historie nákupů</h2>
<table>
<tr><th>#</th><th>Částka</th><th>Odměna</th><th>Datum</th><th>Akce</th></tr>
{% for n in zakaznik.nakupy %}
<tr>
<td>{{ loop.index }}</td>
<td>{{ n.castka }}</td>
<td>{{ n.odmena }}</td>
<td>{{ n.datum.strftime('%d.%m.%Y %H:%M') }}</td>
<td>
<form method="post" action="/delete_odmena/{{ n.id }}" style="display:inline"><button type="submit">Smazat</button></form>
<form method="get" action="/edit_castka/{{ n.id }}" style="display:inline"><button type="submit">Upravit</button></form>
</td>
</tr>
{% endfor %}
</table>
</section>

<p><a href="/">Zpět na seznam</a></p>
</div>
</body>
</html>
"""

# Šablona pro úpravu částky nákupu
EDIT_CASTKA_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <title>Upravit částku nákupu - CannaSpace VIP</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
    body { font-family: 'Roboto', sans-serif; background:#f5f0f7; color:#333; margin:0; padding:0; text-align:center; }
    header { background:#6c4298; color:white; padding:20px; font-size:26px; font-weight:700; }
    .logo-container { text-align: center; padding: 20px 0; }
    .img-logo { max-width: 150px; height: auto; }
    .container { width:90%; margin:20px auto; padding:20px; background:white; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1); }
    h1 { color:#6c4298; }
    input, button { margin: 8px 0; padding: 10px; width: 80%; max-width: 400px; border-radius: 6px; border: 1px solid #ccc; box-sizing: border-box; }
    button { background:#6c4298; color:white; border:none; cursor:pointer; }
    button:hover { background:#5a3780; }
    a { color:#6c4298; text-decoration:none; }
    </style>
</head>
<body>
    <header>Úprava nákupu</header>
    <div class="logo-container">
    <img srcset="https://cannaspace.s28.cdn-upgates.com/_cache/a/2/a2a6826dd7fd9b73163fdef2a2c557a2-cs-logo-2024.png 1x, https://cannaspace.s28.cdn-upgates.com/_cache/9/f/9ff50bc119e48a50f978fcd4100958bf-cs-logo-2024.png 2x" src="https://cannaspace.s28.cdn-upgates.com/_cache/a/2/a2a6826dd7fd9b73163fdef2a2c557a2-cs-logo-2024.png" width="304" height="77" class="img-fluid-2 img-logo" alt="CannaSpace VIP" title="CannaSpace VIP">
    </div>
    <div class="container">
        <h1>Upravit částku nákupu {{ nakup.id }}</h1>
        <form method="post" action="/update_castka/{{ nakup.id }}">
            <p>Původní částka: {{ nakup.castka }}</p>
            <input type="number" name="castka" value="{{ nakup.castka }}" step="0.01" required><br>
            <button type="submit">Uložit změnu</button>
        </form>
        <p><a href="/detail/{{ nakup.zakaznik_id }}">Zpět na detail zákazníka</a></p>
    </div>
</body>
</html>
"""

# Šablona pro úpravu zákazníka
EDIT_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <title>Upravit zákazníka - CannaSpace VIP</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
    body { font-family: 'Roboto', sans-serif; background:#f5f0f7; color:#333; margin:0; padding:0; text-align:center; }
    header { background:#6c4298; color:white; padding:20px; font-size:26px; font-weight:700; }
    .logo-container { text-align: center; padding: 20px 0; }
    .img-logo { max-width: 150px; height: auto; }
    .container { width:90%; margin:20px auto; padding:20px; background:white; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1); }
    h1 { color:#6c4298; }
    input, button { margin: 8px 0; padding: 10px; width: 80%; max-width: 400px; border-radius: 6px; border: 1px solid #ccc; box-sizing: border-box; }
    button { background:#6c4298; color:white; border:none; cursor:pointer; }
    button:hover { background:#5a3780; }
    a { color:#6c4298; text-decoration:none; }
    </style>
</head>
<body>
    <header>Úprava údajů</header>
    <div class="logo-container">
    <img srcset="https://cannaspace.s28.cdn-upgates.com/_cache/a/2/a2a6826dd7fd9b73163fdef2a2c557a2-cs-logo-2024.png 1x, https://cannaspace.s28.cdn-upgates.com/_cache/9/f/9ff50bc119e48a50f978fcd4100958bf-cs-logo-2024.png 2x" src="https://cannaspace.s28.cdn-upgates.com/_cache/a/2/a2a6826dd7fd9b73163fdef2a2c557a2-cs-logo-2024.png" width="304" height="77" class="img-fluid-2 img-logo" alt="CannaSpace VIP" title="CannaSpace VIP">
    </div>
    <div class="container">
        <h1>Upravit údaje pro {{ zakaznik.jmeno }} {{ zakaznik.prijmeni }}</h1>
        <form method="post" action="/update/{{ zakaznik.id }}">
            <input type="text" name="jmeno" value="{{ zakaznik.jmeno }}" required><br>
            <input type="text" name="prijmeni" value="{{ zakaznik.prijmeni }}" required><br>
            <input type="email" name="email" value="{{ zakaznik.email }}" required><br>
            <input type="tel" name="telefon" value="{{ zakaznik.telefon }}" required><br>
            <button type="submit">Uložit změny</button>
        </form>
        <p><a href="/detail/{{ zakaznik.id }}">Zpět na detail zákazníka</a></p>
    </div>
</body>
</html>
"""

# --------- HTML šablony pro zákazníky ---------
REGISTER_FORM_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <title>Registrace zákazníka - CannaSpace VIP</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
    body { font-family: 'Roboto', sans-serif; background:#f5f0f7; color:#333; margin:0; padding:0; text-align:center; }
    header { background:#6c4298; color:white; padding:20px; font-size:26px; font-weight:700; }
    .logo-container { text-align: center; padding: 20px 0; }
    .img-logo { max-width: 150px; height: auto; }
    .container { width:90%; margin:20px auto; padding:20px; background:white; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1); }
    h1 { color:#6c4298; }
    input, button { margin: 8px 0; padding: 10px; width: 80%; max-width: 400px; border-radius: 6px; border: 1px solid #ccc; box-sizing: border-box; }
    button { background:#6c4298; color:white; border:none; cursor:pointer; }
    button:hover { background:#5a3780; }
    a { color:#6c4298; text-decoration:none; }
    </style>
</head>
<body>
    <header>Registrace - CannaSpace VIP</header>
    <div class="logo-container">
    <img srcset="https://cannaspace.s28.cdn-upgates.com/_cache/a/2/a2a6826dd7fd9b73163fdef2a2c557a2-cs-logo-2024.png 1x, https://cannaspace.s28.cdn-upgates.com/_cache/9/f/9ff50bc119e48a50f978fcd4100958bf-cs-logo-2024.png 2x" src="https://cannaspace.s28.cdn-upgates.com/_cache/a/2/a2a6826dd7fd9b73163fdef2a2c557a2-cs-logo-2024.png" width="304" height="77" class="img-fluid-2 img-logo" alt="CannaSpace VIP" title="CannaSpace VIP">
    </div>
    <div class="container">
        <h1>Registrační formulář</h1>
        <form method="post" action="/register">
            <input type="text" name="jmeno" placeholder="Jméno" required><br>
            <input type="text" name="prijmeni" placeholder="Příjmení" required><br>
            <input type="text" name="email" placeholder="Email" required><br>
            <input type="text" name="telefon" placeholder="Telefon" required><br>
            <button type="submit">Registrovat</button>
        </form>
    </div>
</body>
</html>
"""

CONFIRMATION_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <title>Registrace úspěšná - CannaSpace VIP</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
    body { font-family: 'Roboto', sans-serif; background:#f5f0f7; color:#333; margin:0; padding:0; text-align:center; }
    header { background:#6c4298; color:white; padding:20px; font-size:26px; font-weight:700; }
    .logo-container { text-align: center; padding: 20px 0; }
    .img-logo { max-width: 150px; height: auto; }
    .container { width:90%; margin:20px auto; padding:20px; background:white; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1); }
    h1 { color:#6c4298; }
    </style>
</head>
<body>
    <header>Registrace úspěšná</header>
    <div class="logo-container">
    <img srcset="https://cannaspace.s28.cdn-upgates.com/_cache/a/2/a2a6826dd7fd9b73163fdef2a2c557a2-cs-logo-2024.png 1x, https://cannaspace.s28.cdn-upgates.com/_cache/9/f/9ff50bc119e48a50f978fcd4100958bf-cs-logo-2024.png 2x" src="https://cannaspace.s28.cdn-upgates.com/_cache/a/2/a2a6826dd7fd9b73163fdef2a2c557a2-cs-logo-2024.png" width="304" height="77" class="img-fluid-2 img-logo" alt="CannaSpace VIP" title="CannaSpace VIP">
    </div>
    <div class="container">
        <h1>Registrace proběhla v pořádku!</h1>
        <p>Vítejte v našem věrnostním programu.</p>
    </div>
</body>
</html>
"""

QR_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <title>QR Kód pro registraci - CannaSpace VIP</title>
    <style>
    body { font-family: 'Roboto', sans-serif; background:#f5f0f7; color:#333; text-align:center; }
    h1 { color:#6c4298; }
    .logo-container { text-align: center; padding: 20px 0; }
    .img-logo { max-width: 150px; height: auto; }
    .qr-code { margin-top: 20px; max-width: 300px; }
    </style>
</head>
<body>
    <div class="logo-container">
    <img srcset="https://cannaspace.s28.cdn-upgates.com/_cache/a/2/a2a6826dd7fd9b73163fdef2a2c557a2-cs-logo-2024.png 1x, https://cannaspace.s28.cdn-upgates.com/_cache/9/f/9ff50bc119e48a50f978fcd4100958bf-cs-logo-2024.png 2x" src="https://cannaspace.s28.cdn-upgates.com/_cache/a/2/a2a6826dd7fd9b73163fdef2a2c557a2-cs-logo-2024.png" width="304" height="77" class="img-fluid-2 img-logo" alt="CannaSpace VIP" title="CannaSpace VIP">
    </div>
    <h1>Naskenujte pro registraci</h1>
    <img class="qr-code" src="data:image/png;base64,{{ img_str }}" alt="QR Kód pro registraci">
    <p>Pro registraci naskenujte QR kód.</p>
    <p><a href="/">Zpět na hlavní stránku</a></p>
</body>
</html>
"""

# --------- ROUTES ---------
@app.route("/")
def index():
    session = get_db_session()
    zakaznici = session.query(Zakaznik).all()
    for z in zakaznici:
        z.nasbirana_odmena = sum(n.odmena for n in z.nakupy)
    return render_template_string(TEMPLATE, zakaznici=zakaznici)

@app.route("/add", methods=["POST"])
def add():
    session = get_db_session()
    z = Zakaznik(
        jmeno=request.form['jmeno'],
        prijmeni=request.form['prijmeni'],
        email=request.form['email'],
        telefon=request.form['telefon'],
        typ_odmeny=request.form['typ_odmeny'],
        hodnota_odmeny=float(request.form['hodnota_odmeny'])
    )
    session.add(z)
    session.commit()
    return redirect("/")

@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    session = get_db_session()
    zakaznik = session.query(Zakaznik).get(id)
    if zakaznik:
        session.delete(zakaznik)
        session.commit()
    return redirect("/")

@app.route("/detail/<int:id>")
def detail(id):
    session = get_db_session()
    zakaznik = session.query(Zakaznik).get(id)
    zakaznik.nasbirana_odmena = sum(n.odmena for n in zakaznik.nakupy)
    return render_template_string(DETAIL_TEMPLATE, zakaznik=zakaznik)

@app.route("/add_nakup/<int:id>", methods=["POST"])
def add_nakup(id):
    session = get_db_session()
    zakaznik = session.query(Zakaznik).get(id)
    castka = float(request.form['castka'])
    vyuzita_odmena = float(request.form.get('vyuzita_odmena', 0))

    # Odečteme použitou odměnu z celkové nasbírané odměny
    if vyuzita_odmena > 0 and vyuzita_odmena <= zakaznik.nasbirana_odmena:
        zakaznik.nasbirana_odmena -= vyuzita_odmena
    
    # Vypočítáme novou odměnu na základě nákupu (pokud to není cashback)
    odmena = 0
    if zakaznik.typ_odmeny == 'Cashback':
        odmena = castka * zakaznik.hodnota_odmeny / 100
        zakaznik.celkove_utraceno += castka
    
    # Přičteme nově získanou odměnu k nasbírané
    zakaznik.nasbirana_odmena += odmena

    n = Nakup(zakaznik=zakaznik, castka=castka, odmena=odmena - vyuzita_odmena) # Ukládáme čistý zisk/ztrátu odměny
    session.add(n)
    session.commit()
    return redirect(f"/detail/{id}")

@app.route("/edit/<int:id>", methods=["GET"])
def edit_customer(id):
    session = get_db_session()
    zakaznik = session.query(Zakaznik).get(id)
    return render_template_string(EDIT_TEMPLATE, zakaznik=zakaznik)

@app.route("/update/<int:id>", methods=["POST"])
def update_customer(id):
    session = get_db_session()
    zakaznik = session.query(Zakaznik).get(id)
    if zakaznik:
        zakaznik.jmeno = request.form['jmeno']
        zakaznik.prijmeni = request.form['prijmeni']
        zakaznik.email = request.form['email']
        zakaznik.telefon = request.form['telefon']
        session.commit()
    return redirect(f"/detail/{id}")

@app.route("/edit_castka/<int:nakup_id>", methods=["GET"])
def edit_castka(nakup_id):
    session = get_db_session()
    nakup = session.query(Nakup).get(nakup_id)
    return render_template_string(EDIT_CASTKA_TEMPLATE, nakup=nakup)

@app.route("/update_castka/<int:nakup_id>", methods=["POST"])
def update_castka(nakup_id):
    session = get_db_session()
    nakup = session.query(Nakup).get(nakup_id)
    stara_castka = nakup.castka
    nova_castka = float(request.form['castka'])
    
    nakup.zakaznik.celkove_utraceno -= stara_castka
    nakup.zakaznik.celkove_utraceno += nova_castka
    
    nakup.castka = nova_castka
    nakup.odmena = nova_castka * nakup.zakaznik.hodnota_odmeny / 100
    
    session.commit()
    return redirect(f"/detail/{nakup.zakaznik_id}")

@app.route("/delete_odmena/<int:nakup_id>", methods=["POST"])
def delete_odmena(nakup_id):
    session = get_db_session()
    nakup = session.query(Nakup).get(nakup_id)
    if nakup.odmena > 0:
        nakup.odmena = 0.0
        session.commit()
    return redirect(f"/detail/{nakup.zakaznik_id}")

@app.route("/qrcode")
def show_qrcode():
    # Použijeme request.host_url, aby URL fungovala i po nasazení na Render
    data = f"{request.host_url}register"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#6c4298", back_color="#f5f0f7")

    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    return render_template_string(QR_PAGE_TEMPLATE, img_str=img_str)

@app.route("/register", methods=["GET", "POST"])
def register_customer():
    session = get_db_session()
    if request.method == "POST":
        z = Zakaznik(
            jmeno=request.form['jmeno'],
            prijmeni=request.form['prijmeni'],
            email=request.form['email'],
            telefon=request.form['telefon'],
            typ_odmeny="Cashback",
            hodnota_odmeny=5.0
        )
        session.add(z)
        session.commit()
        return render_template_string(CONFIRMATION_TEMPLATE)
    else:
        return render_template_string(REGISTER_FORM_TEMPLATE)

if __name__ == "__main__":
    app.run(debug=True)

