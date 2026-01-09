import streamlit as st
import json
import os
from datetime import datetime, date
from fpdf import FPDF

# --- KONFIGURATION ---
DATEI_NAME = "meine_kuechen_daten.json"
ORTE = ["Kühlschrank", "Vorratsregal", "Tiefkühler", "Gewürzschrank", "Keller", "Sonstiges"]

# --- FUNKTIONEN (Laden/Speichern/PDF) ---
def daten_laden():
    if os.path.exists(DATEI_NAME):
        with open(DATEI_NAME, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                return data
            except: return {"vorrat": [], "rezepte": {}, "barcode_db": {}}
    return {"vorrat": [], "rezepte": {}, "barcode_db": {}}

def daten_speichern():
    daten = {"vorrat": st.session_state.vorrat, "rezepte": st.session_state.rezepte, "barcode_db": st.session_state.barcode_db}
    with open(DATEI_NAME, "w", encoding="utf-8") as f:
        json.dump(daten, f, indent=4, ensure_ascii=False)

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
if 'daten_geladen' not in st.session_state:
    daten = daten_laden()
    st.session_state.vorrat = daten.get("vorrat", [])
    st.session_state.rezepte = daten.get("rezepte", {})
    st.session_state.barcode_db = daten.get("barcode_db", {})
    st.session_state.daten_geladen = True

# --- NAVIGATION ---
st.sidebar.title("🍎 Küchen-Manager")
menu = st.sidebar.radio("Navigation", ["📦 Vorrat", "➕ Neu hinzufügen", "📖 Rezepte", "🍳 Kochen & Shopping"])

# --- 1. VORRAT ---
if menu == "📦 Vorrat":
    st.header("🏠 Dein Bestand")
    for ort in ORTE:
        artikel = [i for i in st.session_state.vorrat if i.get('ort') == ort]
        if artikel:
            with st.expander(f"📍 {ort}"):
                for item in artikel:
                    st.write(f"**{item['artikel']}** ({item['menge']} {item['einheit']}) - MHD: {item['mhd']}")

# --- 2. NEU HINZUFÜGEN (Ohne Kamera-Scanner) ---
elif menu == "➕ Neu hinzufügen":
    st.header("🛒 Produkte einlagern")
    manual_barcode = st.text_input("Barcode-Nummer (optional)")
    default_name = st.session_state.barcode_db.get(manual_barcode, "") if manual_barcode else ""
    
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("Name des Produkts", value=default_name)
        ort = st.selectbox("Ort", ORTE)
        col1, col2 = st.columns(2)
        menge = col1.number_input("Menge", min_value=0.1, value=1.0)
        einheit = col1.selectbox("Einheit", ["Stück", "Packung", "g", "kg", "ml", "L", "Dose"])
        mhd = col2.date_input("MHD", value=date.today())
        
        if st.form_submit_button("Speichern"):
            st.session_state.vorrat.append({"artikel": name
