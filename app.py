import streamlit as st
import json
import hashlib
import requests
from fpdf import FPDF
from datetime import datetime, date

# --- 1. CONFIG & CLOUD ---
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyh6FaOQeXodvSLfCXFq-dUIP-BHhzqcuItXrbboxsM2FdWCaPa9udeUHv2HEJ5zi4JDg/exec"

ORTE = ["Kühlschrank", "Vorratsregal", "Tiefkühler", "Gewürzschrank", "Keller", "Sonstiges"]
TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

# --- 2. HILFSFUNKTIONEN ---
def daten_laden():
    try:
        response = requests.get(WEB_APP_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if not data or "haushalte" not in data:
                data = {"haushalte": {}, "globale_rezepte": {}, "globale_anleitungen": {}}
            return data
        return {"haushalte": {}, "globale_rezepte": {}, "globale_anleitungen": {}}
    except:
        return {"haushalte": {}, "globale_rezepte": {}, "globale_anleitungen": {}}

def daten_speichern(alle_daten):
    try:
        requests.post(WEB_APP_URL, json=alle_daten, timeout=10)
    except Exception as e:
        st.error(f"Cloud-Fehler: {e}")

def hash_passwort(passwort):
    return hashlib.sha256(str.encode(passwort)).hexdigest()

# --- 3. INITIALISIERUNG ---
st.set_page_config(page_title="Küchen-Chef Pro Max", layout="wide", page_icon="👨‍🍳")
if 'haushalt' not in st.session_state: st.session_state.haushalt = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

alle_daten = daten_laden()

# --- 4. LOGIN ---
if st.session_state.haushalt is None:
    st.title("👨‍🍳 Küchen-Chef Cloud")
    tab_login, tab_reg = st.tabs(["🔐 Login", "📝 Registrieren"])
    
    with tab_login:
        h_name = st.text_input("Haushalt").strip()
        h_pass = st.text_input("Passwort", type="password")
        if st.button("Anmelden"):
            if h_name in alle_daten["haushalte"] and alle_daten["haushalte"][h_name]['passwort'] == hash_passwort(h_pass):
                st.session_state.haushalt = h_name
                st.rerun()
            else: st.error("Login fehlgeschlagen.")

    with tab_reg:
        r_name = st.text_input("Neuer Haushalt").strip()
        r_pass = st.text_input("Wunsch-Passwort", type="password")
        if st.button("Konto erstellen"):
            if r_name and r_pass and r_name not in alle_daten["haushalte"]:
                alle_daten["haushalte"][r_name] = {"passwort": hash_passwort(r_pass), "vorrat": [], "wochenplan": {t: "-" for t in TAGE}, "einkauf": [], "stats": {"weg": 0, "gegessen": 0}, "verlinkt": []}
                daten_speichern(alle_daten); st.success("Erstellt!")
    st.stop()

# --- 5. HAUPT-APP ---
mein_h = alle_daten["haushalte"][st.session_state.haushalt]
menu = st.sidebar.radio("Menü", ["📦 Vorrat", "📅 Wochenplan", "🍳 Was kochen?", "📖 Rezeptbuch", "🛒 Einkauf", "📊 Connect"])

if st.sidebar.button("Logout"):
    st.session_state.haushalt = None
    st.rerun()

# --- VORRAT ---
if menu == "📦 Vorrat":
    st.header("📦 Vorrat")
    with st.expander("➕ Hinzufügen"):
        with st.form("n"):
            n = st.text_input("Name"); m = st.number_input("Menge", 0.1, value=1.0); e = st.selectbox("Einheit", ["g", "kg", "ml", "L", "Stück"])
            o = st.selectbox("Ort", ORTE); d = st.date_input("MHD")
            if st.form_submit_button("OK"):
                mein_h["vorrat"].append({"artikel": n, "menge": m, "einheit": e, "ort": o, "mhd": str(d)})
                daten_speichern(alle_daten); st.rerun()

    for ort in ORTE:
        items = [i for i in mein_h["vorrat"] if i.get('ort') == ort]
        if items:
            with st.expander(f"📍 {ort}", expanded=True):
                for i in items:
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"**{i['artikel']}** ({i['menge']} {i['einheit']})")
                    if c2.button("🗑️", key=f"del_{i['artikel']}{i['mhd']}"):
                        mein_h["vorrat"].remove(i); daten_speichern(alle_daten); st.rerun()

# --- REZEPTBUCH (Detailliert) ---
elif menu == "📖 Rezeptbuch":
    st.header("📖 Rezeptbuch")
    with st.expander("➕ Neues Rezept mit Zutatenliste"):
        r_name = st.text_input("Name des Gerichts")
        if 'z_liste' not in st.session_state: st.session_state.z_liste = {}
        
        c1, c2, c3 = st.columns([2,1,1])
        z_n = c1.text_input("Zutat")
        z_m = c2.number_input("Menge", 0.0)
        if c3.button("Zutat hinzufügen"):
            st.session_state.z_liste[z_n] = z_m; st.rerun()
        
        st.write("Zutaten:", st.session_state.z_liste)
        r_anl = st.text_area("Zubereitung")
        
        if st.button("Rezept speichern"):
            alle_daten["globale_rezepte"][r_name] = st.session_state.z_liste
            alle_daten["globale_anleitungen"][r_name] = r_anl
            st.session_state.z_liste = {}
            daten_speichern(alle_daten); st.success("Gespeichert!"); st.rerun()

    for r in alle_daten["globale_rezepte"]:
        with st.expander(f"🍽️ {r}"):
            st.write("**Zutaten:**", alle_daten["globale_rezepte"][r])
            st.write("**Anleitung:**", alle_daten["globale_anleitungen"].get(r))

# --- WAS KOCHEN? (Intelligente Suche) ---
elif menu == "🍳 Was kochen?":
    st.header("🍳 Rezept-Check")
    st.write("Folgende Rezepte kannst du mit deinem Vorrat kochen:")
    
    for r_name, zutaten in alle_daten["globale_rezepte"].items():
        kann_kochen = True
        fehlend = []
        
        for z_name, z_menge in zutaten.items():
            # Prüfen ob Zutat im Vorrat (Name muss vorkommen)
            vorrat_menge = sum([i['menge'] for i in mein_h["vorrat"] if z_name.lower() in i['artikel'].lower()])
            if vorrat_menge < z_menge:
                kann_kochen = False
                fehlend.append(f"{z_name} (fehlen {z_menge - vorrat_menge})")
        
        if kann_kochen:
            with st.container():
                st.success(f"✅ **{r_name}** - Alles da!")
                if st.button(f"{r_name} jetzt kochen", key=f"cook_{r_name}"):
                    # Vorrat abziehen
                    for z_name, z_menge in zutaten.items():
                        bedarf = z_menge
                        for i in mein_h["vorrat"]:
                            if z_name.lower() in i['artikel'].lower() and bedarf > 0:
                                take = min(i['menge'], bedarf)
                                i['menge'] -= take
                                bedarf -= take
                    mein_h["vorrat"] = [x for x in mein_h["vorrat"] if x['menge'] > 0]
                    mein_h["stats"]["gegessen"] += 1
                    daten_speichern(alle_daten); st.balloons(); st.rerun()
        else:
            with st.expander(f"❌ {r_name} (Es fehlen Zutaten)"):
                st.write("Fehlend:", fehlend)

# --- EINKAUF ---
elif menu == "🛒 Einkauf":
    st.header("🛒 Einkaufsliste")
    neu = st.text_input("Hinzufügen")
    if st.button("Add") and neu: mein_h["einkauf"].append(neu); daten_speichern(alle_daten); st.rerun()
    for i in mein_h["einkauf"]:
        if st.button(f"Gekauft: {i}"): mein_h["einkauf"].remove(i); daten_speichern(alle_daten); st.rerun()

# --- CONNECT ---
elif menu == "📊 Connect":
    st.header("📊 Connect")
    f_name = st.text_input("Haushaltsname von Freunden")
    if st.button("Link"):
        if f_name in alle_daten["haushalte"]: mein_h["verlinkt"].append(f_name); daten_speichern(alle_daten); st.success("OK!")
    for f in mein_h.get("verlinkt", []):
        with st.expander(f"Vorrat von {f}"):
            st.write(alle_daten["haushalte"][f]["vorrat"])
