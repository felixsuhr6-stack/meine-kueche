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

# --- 2. HILFSFUNKTIONEN ---
def daten_laden():
    try:
        response = requests.get(WEB_APP_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if not isinstance(data, dict) or "haushalte" not in data:
                return {"haushalte": {}, "globale_rezepte": {}, "globale_anleitungen": {}}
            return data
    except:
        pass
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

alle_daten = daten_laden()

# --- 4. LOGIN / REGISTRIERUNG ---
if st.session_state.haushalt is None:
    st.title("👨‍🍳 Küchen-Chef Cloud")
    t1, t2 = st.tabs(["🔐 Login", "📝 Registrieren"])
    
    with t1:
        h_name = st.text_input("Haushalt").strip()
        h_pass = st.text_input("Passwort", type="password")
        if st.button("Anmelden"):
            if h_name in alle_daten["haushalte"] and alle_daten["haushalte"][h_name]['passwort'] == hash_passwort(h_pass):
                st.session_state.haushalt = h_name
                st.rerun()
            else: st.error("Login fehlgeschlagen oder Haushalt existiert nicht.")

    with t2:
        r_name = st.text_input("Neuer Haushalts-Name").strip()
        r_pass = st.text_input("Wunsch-Passwort", type="password")
        if st.button("Konto erstellen"):
            if r_name and r_pass and r_name not in alle_daten["haushalte"]:
                alle_daten["haushalte"][r_name] = {
                    "passwort": hash_passwort(r_pass), 
                    "vorrat": [], 
                    "wochenplan": {t: "-" for t in TAGE}, 
                    "einkauf": [], 
                    "stats": {"weg": 0, "gegessen": 0}, 
                    "verlinkt": []
                }
                daten_speichern(alle_daten)
                st.success("Erstellt! Du kannst dich jetzt einloggen.")
            else: st.warning("Name ungültig oder vergeben.")
    st.stop()

# --- 5. SICHERHEITS-CHECK (Verhindert KeyError) ---
if st.session_state.haushalt not in alle_daten["haushalte"]:
    st.error("Sitzung abgelaufen oder Haushalt nicht in Cloud gefunden.")
    if st.button("Zurück zum Login"):
        st.session_state.haushalt = None
        st.rerun()
    st.stop()

# --- 6. HAUPT-APP ---
mein_h = alle_daten["haushalte"][st.session_state.haushalt]
menu = st.sidebar.radio("Menü", ["📦 Vorrat", "🍳 Was kochen?", "📖 Rezeptbuch", "📅 Wochenplan", "🛒 Einkauf"])

if st.sidebar.button("Logout"):
    st.session_state.haushalt = None
    st.rerun()

# --- VORRAT ---
if menu == "📦 Vorrat":
    st.header("📦 Vorrat")
    with st.expander("➕ Artikel hinzufügen"):
        with st.form("neu_item"):
            n = st.text_input("Name")
            c1, c2 = st.columns(2)
            m = c1.number_input("Menge", 0.0, value=1.0)
            e = c2.selectbox("Einheit", ["g", "kg", "ml", "L", "Stück"])
            o = st.selectbox("Ort", ORTE)
            if st.form_submit_button("Speichern"):
                if n:
                    mein_h["vorrat"].append({"artikel": n, "menge": m, "einheit": e, "ort": o})
                    daten_speichern(alle_daten); st.rerun()

    for ort in ORTE:
        items = [i for i in mein_h["vorrat"] if i.get('ort') == ort]
        if items:
            st.subheader(f"📍 {ort}")
            for i in items:
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{i['artikel']}** ({i['menge']} {i['einheit']})")
                if c2.button("🗑️", key=f"del_{i['artikel']}{ort}{i['menge']}"):
                    mein_h["vorrat"].remove(i)
                    daten_speichern(alle_daten); st.rerun()

# --- REZEPTBUCH ---
elif menu == "📖 Rezeptbuch":
    st.header("📖 Globales Rezeptbuch")
    with st.expander("➕ Neues Rezept erstellen"):
        r_name = st.text_input("Name des Gerichts")
        if 'temp_zutaten' not in st.session_state: st.session_state.temp_zutaten = {}
        
        c1, c2, c3 = st.columns([2,1,1])
        z_n = c1.text_input("Zutat (z.B. Mehl)")
        z_m = c2.number_input("Menge", 0.0)
        if c3.button("Zutat +"):
            if z_n: st.session_state.temp_zutaten[z_n] = z_m; st.rerun()
        
        st.write("Aktuelle Zutaten:", st.session_state.temp_zutaten)
        r_anl = st.text_area("Anleitung")
        
        if st.button("Rezept speichern"):
            if r_name and st.session_state.temp_zutaten:
                alle_daten["globale_rezepte"][r_name] = st.session_state.temp_zutaten
                alle_daten["globale_anleitungen"][r_name] = r_anl
                st.session_state.temp_zutaten = {}
                daten_speichern(alle_daten); st.success("Gespeichert!"); st.rerun()

    for r in alle_daten["globale_rezepte"]:
        with st.expander(f"🍽️ {r}"):
            st.write("**Zutaten:**", alle_daten["globale_rezepte"][r])
            st.write("**Anleitung:**", alle_daten["globale_anleitungen"].get(r, ""))

# --- WAS KOCHEN? ---
elif menu == "🍳 Was kochen?":
    st.header("🍳 Intelligenter Koch-Check")
    st.write("Hier siehst du, was du mit deinen Vorräten kochen kannst.")
    
    gekocht = False
    for r_name, zutaten in alle_daten["globale_rezepte"].items():
        kann_kochen = True
        fehlend = []
        
        for z_name, z_menge in zutaten.items():
            ist_menge = sum([i['menge'] for i in mein_h["vorrat"] if z_name.lower() in i['artikel'].lower()])
            if ist_menge < z_menge:
                kann_kochen = False
                fehlend.append(f"{z_name} ({z_menge - ist_menge} fehlen)")
        
        if kann_kochen:
            st.success(f"✅ **{r_name}** - Alle Zutaten sind da!")
            if st.button(f"{r_name} jetzt kochen", key=f"cook_{r_name}"):
                for z_name, z_menge in zutaten.items():
                    bedarf = z_menge
                    for i in mein_h["vorrat"]:
                        if z_name.lower() in i['artikel'].lower() and bedarf > 0:
                            take = min(i['menge'], bedarf)
                            i['menge'] -= take
                            bedarf -= take
                mein_h["vorrat"] = [x for x in mein_h["vorrat"] if x['menge'] > 0]
                daten_speichern(alle_daten); st.balloons(); st.rerun()
        else:
            with st.expander(f"❌ {r_name} (Zutaten fehlen)"):
                st.write("Es fehlt:", fehlend)

# --- EINKAUF ---
elif menu == "🛒 Einkauf":
    st.header("🛒 Einkaufsliste")
    neu = st.text_input("Notiz")
    if st.button("Hinzufügen"):
        mein_h["einkauf"].append(neu); daten_speichern(alle_daten); st.rerun()
    for i in mein_h["einkauf"]:
        if st.button(f"Gekauft: {i}"):
            mein_h["einkauf"].remove(i); daten_speichern(alle_daten); st.rerun()
