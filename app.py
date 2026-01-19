import streamlit as st
import json
import hashlib
import requests
from fpdf import FPDF
from datetime import datetime, date

# --- 1. KONFIGURATION ---
# Deine Google Apps Script URL:
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbz0s1Hu4BvYzI9-Jhml8iI4OiGagRmMyyHU-UwXNFuragMKkYB3pmDW0J3xxqexyNpYNQ/exec"

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
                "stats": {"weg": 0, "gegessen": 0}, "verlinkt": []
            }
            with st.spinner("Speichere in Cloud..."):
                daten_speichern(alle_daten)
            st.success("Erfolgreich registriert! Bitte jetzt anmelden.")
        else: st.warning("Name ungültig oder bereits vergeben.")
    st.stop()

# --- 5. HAUPT-APP ---
h_name = st.session_state.haushalt
st.sidebar.title(f"👤 {h_name}")
if st.sidebar.checkbox("🌑 Dark Mode", value=True): apply_dark_mode()
if st.sidebar.button("Logout"):
    st.session_state.haushalt = None
    st.session_state.is_admin = False
    st.rerun()

# --- ADMIN BEREICH ---
if st.session_state.is_admin:
    st.title("🛠️ Admin Konsole")
    admin_menu = st.sidebar.radio("Admin Menü", ["👥 User-Verwaltung", "💾 Datenbank Raw"])
    
    if admin_menu == "👥 User-Verwaltung":
        for user in list(alle_daten["haushalte"].keys()):
            with st.expander(f"Haushalt: {user}"):
                new_pw = st.text_input(f"Neues PW für {user}", key=f"pw_{user}")
                if st.button(f"Passwort setzen", key=f"btn_{user}"):
                    alle_daten["haushalte"][user]["passwort"] = hash_passwort(new_pw)
                    daten_speichern(alle_daten); st.success("Geändert!")
                if st.button(f"Löschen", key=f"del_{user}"):
                    del alle_daten["haushalte"][user]; daten_speichern(alle_daten); st.rerun()

    elif admin_menu == "💾 Datenbank Raw":
        st.json(alle_daten)

# --- USER BEREICH ---
else:
    mein_h = alle_daten["haushalte"][h_name]
    menu = st.sidebar.radio("Menü", ["📅 Wochenplan", "📦 Vorrat", "➕ Neu", "📖 Rezepte", "🍳 Kochen", "🛒 Einkauf", "📊 Connect"])

    if menu == "📅 Wochenplan":
        st.header("📅 Wochenplan")
        rezepte = ["-"] + list(alle_daten["globale_rezepte"].keys())
        with st.form("w_form"):
            for t in TAGE:
                mein_h["wochenplan"][t] = st.selectbox(t, rezepte, index=rezepte.index(mein_h["wochenplan"].get(t, "-")))
            if st.form_submit_button("Speichern"): daten_speichern(alle_daten); st.success("Plan gespeichert!")

    elif menu == "📦 Vorrat":
        st.header("📦 Vorrat")
        for ort in ORTE:
            items = [i for i in mein_h["vorrat"] if i.get('ort') == ort]
            if items:
                with st.expander(f"📍 {ort}"):
                    for item in items:
                        c1, c2, c3 = st.columns([4,1,1])
                        c1.write(f"**{item['artikel']}** ({item['menge']} {item['einheit']}) - MHD: {item['mhd']}")
                        if c2.button("🍽️", key=f"e_{item['artikel']}{item['mhd']}"):
                            mein_h["vorrat"].remove(item); mein_h["stats"]["gegessen"] += 1; daten_speichern(alle_daten); st.rerun()
                        if c3.button("🗑️", key=f"t_{item['artikel']}{item['mhd']}"):
                            mein_h["vorrat"].remove(item); mein_h["stats"]["weg"] += 1; daten_speichern(alle_daten); st.rerun()

    elif menu == "➕ Neu":
        st.header("➕ Artikel hinzufügen")
        with st.form("neu_item"):
            n = st.text_input("Name"); o = st.selectbox("Ort", ORTE)
            m = st.number_input("Menge", 1.0); e = st.selectbox("Einh.", ["Stück", "g", "kg", "ml", "L"])
            d = st.date_input("MHD")
            if st.form_submit_button("Hinzufügen"):
                mein_h["vorrat"].append({"artikel": n, "menge": m, "einheit": e, "ort": o, "mhd": str(d)})
                daten_speichern(alle_daten); st.success("Hinzugefügt!")

    elif menu == "📖 Rezepte":
        st.header("📖 Rezepte")
        with st.expander("➕ Neues Rezept erstellen"):
            rn = st.text_input("Rezept Name")
            if 'tmp_z' not in st.session_state: st.session_state.tmp_z = {}
            c1, c2, c3 = st.columns([2,1,1])
            zn = c1.text_input("Zutat"); zm = c2.number_input("Menge", 0.0)
            if c3.button("Zutat +"): st.session_state.tmp_z[zn] = zm; st.rerun()
            st.write(st.session_state.tmp_z)
            anl = st.text_area("Anleitung")
            if st.button("Rezept Speichern"):
                alle_daten["globale_rezepte"][rn] = st.session_state.tmp_z
                alle_daten["globale_anleitungen"][rn] = anl
                st.session_state.tmp_z = {}; daten_speichern(alle_daten); st.success("Gespeichert!")

    elif menu == "🍳 Kochen":
        st.header("🍳 Kochen")
        wahl = st.selectbox("Was kochst du?", ["-"] + list(alle_daten["globale_rezepte"].keys()))
        if wahl != "-":
            req = alle_daten["globale_rezepte"][wahl]
            st.info(alle_daten["globale_anleitungen"].get(wahl, ""))
            if st.button("Kochen & Vorrat abziehen"):
                for z, m in req.items():
                    for i in mein_h["vorrat"]:
                        if z.lower() in i['artikel'].lower():
                            take = min(i['menge'], m); i['menge'] -= take
                mein_h["vorrat"] = [x for x in mein_h["vorrat"] if x['menge'] > 0]
                daten_speichern(alle_daten); st.balloons(); st.rerun()

    elif menu == "🛒 Einkauf":
        st.header("🛒 Einkaufsliste")
        neu = st.text_input("Was fehlt?")
        if st.button("Dazu") and neu: 
            mein_h["einkauf"].append(neu); daten_speichern(alle_daten); st.rerun()
        for i in mein_h["einkauf"]:
            if st.button(f"✓ {i}"):
                mein_h["einkauf"].remove(i); daten_speichern(alle_daten); st.rerun()

    elif menu == "📊 Connect":
        st.header("📊 Statistik & Verbindung")
        st.write(f"Dein Haushalts-Code: **{h_name}**")
        f_name = st.text_input("Freund hinzufügen (Name)")
        if st.button("Verbinden"):
            if f_name in alle_daten["haushalte"]:
                mein_h["verlinkt"].append(f_name); daten_speichern(alle_daten); st.success("Verbunden!")
        st.metric("Gegessen", mein_h["stats"]["gegessen"])
        st.metric("Weggeworfen", mein_h["stats"]["weg"])
