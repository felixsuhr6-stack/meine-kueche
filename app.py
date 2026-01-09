import streamlit as st
import json
import os
from datetime import datetime, date
from fpdf import FPDF

# --- KONFIGURATION ---
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
                return data
            except:
                return {"vorrat": [], "rezepte": {}}
    return {"vorrat": [], "rezepte": {}}

def daten_speichern():
    daten = {"vorrat": st.session_state.vorrat, "rezepte": st.session_state.rezepte}
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
    st.session_state.vorrat = daten.get("vorrat", [])
    st.session_state.rezepte = daten.get("rezepte", {})
    st.session_state.daten_geladen = True

# --- NAVIGATION ---
st.sidebar.title("🍎 Küchen-Manager")
menu = st.sidebar.radio("Navigation", ["📦 Vorrat", "➕ Neu hinzufügen", "📖 Rezepte", "🍳 Kochen & Shopping"])

# --- 1. VORRAT ---
if menu == "📦 Vorrat":
    st.header("🏠 Dein Bestand")
    if not st.session_state.vorrat:
        st.info("Deine Vorratskammer ist leer.")
    else:
        for ort in ORTE:
            artikel_am_ort = [i for i in st.session_state.vorrat if i.get('ort') == ort]
            if artikel_am_ort:
                with st.expander(f"📍 {ort} ({len(artikel_am_ort)} Artikel)", expanded=True):
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

# --- 2. NEU HINZUFÜGEN ---
elif menu == "➕ Neu hinzufügen":
    st.header("🛒 Produkte einlagern")
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name = col1.text_input("Name des Produkts")
        ort = col1.selectbox("Lagerort", ORTE)
        menge = col2.number_input("Menge", min_value=0.1, value=1.0)
        einheit = col2.selectbox("Einheit", ["Stück", "Packung", "g", "kg", "ml", "L", "Dose"])
        mhd = st.date_input("Haltbar bis (MHD)", value=date.today())
        
        if st.form_submit_button("In den Schrank legen"):
            if name:
                st.session_state.vorrat.append({
                    "artikel": name, 
                    "menge": menge, 
                    "einheit": einheit, 
                    "ort": ort, 
                    "mhd": str(mhd)
                })
                daten_speichern()
                st.success(f"✅ {name} wurde gespeichert!")

# --- 3. REZEPTE ---
elif menu == "📖 Rezepte":
    st.header("📖 Rezeptbuch")
    with st.expander("➕ Neues Rezept erstellen"):
        r_name = st.text_input("Name des Gerichts")
        if 'temp_zutaten' not in st.session_state:
            st.session_state.temp_zutaten = {}
        
        c1, c2, c3 = st.columns([3, 2, 1])
        z_name = c1.text_input("Zutat")
        z_menge = c2.number_input("Menge nötig", min_value=0.1)
        if c3.button("Hinzufügen"):
            if z_name:
                st.session_state.temp_zutaten[z_name] = z_menge
                st.rerun()
        
        if st.session_state.temp_zutaten:
            st.write("Zutaten bisher:")
            for z, m in st.session_state.temp_zutaten.items():
                st.write(f"- {z}: {m}")
            if st.button("Rezept speichern"):
                if r_name:
                    st.session_state.rezepte[r_name] = st.session_state.temp_zutaten
                    daten_speichern()
                    st.session_state.temp_zutaten = {}
                    st.success(f"Rezept '{r_name}' gespeichert!")
                    st.rerun()

    for r, zutaten in st.session_state.rezepte.items():
        with st.expander(f"🍽️ {r}"):
            for z, m in zutaten.items():
                st.write(f"- {z}: {m}")
            if st.button("Löschen", key=f"r_del_{r}"):
                del st.session_state.rezepte[r]
                daten_speichern()
                st.rerun()

# --- 4. KOCHEN & SHOPPING ---
elif menu == "🍳 Kochen & Shopping":
    st.header("🍳 Kochen & Einkaufsliste")
    wahl = st.selectbox("Was möchtest du kochen?", ["-"] + list(st.session_state.rezepte.keys()))
    if wahl != "-":
        zutaten_req = st.session_state.rezepte[wahl]
        vorrat_summe = {i['artikel'].lower(): 0 for i in st.session_state.vorrat}
        for i in st.session_state.vorrat:
            vorrat_summe[i['artikel'].lower()] += i['menge']
        
        shopping_liste = []
        alles_da = True
        for z, m_soll in zutaten_req.items():
            m_ist = vorrat_summe.get(z.lower(), 0)
            if m_ist >= m_soll:
                st.success(f"✅ {z}")
            else:
                st.error(f"❌ {z} (Fehlt: {m_soll - m_ist})")
                shopping_liste.append(f"{z}: {m_soll - m_ist}")
                alles_da = False
        
        if alles_da:
            if st.button("Jetzt Kochen"):
                for z, m_soll in zutaten_req.items():
                    m_abzuziehen = m_soll
                    for item in st.session_state.vorrat:
                        if item['artikel'].lower() == z.lower():
                            if item['menge'] >= m_abzuziehen:
                                item['menge'] -= m_abzuziehen
                                m_abzuziehen = 0
                            else:
                                m_abzuziehen -= item['menge']
                                item['menge'] = 0
                        if m_abzuziehen <= 0: break
                st.session_state.vorrat = [i for i in st.session_state.vorrat if i['menge'] > 0]
                daten_speichern()
                st.balloons()
                st.rerun()
        elif shopping_liste:
            pdf_data = erstelle_pdf(shopping_liste, f"Einkauf für {wahl}")
            st.download_button("📄 PDF Einkaufsliste", data=pdf_data, file_name="einkauf.pdf")
