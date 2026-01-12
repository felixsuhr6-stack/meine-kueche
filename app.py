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

# --- SETUP & DARK MODE ---
st.set_page_config(page_title="Küchen-Chef Connect", layout="wide", page_icon="🍎")

def apply_dark_mode():
    st.markdown("""
    <style>
    .stApp { background-color: #1E1E1E; color: white; }
    div[data-testid="stSidebar"] { background-color: #262730; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea { color: black; }
    </style>
    """, unsafe_allow_html=True)

if 'haushalt' not in st.session_state:
    st.session_state.haushalt = None

alle_daten = daten_laden()

# --- LOGIN SCREEN ---
if st.session_state.haushalt is None:
    st.header("🔐 Küchen-Chef Login")
    with st.form("login_form"):
        h_name = st.text_input("Haushalts-Name (für Freunde sichtbar)").strip()
        h_pass = st.text_input("Passwort", type="password")
        c1, c2 = st.columns(2)
        if c1.form_submit_button("Anmelden"):
            if h_name in alle_daten["haushalte"] and alle_daten["haushalte"][h_name]['passwort'] == hash_passwort(h_pass):
                st.session_state.haushalt = h_name; st.rerun()
            else: st.error("Name oder Passwort falsch!")
        if c2.form_submit_button("Neu Registrieren"):
            if h_name and h_pass and h_name not in alle_daten["haushalte"]:
                alle_daten["haushalte"][h_name] = {
                    "passwort": hash_passwort(h_pass), "vorrat": [], 
                    "wochenplan": {t: "-" for t in TAGE}, "einkauf": [], 
                    "stats": {"weg": 0, "gegessen": 0}, "verlinkt": []
                }
                daten_speichern(alle_daten); st.success("Konto erstellt! Jetzt anmelden.")
            else: st.warning("Name vergeben oder Felder leer.")
    st.stop()

# --- DATEN DES AKTUELLEN HAUSHALTS ---
h_name = st.session_state.haushalt
mein_h = alle_daten["haushalte"][h_name]

# Kompatibilitäts-Check für alte Accounts
if "verlinkt" not in mein_h: mein_h["verlinkt"] = []
if "stats" not in mein_h: mein_h["stats"] = {"weg": 0, "gegessen": 0}

def save_all():
    daten_speichern(alle_daten)

# --- SIDEBAR ---
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
    st.session_state.haushalt = None; st.rerun()

# --- MODUL 0: WOCHENPLAN ---
if menu == "📅 Wochenplan":
    st.header("📅 Wochenplaner")
    col1, col2 = st.columns([2, 1])
    with col1:
        rezepte_liste = ["-"] + list(alle_daten["globale_rezepte"].keys())
        with st.form("w_form"):
            for t in TAGE:
                aktuell = mein_h["wochenplan"].get(t, "-")
                if aktuell not in rezepte_liste: aktuell = "-"
                mein_h["wochenplan"][t] = st.selectbox(t, rezepte_liste, index=rezepte_liste.index(aktuell))
            if st.form_submit_button("Plan speichern"): save_all(); st.success("Gespeichert!")
    with col2:
        plan_pdf = erstelle_pdf([f"{t}: {mein_h['wochenplan'][t]}" for t in TAGE], "Wochenplan")
        st.download_button("📄 Plan als PDF", plan_pdf, "plan.pdf")
        if st.button("🛒 Alles auf Einkaufsliste"):
            for t, g in mein_h["wochenplan"].items():
                if g != "-":
                    for z, m in alle_daten["globale_rezepte"][g].items():
                        mein_h["einkauf"].append(f"{z} ({m})")
            save_all(); st.success("Zutaten hinzugefügt!")

# --- MODUL 1: VORRAT ---
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
        if not mein_h["verlinkt"]: st.info("Keine Freunde verknüpft.")
        for f_name in mein_h["verlinkt"]:
            if f_name in alle_daten["haushalte"]:
                f_h = alle_daten["haushalte"][f_name]
                with st.expander(f"👤 Kühlschrank von {f_name}"):
                    for i in f_h["vorrat"]:
                        col1, col2 = st.columns([4, 1])
                        col1.write(f"{i['artikel']} ({i['menge']} {i['einheit']})")
                        if col2.button("Ausleihen", key=f"lend_{f_name}_{i['artikel']}"):
                            alle_daten["haushalte"][f_name]["vorrat"].remove(i)
                            mein_h["vorrat"].append(i)
                            save_all(); st.rerun()

# --- MODUL 2: NEU HINZUFÜGEN ---
elif menu == "➕ Neu":
    st.header("➕ Neuen Vorrat eintragen")
    with st.form("n_form"):
        name = st.text_input("Name")
        ort = st.selectbox("Ort", ORTE)
        c1, c2 = st.columns(2)
        menge = c1.number_input("Menge", 1.0)
        einheit = c2.selectbox("Einh.", ["Stück", "g", "kg", "ml", "L", "Pk."])
        mhd = st.date_input("MHD")
        if st.form_submit_button("Speichern"):
            mein_h["vorrat"].append({"artikel": name, "menge": menge, "einheit": einheit, "ort": ort, "mhd": str(mhd)})
            save_all(); st.success("Gespeichert!")

# --- MODUL 3: REZEPTE (GEMEINSAM) ---
elif menu == "📖 Gemeinschafts-Rezepte":
    st.header("📖 Gemeinschafts-Kochbuch")
    with st.expander("➕ Neues Rezept für ALLE hinzufügen"):
        rn = st.text_input("Rezept Name")
        if 'tmp_z' not in st.session_state: st.session_state.tmp_z = {}
        c1, c2, c3 = st.columns([2,1,1])
        zn = c1.text_input("Zutat"); zm = c2.number_input("Menge", 0.1)
        if c3.button("Hinzufügen"): st.session_state.tmp_z[zn] = zm; st.rerun()
        st.write("Zutaten:", st.session_state.tmp_z)
        anl = st.text_area("Anleitung (Schritte)")
        if st.button("Rezept global veröffentlichen"):
            alle_daten["globale_rezepte"][rn] = st.session_state.tmp_z
            alle_daten["globale_anleitungen"][rn] = anl
            st.session_state.tmp_z = {}; save_all(); st.rerun()
    
    for r in list(alle_daten["globale_rezepte"].keys()):
        with st.expander(f"🍽️ {r}"):
            st.write("**Zutaten:**", alle_daten["globale_rezepte"][r])
            st.write("**Anleitung:**", alle_daten["globale_anleitungen"].get(r, "-"))
            if st.button("Löschen für ALLE", key=f"del_{r}"):
                del alle_daten["globale_rezepte"][r]
                if r in alle_daten["globale_anleitungen"]: del alle_daten["globale_anleitungen"][r]
                save_all(); st.rerun()

# --- MODUL 4: KOCHEN ---
elif menu == "🍳 Kochen":
    st.header("🍳 Was kochen wir?")
    tab_k, tab_r = st.tabs(["Kochen", "Rest-O-Mat"])
    with tab_k:
        wahl = st.selectbox("Rezept wählen", ["-"] + list(alle_daten["globale_rezepte"].keys()))
        if wahl != "-":
            st.info(alle_daten["globale_anleitungen"].get(wahl, ""))
            req = alle_daten["globale_rezepte"][wahl]; missing = []
            for z, m in req.items():
                ist = sum([i['menge'] for i in mein_h["vorrat"] if z.lower() in i['artikel'].lower()])
                if ist >= m: st.success(f"✅ {z}")
                else: st.error(f"❌ {z} (Fehlt: {m-ist})"); missing.append(z)
            if not missing and st.button("Kochen & Vorrat abbuchen"):
                for z, m in req.items():
                    todo = m
                    for i in mein_h["vorrat"]:
                        if z.lower() in i['artikel'].lower():
                            t = min(i['menge'], todo); i['menge'] -= t; todo -= t
                mein_h["stats"]["gegessen"] += 1; save_all(); st.balloons(); st.rerun()
    with tab_r:
        s = st.text_input("Suche nach Zutat")
        if s:
            hits = [r for r, zut in alle_daten["globale_rezepte"].items() if any(s.lower() in z.lower() for z in zut)]
            st.write("Gefunden:", hits if hits else "Nichts.")

# --- MODUL 5: EINKAUF ---
elif menu == "🛒 Einkauf":
    st.header("🛒 Einkaufsliste")
    new = st.text_input("Hinzufügen")
    if st.button("OK"): mein_h["einkauf"].append(new); save_all(); st.rerun()
    for i in mein_h["einkauf"]:
        c1, c2 = st.columns([4, 1])
        c1.write(f"- {i}")
        if c2.button("✓", key=f"shop_{i}"): mein_h["einkauf"].remove(i); save_all(); st.rerun()
    if mein_h["einkauf"]:
        pdf = erstelle_pdf(mein_h["einkauf"], "Einkaufsliste")
        st.download_button("📄 PDF Export", pdf, "einkauf.pdf")

# --- MODUL 6: STATISTIK & CONNECT ---
elif menu == "📊 Statistik & Connect":
    st.header("📊 Haushalt & Netzwerk")
    st.subheader("🔗 Mit Freunden verknüpfen")
    st.write(f"Dein Name für andere: **{h_name}**")
    f_input = st.text_input("Name des Freundes eingeben:")
    if st.button("Verbinden"):
        if f_input in alle_daten["haushalte"] and f_input != h_name:
            if f_input not in mein_h["verlinkt"]:
                mein_h["verlinkt"].append(f_input)
                save_all(); st.success(f"Verbunden mit {f_input}!")
            else: st.warning("Bereits verbunden.")
        else: st.error("Haushalt nicht gefunden.")
    
    st.write("Deine Partner:", mein_h["verlinkt"])
    if st.button("Alle Verbindungen trennen"): mein_h["verlinkt"] = []; save_all(); st.rerun()
    
    st.write("---")
    c1, c2 = st.columns(2)
    c1.metric("Gegessen/Gerettet", mein_h["stats"]["gegessen"])
    c2.metric("Weggeworfen", mein_h["stats"]["weg"])
