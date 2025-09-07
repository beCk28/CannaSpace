import os
from datetime import datetime

from flask import Flask, request, render_template_string, redirect
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

# --- Dynamická konfigurace databáze ---
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///vernost.db")
engine = create_engine(DB_URL)

Session = sessionmaker(bind=engine)
Base = declarative_base()

# --- Modely databáze ---
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

class Nakup(Base):
    __tablename__ = 'nakupy'
    id = Column(Integer, primary_key=True, autoincrement=True)
    zakaznik_id = Column(Integer, ForeignKey("zakaznici.id"))
    castka = Column(Float)
    odmena = Column(Float)
    datum = Column(DateTime, default=datetime.now)
    zakaznik = relationship("Zakaznik", back_populates="nakupy")

Base.metadata.create_all(engine)
app = Flask(__name__)

# --- Správa databázového sezení ---
@app.before_request
def create_session():
    request.session = Session()

@app.teardown_request
def close_session(exception=None):
    request.session.close()

# --- HTML šablony pro obě rozhraní ---
TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>Věrnostní program - Administrace</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f4; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 900px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #5cb85c; }
        h2 { border-bottom: 2px solid #ddd; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #ddd; }
        th { background-color: #5cb85c; color: white; }
        form { margin-top: 20px; }
        input[type="text"], input[type="email"], input[type="tel"], input[type="number"], select {
            width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;
        }
        input[type="submit"] {
            background-color: #5cb85c; color: white; padding: 14px 20px; margin: 8px 0; border: none;
            border-radius: 4px; cursor: pointer; width: 100%; font-size: 16px;
        }
        .blinking {
            animation: blinker 1s linear infinite;
        }
        @keyframes blinker {
            50% { opacity: 0; }
        }
        a { color: #5cb85c; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Věrnostní program - Administrace</h1>
        <h2>Přidat nového zákazníka</h2>
        <form action="/add" method="post">
            <label for="jmeno">Jméno:</label><br>
            <input type="text" id="jmeno" name="jmeno" required><br>
            <label for="prijmeni">Příjmení:</label><br>
            <input type="text" id="prijmeni" name="prijmeni" required><br>
            <label for="email">E-mail:</label><br>
            <input type="email" id="email" name="email"><br>
            <label for="telefon">Telefon:</label><br>
            <input type="tel" id="telefon" name="telefon"><br>
            <label for="typ_odmeny">Typ odměny:</label><br>
            <select id="typ_odmeny" name="typ_odmeny">
                <option value="cashback">Cashback</option>
                <option value="sleva">Sleva</option>
            </select><br>
            <label for="hodnota_odmeny">Hodnota odměny (%):</label><br>
            <input type="number" id="hodnota_odmeny" name="hodnota_odmeny" step="0.1" required><br>
            <input type="submit" value="Přidat zákazníka">
        </form>
        
        <h2>Seznam zákazníků</h2>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Jméno</th>
                    <th>E-mail</th>
                    <th>Celkově utraceno</th>
                    <th>Nasbíraná odměna</th>
                    <th>Datum přidání</th>
                    <th>Akce</th>
                </tr>
            </thead>
            <tbody>
                {% for zakaznik in zakaznici %}
                <tr>
                    <td><a href="/detail/{{ zakaznik.id }}">{{ zakaznik.id }}</a></td>
                    <td>{{ zakaznik.jmeno }} {{ zakaznik.prijmeni }}</td>
                    <td>{{ zakaznik.email }}</td>
                    <td>{{ "%.2f"|format(zakaznik.celkove_utraceno) }} Kč</td>
                    <td>{{ "%.2f"|format(zakaznik.nasbirana_odmena) }} Kč</td>
                    <td>{{ zakaznik.datum_pridani.strftime('%Y-%m-%d') }}</td>
                    <td>
                        <form action="/delete/{{ zakaznik.id }}" method="post" style="display:inline;">
                            <input type="submit" value="Smazat">
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>Detail zákazníka</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f4; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 900px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #5cb85c; }
        h2 { border-bottom: 2px solid #ddd; padding-bottom: 10px; }
        ul { list-style-type: none; padding: 0; }
        li { padding: 8px 0; border-bottom: 1px solid #eee; }
        form { margin-top: 20px; }
        input[type="number"] { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        input[type="submit"] { background-color: #5cb85c; color: white; padding: 14px 20px; margin: 8px 0; border: none; border-radius: 4px; cursor: pointer; width: 100%; font-size: 16px; }
        a { color: #5cb85c; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Detail zákazníka: {{ zakaznik.jmeno }} {{ zakaznik.prijmeni }}</h1>
        <p><strong>E-mail:</strong> {{ zakaznik.email }}</p>
        <p><strong>Telefon:</strong> {{ zakaznik.telefon }}</p>
        <p><strong>Celkově utraceno:</strong> {{ "%.2f"|format(zakaznik.celkove_utraceno) }} Kč</p>
        <p><strong>Nasbíraná odměna:</strong> {{ "%.2f"|format(zakaznik.nasbirana_odmena) }} Kč</p>
        
        <h2>Historie nákupů</h2>
        {% if zakaznik.nakupy %}
            <ul>
                {% for nakup in zakaznik.nakupy %}
                    <li>{{ "%.2f"|format(nakup.castka) }} Kč - odměna: {{ "%.2f"|format(nakup.odmena) }} Kč ({{ nakup.datum.strftime('%Y-%m-%d %H:%M') }})</li>
                {% endfor %}
            </ul>
        {% else %}
            <p>Žádné nákupy nejsou zaznamenány.</p>
        {% endif %}
        <a href="/">Zpět na přehled</a>
    </div>
</body>
</html>
"""

PERSONNEL_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <title>Věrnostní program - Obsluha</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #e6f7ff; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 500px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #0077b6; text-align: center; }
        .form-group { margin-bottom: 15px; }
        label { font-weight: bold; display: block; margin-bottom: 5px; }
        input[type="number"] { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        input[type="submit"] { background-color: #0077b6; color: white; padding: 12px 20px; border: none; border-radius: 4px; cursor: pointer; width: 100%; font-size: 16px; transition: background-color 0.3s ease; }
        input[type="submit"]:hover { background-color: #005f91; }
        #result { margin-top: 20px; padding: 15px; border-radius: 5px; border: 1px solid #ccc; text-align: center; }
        .blinking {
            animation: blinker 1s linear infinite;
            font-size: 1.2em;
            color: #d9534f;
            font-weight: bold;
        }
        @keyframes blinker {
            50% { opacity: 0; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Věrnostní program</h1>
        <h2>Přidat nákup</h2>
        <form action="/personal/add_nakup" method="post" id="purchaseForm">
            <div class="form-group">
                <label for="zakaznik_id">ID zákazníka:</label>
                <input type="number" id="zakaznik_id" name="zakaznik_id" required>
            </div>
            <div class="form-group">
                <label for="castka">Utracená částka:</label>
                <input type="number" id="castka" name="castka" step="0.01" required>
            </div>
            <input type="submit" value="Přidat">
        </form>

        <div id="result">
            {% if message %}
                <p>{{ message }}</p>
                {% if odmena_blika %}
                    <p class="blinking">Zákazník má nárok na odměnu!</p>
                {% endif %}
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

# --- ROUTY pro obsluhu ---
@app.route("/personal", methods=["GET"])
def personal_form():
    return render_template_string(PERSONNEL_TEMPLATE, message="Zadejte údaje o nákupu.")

@app.route("/personal/add_nakup", methods=["POST"])
def personal_add_nakup():
    try:
        zakaznik_id = int(request.form['zakaznik_id'])
        castka = float(request.form['castka'])

        zakaznik = request.session.query(Zakaznik).get(zakaznik_id)
        
        odmena_blika = False
        message = ""

        if zakaznik:
            # Přidání nákupu
            odmena = castka * zakaznik.hodnota_odmeny / 100
            zakaznik.celkove_utraceno += castka
            n = Nakup(zakaznik=zakaznik, castka=castka, odmena=odmena)
            request.session.add(n)
            request.session.commit()

            # Výpočet celkového cashbacku a ověření, zda bliká odměna
            nasbirana_odmena = sum(n.odmena for n in zakaznik.nakupy)
            if zakaznik.typ_odmeny == "cashback" and nasbirana_odmena >= 500:
                odmena_blika = True

            message = f"Nákup v hodnotě {castka:.2f} Kč pro zákazníka {zakaznik.jmeno} {zakaznik.prijmeni} byl přidán."
        else:
            message = "Zákazník s tímto ID neexistuje."

        return render_template_string(PERSONNEL_TEMPLATE, message=message, odmena_blika=odmena_blika)

    except (ValueError, KeyError):
        return render_template_string(PERSONNEL_TEMPLATE, message="Neplatný vstup, zadejte prosím platná čísla.")
    except Exception as e:
        return render_template_string(PERSONNEL_TEMPLATE, message=f"Došlo k chybě: {e}")

# --- Původní routy pro administraci ---
@app.route("/")
def index():
    zakaznici = request.session.query(Zakaznik).all()
    for z in zakaznici:
        z.nasbirana_odmena = sum(n.odmena for n in z.nakupy)
    return render_template_string(TEMPLATE, zakaznici=zakaznici)

@app.route("/add", methods=["POST"])
def add():
    # Kód pro přidání zákazníka
    # ... (beze změny)
    try:
        z = Zakaznik(
            jmeno=request.form['jmeno'],
            prijmeni=request.form['prijmeni'],
            email=request.form['email'],
            telefon=request.form['telefon'],
            typ_odmeny=request.form['typ_odmeny'],
            hodnota_odmeny=float(request.form['hodnota_odmeny'])
        )
        request.session.add(z)
        request.session.commit()
    except:
        return redirect("/")
    return redirect("/")


@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    # Kód pro smazání zákazníka
    # ... (beze změny)
    zakaznik = request.session.query(Zakaznik).get(id)
    if zakaznik:
        request.session.delete(zakaznik)
        request.session.commit()
    return redirect("/")

@app.route("/detail/<int:id>")
def detail(id):
    # Kód pro detail zákazníka
    # ... (beze změny)
    zakaznik = request.session.query(Zakaznik).get(id)
    zakaznik.nasbirana_odmena = sum(n.odmena for n in zakaznik.nakupy)
    return render_template_string(DETAIL_TEMPLATE, zakaznik=zakaznik)

@app.route("/add_nakup/<int:id>", methods=["POST"])
def add_nakup(id):
    # Kód pro přidání nákupu (na detailu)
    # ... (beze změny)
    zakaznik = request.session.query(Zakaznik).get(id)
    castka = float(request.form['castka'])
    odmena = castka * zakaznik.hodnota_odmeny / 100
    zakaznik.celkove_utraceno += castka
    n = Nakup(zakaznik=zakaznik, castka=castka, odmena=odmena)
    request.session.add(n)
    request.session.commit()
    return redirect(f"/detail/{id}")

if __name__ == "__main__":
    app.run(debug=True)
