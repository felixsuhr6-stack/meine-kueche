import streamlit as st
import json
import hashlib
import requests
from fpdf import FPDF
from datetime import datetime, date

# --- 1. KONFIGURATION ---
# Deine Google Apps Script URL:
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyh6FaOQeXodvSLfCXFq-dUIP-BHhzqcuItXrbboxsM2FdWCaPa9udeUHv2HEJ5zi4JDg/exec"

ORTE = ["Kühlschrank", "Vorratsregal", "Tiefkühler", "Gewürzschrank", "Keller", "Sonstiges"]
TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
ADMIN_USER = "admin"
ADMIN_PASS = "admin" 

# --- 2. DATENBANK FUNKTIONEN ---
def daten_laden():
    try:
        response = requests.get(WEB_APP_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if not data or "haushalte" not in data:
                return {"haushalte": {}, "globale_rezepte": {}, "globale_anleitungen": {}}
            return data
        return {"haushalte": {}, "globale_rezepte": {}, "globale_anleitungen": {}}
    except:
        return {"haushalte": {}, "globale_rezepte": {}, "globale_anleitungen": {}}

def daten_speichern(alle_daten):
    try:
        requests.post(WEB_APP_URL, json=alle_daten, timeout=10)
    except Exception as e:
        st.error(f"Fehler beim Speichern: {e}")

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
        text = f"- {item}".encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(200, 10, txt=text, ln=True)
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 3. APP SETUP ---
st.set_page_config(page_title="Küchen-Chef Cloud", layout="wide", page_icon="☁️")

if 'haushalt' not in st.session_state: st.session_state.haushalt = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

def apply_dark_mode():
    st.markdown("""<style>.stApp { background-color: #1E1E1E; color: white; } div[data-testid="stSidebar"] { background-color: #262730; } .stTextInput>div>div>input, .stTextArea>div>div>textarea { color: black; }</style>""", unsafe_allow_html=True)

alle_daten = daten_laden()

# --- 4. LOGIN & REGISTRIERUNG ---
if st.session_state.haushalt is None and not st.session_state.is_admin:
    st.header("☁️ Küchen-Chef Cloud Login")
    
    with st.expander("🛠️ Entwickler-Login"):
        a_user = st.text_input("Admin Name", key="ad_u")
        a_pass = st.text_input("Admin Passwort", type="password", key="ad_p")
        if st.button("Als Entwickler starten"):
            if a_user == ADMIN_USER and a_pass == ADMIN_PASS:
                st.session_state.is_admin = True
                st.session_state.haushalt = "ADMIN"
                st.rerun()
            else: st.error("Falsche Admin-Daten")

    st.subheader("Anmelden oder Registrieren")
    h_name = st.text_input("Haushalts-Name").strip()
    h_pass = st.text_input("Passwort", type="password")
    
    col_l, col_r = st.columns(2)
    
    if col_l.button("🔐 Anmelden"):
        if h_name in alle_daten["haushalte"]:
            if alle_daten["haushalte"][h_name]['passwort'] == hash_passwort(h_pass):
                st.session_state.haushalt = h_name
                st.rerun()
            else: st.error("Passwort falsch!")
        else: st.error("Haushalt nicht gefunden.")

    if col_r.button("📝 Neu Registrieren"):
        if h_name and h_pass and h_name not in alle_daten["haushalte"] and h_name != ADMIN_USER:
            alle_daten["haushalte"][h_name] = {
                "passwort": hash_passwort(h_pass), "vorrat": [], 
                "wochenplan": {t: "-" for t in TAGE}, "einkauf": [], 
                "stats": {"weg": 0, "geg
