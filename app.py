import streamlit as st
import json
import os
from datetime import datetime, date
from streamlit_barcode_reader import streamlit_barcode_reader
from fpdf import FPDF

# --- KONFIGURATION & DATEI-PFAD ---
DATEI_NAME = "meine_kuechen_daten.json"
ORTE = ["Kühlschrank", "Vorratsregal", "Tiefkühler", "Gewürzschrank", "Keller", "Sonstiges"]

# --- FUNKTIONEN ---
def daten_laden():
    if os.path.exists(DATEI_NAME):
        with open(DATEI_NAME, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if "vorrat" not in data: data["vorrat"] = []
                if "rezepte" not in data: data["rezepte"] = {}
                if "barcode_db" not in data: data["barcode_db"] = {}
                return data
            except:
                return {"vorrat": [], "rezepte": {}, "barcode_db": {}}
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
st.set_page_config(page_title="Küchen-Chef Pro", layout="wide", page_icon="🍎")

if 'daten_geladen' not in st.session_state:
    daten = daten_laden()
    st.session_state.vorrat = daten["vorrat"]
    st.session_state.rezepte = daten["rezepte"]
    st.session_state.barcode_db = daten["barcode_db"]
    st.session_state.daten_geladen = True

# --- NAVIGATION ---
st.sidebar.title("🍎 Küchen-Manager")
menu = st.sidebar.radio("Navigation", ["📦 Vorrat nach Orten", "➕ Neu hinzufügen (Scan)", "📖 Rezeptbuch", "🍳 Kochen & Shopping", "📱 Handy-Info"])

# --- 1. VORRAT NACH ORTEN ---
if menu == "📦 Vorrat nach Orten":
    st.header("🏠 Dein Bestand")
    if not st.session_state.vorrat:
        st.info("Deine Vorratskammer ist leer.")
    else:
        for ort in ORTE:
            artikel_am_ort = [i for i in st.session_state.vorrat if i.get('ort') == ort]
            if artikel_am_ort:
                with st.expander(f"📍 {ort} ({len(artikel_am_ort)} Artikel)", expanded=True):
                    artikel_am_ort.sort(key=lambda x: x.get('mhd', '9999-12-31'))
                    for item in artikel_am_ort:
                        heute = date.today()
                        mhd_dt = datetime.strptime(item['mhd'], '%Y-%m-%d').date()
                        tage = (mhd_dt - heute).days
                        color = "🔴" if tage < 0 else "🟡" if tage <= 7 else "🟢"
                        
                        c1, c2, c3 = st.columns([0.1, 0.7, 0.2])
                        c1.write(color)
                        c2.write(f"**{item['artikel']}** ({item['menge']} {item['einheit']}) — MHD: {item['mhd']}")
                        if c3.button("Löschen", key=f"del_{item['artikel']}_{item['mhd']}"):
                            st.session_state.vorrat.remove(item)
                            daten_speichern()
                            st.rerun()

# --- 2. NEU HINZUFÜGEN (BARCODE) ---
elif menu == "➕ Neu hinzufügen (Scan)":
    st.header("🛒 Produkte einlagern")
    barcode = streamlit_barcode_reader(key='reader')
    default_name = st.session_state.barcode_db.get(str(barcode), "") if barcode else ""
    if barcode: st.success(f"Barcode: {barcode} " + (f"({default_name})" if default_name else ""))

    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name = col1.text_input("Name", value=default_name)
        ort = col1.selectbox("Ort", ORTE)
        menge = col2.number_input("Menge", min_value=0.1, value=1.0)
        einheit = col2.selectbox("Einheit", ["Stück", "Packung", "g", "kg", "ml", "L", "Dose"])
        mhd = st.date_input("MHD", value=date.today())
        if st.form_submit_button("Speichern"):
            if name:
                st.session_state.vorrat.append({"artikel": name, "menge": menge, "einheit": einheit, "ort": ort, "mhd": str(mhd)})
                if barcode: st.session_state.barcode_db[str(barcode)] = name
                daten_speichern()
                st.success(f"{name} verstaut!")

# --- 3. REZEPTBUCH ---
elif menu == "📖 Rezeptbuch":
    st.header("📖 Deine Rezepte")
    with st.expander("➕ Neues Rezept"):
        r_name = st.text_input("Name")
        if 'temp_z' not in st.session_state: st.session_state.temp_z = {}
        c1, c2, c3 = st.columns([3, 2, 1])
        z_n = c1.text_input("Zutat")
        z_m = c2.number_input("Menge", min_value=0.1)
        if c3.button("Zutat +"):
            if z_n: st.session_state.temp_z[z_n] = z_m
        if st.button("Speichern"):
            st.session_state.rezepte[r_name] = st.session_state.temp_z
            daten_speichern(); st.session_state.temp_z = {}; st.rerun()

    for r, z in st.session_state.rezepte.items():
        with st.expander(f"🍽️ {r}"):
            st.write(z)
            if st.button(f"Löschen", key=f"r_del_{r}"):
                del st.session_state.rezepte[r]; daten_speichern(); st.rerun()

# --- 4. KOCHEN & SHOPPING (MIT PDF EXPORT) ---
elif menu == "🍳 Kochen & Shopping":
    st.header("🍳 Kochen & Einkaufsliste")
    wahl = st.selectbox("Rezept wählen", ["-"] + list(st.session_state.rezepte.keys()))
    if wahl != "-":
        zutaten = st.session_state.rezepte[wahl]
        vorrat_summe = {i['artikel'].lower(): 0 for i in st.session_state.vorrat}
        for i in st.session_state.vorrat: vorrat_summe[i['artikel'].lower()] += i['menge']
        
        shopping_liste = []
        alles_da = True
        for z, m_soll in zutaten.items():
            m_ist = vorrat_summe.get(z.lower(), 0)
            if m_ist >= m_soll: st.success(f"✅ {z}")
            else:
                st.error(f"❌ {z} (Fehlt: {m_soll - m_ist})")
                shopping_liste.append(f"{z}: {m_soll - m_ist}")
                alles_da = False
        
        if alles_da:
            if st.button("Kochen & Vorrat abbuchen"):
                for z, m_soll in zutaten.items():
                    m_abzuziehen = m_soll
                    for item in st.session_state.vorrat:
                        if item['artikel'].lower() == z.lower():
                            if item['menge'] >= m_abzuziehen: item['menge'] -= m_abzuziehen; m_abzuziehen = 0
                            else: m_abzuziehen -= item['menge']; item['menge'] = 0
                    if m_abzuziehen <= 0: break
                st.session_state.vorrat = [i for i in st.session_state.vorrat if i['menge'] > 0]
                daten_speichern(); st.balloons(); st.rerun()
        elif shopping_liste:
            pdf_data = erstelle_pdf(shopping_liste, f"Einkaufsliste: {wahl}")
            st.download_button(label="📄 Einkaufsliste als PDF herunterladen", data=pdf_data, file_name=f"einkauf_{wahl}.pdf", mime="application/pdf")

# --- 5. HANDY INFO ---
elif menu == "📱 Handy-Info":
    st.header("📱 Handy-Verbindung")
    st.info("Nutze die 'Network URL' aus dem Terminal. Falls die Kamera nicht geht: 'chrome://flags' -> 'Insecure origins treated as secure' -> Deine IP eintragen.")
