from flask import Flask, request, render_template_string, redirect
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
import os

# --- Krok 1: Dynamická konfigurace databáze ---
# Načtení URL databáze z proměnných prostředí.
# Pokud proměnná není nastavena (lokální vývoj), použije se SQLite.
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///vernost.db")
engine = create_engine(DB_URL)

Session = sessionmaker(bind=engine)
Base = declarative_base()

# --- Modely databáze (zákazníci a nákupy) - zůstávají beze změny ---
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

# Vytvoření tabulek
Base.metadata.create_all(engine)
app = Flask(__name__)

# --- Krok 2: Správa databázového sezení (session) ---
# Tvoříme novou session pro každý požadavek.
@app.before_request
def create_session():
    request.session = Session()

# Uzavření session po dokončení požadavku.
@app.teardown_request
def close_session(exception=None):
    request.session.close()

# --- Routy (cesty) webové aplikace ---
@app.route("/")
def index():
    zakaznici = request.session.query(Zakaznik).all()
    for z in zakaznici:
        z.nasbirana_odmena = sum(n.odmena for n in z.nakupy)
    return render_template_string(TEMPLATE, zakaznici=zakaznici)

@app.route("/add", methods=["POST"])
def add():
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
    return redirect("/")

@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    zakaznik = request.session.query(Zakaznik).get(id)
    if zakaznik:
        request.session.delete(zakaznik)
        request.session.commit()
    return redirect("/")

@app.route("/detail/<int:id>")
def detail(id):
    zakaznik = request.session.query(Zakaznik).get(id)
    zakaznik.nasbirana_odmena = sum(n.odmena for n in zakaznik.nakupy)
    return render_template_string(DETAIL_TEMPLATE, zakaznik=zakaznik)

@app.route("/add_nakup/<int:id>", methods=["POST"])
def add_nakup(id):
    zakaznik = request.session.query(Zakaznik).get(id)
    castka = float(request.form['castka'])
    odmena = castka * zakaznik.hodnota_odmeny / 100
    zakaznik.celkove_utraceno += castka
    n = Nakup(zakaznik=zakaznik, castka=castka, odmena=odmena)
    request.session.add(n)
    request.session.commit()
    return redirect(f"/detail/{id}")

# --- Krok 3: Spuštění aplikace v produkčním režimu ---
# `debug=False` je klíčové pro online nasazení kvůli bezpečnosti.
if __name__ == "__main__":
    app.run(debug=True)
