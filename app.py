
import streamlit as st
import json
import os
import hashlib
from datetime import datetime, date
from fpdf import FPDF

# --- KONFIGURATION ---
DATEI_NAME = "multi_haushalt_daten.json"
ORTE = ["Kühlschrank", "Vorratsregal", "Tiefkühler", "Gewürzschrank", "Keller", "Sonstiges"]

# --- DATEN-FUNKTIONEN ---
def daten_laden():
    if os.path.exists(DATEI_NAME):
        with open(DATEI_NAME, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except: return {}
    return {}

def daten_speichern(alle_daten):
    with open(DATEI_NAME, "w", encoding="utf-8") as f:
        json.dump(alle_daten, f, indent=4, ensure_ascii=False)

def hash_passwort(passwort):
    return hashlib.sha256(str.encode(passwort)).hexdigest()

def erstelle_pdf(liste, titel):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt=titel, ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for item in liste:
        pdf.cell(200, 10, txt=f"- {item}", ln=True)
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- INITIALISIERUNG ---
st.set_page_config(page_title="Küchen-Chef Multi", layout="wide", page_icon="🍎")

if 'haushalt' not in st.session_state:
    st.session_state.haushalt = None

# --- LOGIN SEITE ---
if st.session_state.haushalt is None:
    st.header("🔐 Willkommen beim Küchen-Chef")
    st.subheader("Bitte melde dich an oder erstelle einen neuen Haushalt")
    
    with st.form("login_form"):
        h_name = st.text_input("Name des Haushalts (z.B. Familie_Mustermann)").strip()
        h_pass = st.text_input("Passwort", type="password")
        col1, col2 = st.columns(2)
        login_btn = col1.form_submit_button("Anmelden")
        register_btn = col2.form_submit_button("Neu registrieren")
        
        alle_daten = daten_laden()
        
        if login_btn:
            if h_name in alle_daten and alle_daten[h_name]['passwort'] == hash_passwort(h_pass):
                st.session_state.haushalt = h_name
                st.rerun()
            else:
                st.error("Falscher Name oder Passwort!")
        
        if register_btn:
            if h_name and h_pass:
                if h_name not in alle_daten:
                    alle_daten[h_name] = {
                        "passwort": hash_passwort(h_pass),
                        "vorrat": [],
                        "rezepte": {},
                        "einkauf": []
                    }
                    daten_speichern(alle_daten)
                    st.success("Haushalt erstellt! Bitte jetzt anmelden.")
                else:
                    st.error("Dieser Name existiert bereits!")
            else:
                st.warning("Bitte Namen und Passwort eingeben.")
    st.stop()

# --- AB HIER: EINGELOGGT ---
h_name = st.session_state.haushalt
alle_daten = daten_laden()
mein_h = alle_daten[h_name]

# Logout Button oben in der Sidebar
if st.sidebar.button("🔓 Logout (" + h_name + ")"):
    st.session_state.haushalt = None
    st.rerun()

menu = st.sidebar.radio("Navigation", ["📦 Vorrat", "➕ Neu hinzufügen", "📖 Rezepte", "🍳 Kochen", "🛒 Einkaufsliste"])

# --- Hilfsfunktion zum Speichern der Änderungen im Haushalt ---
def save():
    alle_daten[h_name] = mein_h
    daten_speichern(alle_daten)

# --- 1. VORRAT ---
if menu == "📦 Vorrat":
    st.header(f"🏠 Vorrat von {h_name}")
    if not mein_h["vorrat"]:
        st.info("Noch leer.")
    else:
        for ort in ORTE:
            artikel = [i for i in mein_h["vorrat"] if i.get('ort') == ort]
            if artikel:
                with st.expander(f"📍 {ort}", expanded=True):
                    for item in artikel:
                        heute = date.today()
                        mhd_dt = datetime.strptime(item['mhd'], '%Y-%m-%d').date()
                        tage = (mhd_dt - heute).days
                        color = "🔴" if tage <= 3 else "🟡" if tage <= 7 else "🟢"
                        
                        c1, c2, c3 = st.columns([0.1, 0.7, 0.2])
                        c1.write(color)
                        c2.write(f"**{item['artikel']}** ({item['menge']} {item['einheit']}) — MHD: {item['mhd']} ({tage} Tage)")
                        if c3.button("Löschen", key=f"del_{item['artikel']}_{item['mhd']}"):
                            mein_h["vorrat"].remove(item)
                            save(); st.rerun()

# --- 2. NEU HINZUFÜGEN ---
elif menu == "➕ Neu hinzufügen":
    st.header("➕ Artikel hinzufügen")
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("Produktname")
        ort = st.selectbox("Ort", ORTE)
        menge = st.number_input("Menge", min_value=0.1, value=1.0)
        einheit = st.selectbox("Einheit", ["Stück", "Packung", "g", "kg", "ml", "L", "Dose"])
        mhd = st.date_input("MHD", value=date.today())
        if st.form_submit_button("Speichern"):
            if name:
                mein_h["vorrat"].append({"artikel": name, "menge": menge, "einheit": einheit, "ort": ort, "mhd": str(mhd)})
                save(); st.success("Gespeichert!")

# --- 3. REZEPTE ---
elif menu == "📖 Rezepte":
    st.header("📖 Rezepte")
    with st.expander("➕ Neues Rezept"):
        r_name = st.text_input("Name")
        if 'temp_z' not in st.session_state: st.session_state.temp_z = {}
        c1, c2, c3 = st.columns([3, 2, 1])
        z_n = c1.text_input("Zutat")
        z_m = c2.number_input("Menge", min_value=0.1)
        if c3.button("Zutat +"):
            if z_n: st.session_state.temp_z[z_n] = z_m; st.rerun()
        if st.session_state.temp_z:
            st.write(st.session_state.temp_z)
            if st.button("Rezept speichern"):
                mein_h["rezepte"][r_name] = st.session_state.temp_z
                st.session_state.temp_z = {}; save(); st.rerun()
    
    for r, zutaten in mein_h["rezepte"].items():
        with st.expander(f"🍽️ {r}"):
            st.write(zutaten)
            if st.button("Löschen", key=f"r_del_{r}"):
                del mein_h["rezepte"][r]; save(); st.rerun()

# --- 4. KOCHEN (MIT SMART-CHECK) ---
elif menu == "🍳 Kochen":
    st.header("🍳 Kochen")
    heute = date.today()
    # MHD Check für Vorschläge
    bald_weg = [i['artikel'].lower() for i in mein_h["vorrat"] if (datetime.strptime(i['mhd'], '%Y-%m-%d').date() - heute).days <= 7]
    if bald_weg:
        vorschläge = [r for r, zut in mein_h["rezepte"].items() if any(k in " ".join(zut.keys()).lower() for k in bald_weg)]
        if vorschläge: st.info(f"💡 Tipp: Koche **{', '.join(vorschläge)}**, um Reste zu verwerten!")

    wahl = st.selectbox("Rezept wählen", ["-"] + list(mein_h["rezepte"].keys()))
    if wahl != "-":
        req = mein_h["rezepte"][wahl]
        vorrat_summe = {i['artikel'].lower(): 0 for i in mein_h["vorrat"]}
        for i in mein_h["vorrat"]: vorrat_summe[i['artikel'].lower()] += i['menge']
        
        alles_da = True
        for z, m in req.items():
            ist = vorrat_summe.get(z.lower(), 0)
            if ist >= m: st.success(f"✅ {z}")
            else:
                st.error(f"❌ {z} (Fehlt: {m-ist})")
                alles_da = False
                if st.button(f"'{z}' auf Einkaufsliste"):
                    if z not in mein_h["einkauf"]: mein_h["einkauf"].append(z); save()
        
        if alles_da and st.button("Jetzt Kochen"):
            for z, m in req.items():
                m_abz = m
                for item in mein_h["vorrat"]:
                    if item['artikel'].lower() == z.lower():
                        if item['menge'] >= m_abz: item['menge'] -= m_abz; m_abz = 0
                        else: m_abz -= item['menge']; item['menge'] = 0
                if m_abz <= 0: break
            mein_h["vorrat"] = [i for i in mein_h["vorrat"] if i['menge'] > 0]
            save(); st.balloons(); st.rerun()

# --- 5. EINKAUFSLISTE ---
elif menu == "🛒 Einkaufsliste":
    st.header("🛒 Einkaufsliste")
    with st.form("shop_f"):
        item = st.text_input("Was fehlt?")
        if st.form_submit_button("Hinzufügen"):
            if item: mein_h["einkauf"].append(item); save(); st.rerun()
    
    for i in mein_h["einkauf"]:
        c1, c2 = st.columns([0.8, 0.2])
        c1.write(f"- {i}")
        if c2.button("Gekauft", key=f"s_{i}"):
            mein_h["einkauf"].remove(i); save(); st.rerun()
    
    if mein_h["einkauf"]:
        pdf = erstelle_pdf(mein_h["einkauf"], "Einkaufsliste")
        st.download_button("📄 PDF Download", pdf, "liste.pdf")
