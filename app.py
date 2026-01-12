import streamlit as st
import json
import os
import hashlib
from datetime import datetime, date
from fpdf import FPDF

# --- KONFIGURATION ---
DATEI_NAME = "multi_haushalt_daten.json"
ORTE = ["Kühlschrank", "Vorratsregal", "Tiefkühler", "Gewürzschrank", "Keller", "Sonstiges"]
TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

# --- FUNKTIONEN ---
def daten_laden():
    if os.path.exists(DATEI_NAME):
        with open(DATEI_NAME, "r", encoding="utf-8") as f:
            try: 
                data = json.load(f)
                # Notfall-Check: Wenn die Datei noch die ganz alte Struktur hat
                if "haushalte" not in data and "globale_rezepte" not in data:
                    old_data = data.copy()
                    data = {"haushalte": old_data, "globale_rezepte": {}, "globale_anleitungen": {}}
                
                if "globale_rezepte" not in data: data["globale_rezepte"] = {}
                if "globale_anleitungen" not in data: data["globale_anleitungen"] = {}
                if "haushalte" not in data: data["haushalte"] = {}
                return data
            except: return {"globale_rezepte": {}, "globale_anleitungen": {}, "haushalte": {}}
    return {"globale_rezepte": {}, "globale_anleitungen": {}, "haushalte": {}}

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

# --- SETUP ---
st.set_page_config(page_title="Küchen-Chef Connect", layout="wide", page_icon="🍎")

def apply_dark_mode():
    st.markdown("""<style>.stApp { background-color: #1E1E1E; color: white; } div[data-testid="stSidebar"] { background-color: #262730; } .stTextInput>div>div>input, .stTextArea>div>div>textarea { color: black; }</style>""", unsafe_allow_html=True)

if 'haushalt' not in st.session_state:
    st.session_state.haushalt = None

alle_daten = daten_laden()

# --- LOGIN SCREEN ---
if st.session_state.haushalt is None:
    st.header("🔐 Küchen-Chef Login")
    with st.form("login_form"):
        h_name = st.text_input("Haushalts-Name").strip()
        h_pass = st.text_input("Passwort", type="password")
        c1, c2 = st.columns(2)
        
        if c1.form_submit_button("Anmelden"):
            # Prüfe ob der Haushalt existiert (egal ob neue oder alte Struktur)
            if h_name in alle_daten["haushalte"]:
                user_data = alle_daten["haushalte"][h_name]
                if user_data['passwort'] == hash_passwort(h_pass):
                    st.session_state.haushalt = h_name
                    st.rerun()
                else:
                    st.error("Passwort falsch!")
            else:
                st.error("Haushalt nicht gefunden!")
                
        if c2.form_submit_button("Neu Registrieren"):
            if h_name and h_pass and h_name not in alle_daten["haushalte"]:
                alle_daten["haushalte"][h_name] = {
                    "passwort": hash_passwort(h_pass), "vorrat": [], 
                    "wochenplan": {t: "-" for t in TAGE}, "einkauf": [], 
                    "stats": {"weg": 0, "gegessen": 0}, "verlinkt": []
                }
                daten_speichern(alle_daten)
                st.success("Konto erstellt! Bitte jetzt anmelden.")
            else:
                st.warning("Name vergeben oder leer.")
    st.stop()

# --- AB HIER BLEIBT DER REST GLEICH (WIE IM VORHERIGEN CODE) ---
h_name = st.session_state.haushalt
mein_h = alle_daten["haushalte"][h_name]

# Sicherstellen dass alle Unter-Ordner da sind
if "verlinkt" not in mein_h: mein_h["verlinkt"] = []
if "stats" not in mein_h: mein_h["stats"] = {"weg": 0, "gegessen": 0}
if "wochenplan" not in mein_h: mein_h["wochenplan"] = {t: "-" for t in TAGE}
if "einkauf" not in mein_h: mein_h["einkauf"] = []
if "vorrat" not in mein_h: mein_h["vorrat"] = []

def save_all():
    daten_speichern(alle_daten)

# SIDEBAR
st.sidebar.title(f"🏠 {h_name}")
dark_mode = st.sidebar.checkbox("🌑 Dark Mode")
if dark_mode: apply_dark_mode()

menu = st.sidebar.radio("Menü", ["📅 Wochenplan", "📦 Vorrat", "➕ Neu", "📖 Gemeinschafts-Rezepte", "🍳 Kochen", "🛒 Einkauf", "📊 Statistik & Connect"])

with st.sidebar.expander("🧮 Umrechner"):
    wert = st.number_input("Wert", value=100.0)
    von = st.selectbox("Von", ["g", "kg", "ml", "L"])
    if von == "g": st.write(f"= {wert/1000} kg")
    elif von == "kg": st.write(f"= {wert*1000} g")
    elif von == "ml": st.write(f"= {wert/1000} L")
    elif von == "L": st.write(f"= {wert*1000} ml")

if st.sidebar.button("Logout"):
    st.session_state.haushalt = None
    st.rerun()

# --- DIE MODULE (ZUSAMMENGEFASST FÜR DIE ÜBERSICHT) ---

if menu == "📅 Wochenplan":
    st.header("📅 Wochenplaner")
    rezepte_liste = ["-"] + list(alle_daten["globale_rezepte"].keys())
    with st.form("w_form"):
        for t in TAGE:
            aktuell = mein_h["wochenplan"].get(t, "-")
            if aktuell not in rezepte_liste: aktuell = "-"
            mein_h["wochenplan"][t] = st.selectbox(t, rezepte_liste, index=rezepte_liste.index(aktuell))
        if st.form_submit_button("Plan speichern"): save_all(); st.success("Gespeichert!")

elif menu == "📦 Vorrat":
    st.header("📦 Vorräte")
    tab1, tab2 = st.tabs(["🏠 Mein Haushalt", "🔗 Verknüpfte Freunde"])
    with tab1:
        sort_mode = st.radio("Sortierung:", ["MHD", "A-Z"], horizontal=True)
        for ort in ORTE:
            items = [i for i in mein_h["vorrat"] if i.get('ort') == ort]
            if items:
                items.sort(key=lambda x: x.get('mhd', '9999') if "MHD" in sort_mode else x.get('artikel', '').lower())
                with st.expander(f"📍 {ort}", expanded=True):
                    for item in items:
                        c1, c2, c3, c4 = st.columns([0.5, 4, 1, 1])
                        c2.write(f"**{item['artikel']}** ({item['menge']} {item['einheit']}) - MHD: {item['mhd']}")
                        if c3.button("🍽️", key=f"e_{item['artikel']}_{item['mhd']}"):
                            mein_h["vorrat"].remove(item); mein_h["stats"]["gegessen"] += 1; save_all(); st.rerun()
                        if c4.button("🗑️", key=f"t_{item['artikel']}_{item['mhd']}"):
                            mein_h["vorrat"].remove(item); mein_h["stats"]["weg"] += 1; save_all(); st.rerun()
    with tab2:
        for f_name in mein_h["verlinkt"]:
            if f_name in alle_daten["haushalte"]:
                f_h = alle_daten["haushalte"][f_name]
                with st.expander(f"👤 Kühlschrank von {f_name}"):
                    for i in f_h["vorrat"]:
                        st.write(f"{i['artikel']} ({i['menge']} {i['einheit']})")

elif menu == "➕ Neu":
    st.header("➕ Neu")
    with st.form("n"):
        n = st.text_input("Name")
        o = st.selectbox("Ort", ORTE)
        m = st.number_input("Menge", 1.0)
        e = st.selectbox("Einh.", ["Stück", "g", "kg", "ml", "L", "Pk."])
        d = st.date_input("MHD")
        if st.form_submit_button("Speichern"):
            mein_h["vorrat"].append({"artikel": n, "menge": m, "einheit": e, "ort": o, "mhd": str(d)})
            save_all(); st.success("Drin!")

elif menu == "📖 Gemeinschafts-Rezepte":
    st.header("📖 Rezepte")
    with st.expander("➕ Neu"):
        rn = st.text_input("Name")
        anl = st.text_area("Anleitung")
        if st.button("Speichern"):
            alle_daten["globale_rezepte"][rn] = {} # Nur Name/Anleitung hier vereinfacht
            alle_daten["globale_anleitungen"][rn] = anl
            save_all(); st.rerun()
    for r in list(alle_daten["globale_rezepte"].keys()):
        with st.expander(r):
            st.write(alle_daten["globale_anleitungen"].get(r, ""))
            if st.button("Löschen", key=r): del alle_daten["globale_rezepte"][r]; save_all(); st.rerun()

elif menu == "🍳 Kochen":
    st.header("🍳 Kochen")
    wahl = st.selectbox("Was kochen?", ["-"] + list(alle_daten["globale_rezepte"].keys()))
    if wahl != "-":
        st.write(alle_daten["globale_anleitungen"].get(wahl, ""))

elif menu == "🛒 Einkauf":
    st.header("🛒 Einkauf")
    new = st.text_input("Neu")
    if st.button("Add"): mein_h["einkauf"].append(new); save_all(); st.rerun()
    for i in mein_h["einkauf"]:
        st.write(f"- {i}")
        if st.button("✓", key=i): mein_h["einkauf"].remove(i); save_all(); st.rerun()

elif menu == "📊 Statistik & Connect":
    st.header("📊 Connect")
    f_input = st.text_input("Freund adden (Name):")
    if st.button("Link"):
        if f_input in alle_daten["haushalte"]:
            mein_h["verlinkt"].append(f_input); save_all(); st.success("Verbunden!")
