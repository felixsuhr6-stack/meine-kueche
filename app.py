import streamlit as st
import json
import hashlib
import requests
from fpdf import FPDF
from datetime import datetime, date

# --- KONFIGURATION ---
# Deine Google Apps Script URL ist jetzt hier fest eingetragen:
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyh6FaOQeXodvSLfCXFq-dUIP-BHhzqcuItXrbboxsM2FdWCaPa9udeUHv2HEJ5zi4JDg/exec"

ORTE = ["Kühlschrank", "Vorratsregal", "Tiefkühler", "Gewürzschrank", "Keller", "Sonstiges"]
TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
ADMIN_USER = "admin"
ADMIN_PASS = "admin" # Kannst du hier ändern

# --- DATENBANK FUNKTIONEN (GOOGLE SHEETS) ---
def daten_laden():
    try:
        # Wir fragen das Google Script nach dem Inhalt
        response = requests.get(WEB_APP_URL)
        if response.status_code == 200:
            data = response.json()
            
            # Falls das Sheet komplett leer ist (erster Start)
            if not data:
                 data = {"haushalte": {}, "globale_rezepte": {}, "globale_anleitungen": {}}

            # --- NOTFALL-STRUKTUR-CHECK ---
            if "haushalte" not in data and "globale_rezepte" not in data:
                 # Falls alte Datenstruktur erkannt wird
                old_data = data.copy() if data else {}
                data = {"haushalte": old_data, "globale_rezepte": {}, "globale_anleitungen": {}}

            # Sicherstellen, dass Haupt-Keys da sind
            if "globale_rezepte" not in data: data["globale_rezepte"] = {}
            if "globale_anleitungen" not in data: data["globale_anleitungen"] = {}
            if "haushalte" not in data: data["haushalte"] = {}
            return data
        else:
            return {"globale_rezepte": {}, "globale_anleitungen": {}, "haushalte": {}}
    except Exception as e:
        # Falls kein Internet oder URL falsch
        st.error(f"Verbindungsfehler: {e}")
        return {"globale_rezepte": {}, "globale_anleitungen": {}, "haushalte": {}}

def daten_speichern(alle_daten):
    try:
        # Wir senden das komplette JSON an das Google Script
        requests.post(WEB_APP_URL, json=alle_daten)
    except Exception as e:
        st.error(f"Fehler beim Speichern in die Cloud: {e}")

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
        # Encoding fix für Umlaute im PDF
        text = f"- {item}".encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(200, 10, txt=text, ln=True)
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- SETUP ---
st.set_page_config(page_title="Küchen-Chef Cloud", layout="wide", page_icon="☁️")

def apply_dark_mode():
    st.markdown("""<style>.stApp { background-color: #1E1E1E; color: white; } div[data-testid="stSidebar"] { background-color: #262730; } .stTextInput>div>div>input, .stTextArea>div>div>textarea { color: black; }</style>""", unsafe_allow_html=True)

if 'haushalt' not in st.session_state: st.session_state.haushalt = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

# Daten initial laden (aus der Cloud!)
alle_daten = daten_laden()

def save_all():
    daten_speichern(alle_daten)

# --- LOGIN SCREEN ---
if st.session_state.haushalt is None and not st.session_state.is_admin:
    st.header("☁️ Küchen-Chef Cloud Login")
    
    # ADMIN LOGIN
    with st.expander("🛠️ Entwickler-Login"):
        a_user = st.text_input("Admin Name")
        a_pass = st.text_input("Admin Passwort", type="password")
        if st.button("Als Entwickler starten"):
            if a_user == ADMIN_USER and a_pass == ADMIN_PASS:
                st.session_state.is_admin = True
                st.session_state.haushalt = "ADMIN"
                st.rerun()
            else: st.error("Zugriff verweigert!")

    # NORMALER LOGIN
    if c2.form_submit_button("Registrieren"):
            if h_name and h_pass and h_name not in alle_daten["haushalte"] and h_name != ADMIN_USER:
                # 1. Account lokal im Programm erstellen
                alle_daten["haushalte"][h_name] = {
                    "passwort": hash_passwort(h_pass), "vorrat": [], 
                    "wochenplan": {t: "-" for t in TAGE}, "einkauf": [], 
                    "stats": {"weg": 0, "gegessen": 0}, "verlinkt": []
                }
                
                # 2. Versuchen an Google zu senden
                try:
                    res = requests.post(WEB_APP_URL, json=alle_daten)
                    if res.status_code == 200:
                        st.success(f"✅ Account '{h_name}' erfolgreich in der Cloud gespeichert! Bitte jetzt anmelden.")
                    else:
                        st.error(f"❌ Google hat die Daten abgelehnt (Fehler {res.status_code}). Hast du 'Jeder' ausgewählt?")
                except Exception as e:
                    st.error(f"❌ Verbindung zur Cloud fehlgeschlagen: {e}")
            else:
                st.warning("Name ungültig oder existiert bereits.")

# --- SIDEBAR ---
h_name = st.session_state.haushalt
st.sidebar.title(f"👤 {h_name}")
dark_mode = st.sidebar.checkbox("🌑 Dark Mode", value=True)
if dark_mode: apply_dark_mode()

if st.sidebar.button("Logout"):
    st.session_state.haushalt = None
    st.session_state.is_admin = False
    st.rerun()

# ==========================================
#         ENTWICKLER / ADMIN BEREICH
# ==========================================
if st.session_state.is_admin:
    st.title("🛠️ Cloud-Konsole (Admin)")
    st.success("Verbindung zur Google Tabelle steht.")
    
    admin_menu = st.sidebar.radio("Admin Menü", ["👥 User-Verwaltung", "💾 Datenbank Raw", "📖 Rezepte bearbeiten"])
    
    if admin_menu == "👥 User-Verwaltung":
        st.subheader("User verwalten")
        users = list(alle_daten["haushalte"].keys())
        if not users: st.info("Keine User.")
        for user in users:
            with st.expander(f"👤 {user}"):
                st.write(f"Vorrat: {len(alle_daten['haushalte'][user]['vorrat'])} Artikel")
                new_pw = st.text_input(f"Neues PW für {user}", key=f"pw_{user}")
                if st.button("Passwort ändern", key=f"btn_{user}"):
                    alle_daten["haushalte"][user]["passwort"] = hash_passwort(new_pw)
                    save_all(); st.success("Geändert!")
                if st.button("Löschen", key=f"del_{user}"):
                    del alle_daten["haushalte"][user]; save_all(); st.rerun()

    elif admin_menu == "💾 Datenbank Raw":
        st.subheader("JSON Rohdaten")
        st.write("Daten aus der Cloud:")
        st.json(alle_daten)

    elif admin_menu == "📖 Rezepte bearbeiten":
        st.subheader("Globale Rezepte")
        for r in list(alle_daten["globale_rezepte"].keys()):
            if st.button(f"Löschen: {r}", key=f"adel_{r}"):
                del alle_daten["globale_rezepte"][r]
                if r in alle_daten["globale_anleitungen"]: del alle_daten["globale_anleitungen"][r]
                save_all(); st.rerun()

# ==========================================
#         NORMALER USER BEREICH
# ==========================================
else:
    mein_h = alle_daten["haushalte"][h_name]
    
    # Reparatur zur Laufzeit (Falls Felder fehlen)
    if "verlinkt" not in mein_h: mein_h["verlinkt"] = []
    if "stats" not in mein_h: mein_h["stats"] = {"weg": 0, "gegessen": 0}
    if "wochenplan" not in mein_h: mein_h["wochenplan"] = {t: "-" for t in TAGE}
    if "einkauf" not in mein_h: mein_h["einkauf"] = []
    if "vorrat" not in mein_h: mein_h["vorrat"] = []

    menu = st.sidebar.radio("Menü", ["📅 Wochenplan", "📦 Vorrat", "➕ Neu", "📖 Rezepte", "🍳 Kochen", "🛒 Einkauf", "📊 Connect"])

    with st.sidebar.expander("🧮 Umrechner"):
        wert = st.number_input("Wert", value=100.0)
        von = st.selectbox("Von", ["g", "kg", "ml", "L"])
        if von == "g": st.write(f"= {wert/1000} kg")
        elif von == "kg": st.write(f"= {wert*1000} g")
        elif von == "ml": st.write(f"= {wert/1000} L")
        elif von == "L": st.write(f"= {wert*1000} ml")

    if menu == "📅 Wochenplan":
        st.header("📅 Wochenplaner")
        rezepte_liste = ["-"] + list(alle_daten["globale_rezepte"].keys())
        c1, c2 = st.columns([2,1])
        with c1:
            with st.form("w_form"):
                for t in TAGE:
                    aktuell = mein_h["wochenplan"].get(t, "-")
                    if aktuell not in rezepte_liste: aktuell = "-"
                    mein_h["wochenplan"][t] = st.selectbox(t, rezepte_liste, index=rezepte_liste.index(aktuell))
                if st.form_submit_button("Speichern"): save_all(); st.success("Gespeichert!")
        with c2:
            st.write("---")
            if st.button("🛒 Zutaten auf Liste"):
                c = 0
                for t, g in mein_h["wochenplan"].items():
                    if g != "-":
                        for z, m in alle_daten["globale_rezepte"][g].items():
                            mein_h["einkauf"].append(f"{z} ({m})"); c+=1
                save_all(); st.success(f"{c} Zutaten hinzugefügt!")
            pdf_text = [f"{t}: {mein_h['wochenplan'][t]}" for t in TAGE]
            st.download_button("📄 PDF", erstelle_pdf(pdf_text, "Wochenplan"), "plan.pdf")

    elif menu == "📦 Vorrat":
        st.header("📦 Vorräte")
        t1, t2 = st.tabs(["🏠 Mein Vorrat", "🔗 Freunde"])
        with t1:
            mode = st.radio("Sort:", ["MHD", "A-Z"], horizontal=True)
            for ort in ORTE:
                items = [i for i in mein_h["vorrat"] if i.get('ort') == ort]
                if items:
                    items.sort(key=lambda x: x.get('mhd', '9999') if "MHD" in mode else x.get('artikel', '').lower())
                    with st.expander(f"📍 {ort} ({len(items)})", expanded=True):
                        for item in items:
                            c1, c2, c3, c4 = st.columns([0.5, 4, 1, 1])
                            c2.write(f"**{item['artikel']}** ({item['menge']} {item['einheit']}) - {item['mhd']}")
                            if c3.button("🍽️", key=f"e_{item['artikel']}{item['mhd']}"):
                                mein_h["vorrat"].remove(item); mein_h["stats"]["gegessen"] += 1; save_all(); st.rerun()
                            if c4.button("🗑️", key=f"t_{item['artikel']}{item['mhd']}"):
                                mein_h["vorrat"].remove(item); mein_h["stats"]["weg"] += 1; save_all(); st.rerun()
        with t2:
            if not mein_h["verlinkt"]: st.info("Niemand verknüpft.")
            for f in mein_h["verlinkt"]:
                if f in alle_daten["haushalte"]:
                    with st.expander(f"👤 {f}"):
                        for i in alle_daten["haushalte"][f]["vorrat"]:
                            c1, c2 = st.columns([4,1])
                            c1.write(f"{i['artikel']} ({i['menge']} {i['einheit']})")
                            if c2.button("Nehmen", key=f"take_{f}_{i['artikel']}"):
                                alle_daten["haushalte"][f]["vorrat"].remove(i)
                                mein_h["vorrat"].append(i); save_all(); st.rerun()

    elif menu == "➕ Neu":
        st.header("➕ Neu")
        with st.form("n"):
            n = st.text_input("Name"); o = st.selectbox("Ort", ORTE)
            c1, c2 = st.columns(2)
            m = c1.number_input("Menge", 1.0); e = c2.selectbox("Einh.", ["Stück", "g", "kg", "ml", "L", "Pk."])
            d = st.date_input("MHD")
            if st.form_submit_button("Speichern"):
                mein_h["vorrat"].append({"artikel": n, "menge": m, "einheit": e, "ort": o, "mhd": str(d)})
                save_all(); st.success("Gespeichert!")

    elif menu == "📖 Rezepte":
        st.header("📖 Rezepte")
        with st.expander("➕ Neues Rezept"):
            rn = st.text_input("Name")
            st.write("**Zutaten:**")
            if 'tmp_z' not in st.session_state: st.session_state.tmp_z = {}
            c1, c2, c3 = st.columns([2,1,1])
            zn = c1.text_input("Zutat"); zm = c2.number_input("Menge", 0.0)
            if c3.button("Dazu"): st.session_state.tmp_z[zn] = zm; st.rerun()
            st.write(st.session_state.tmp_z)
            if st.button("Reset"): st.session_state.tmp_z = {}; st.rerun()
            anl = st.text_area("Anleitung")
            if st.button("Global speichern"):
                if rn:
                    alle_daten["globale_rezepte"][rn] = st.session_state.tmp_z
                    alle_daten["globale_anleitungen"][rn] = anl
                    st.session_state.tmp_z = {}; save_all(); st.rerun()
        
        for r in alle_daten["globale_rezepte"]:
            with st.expander(f"🍽️ {r}"):
                st.write(alle_daten["globale_rezepte"][r])
                st.info(alle_daten["globale_anleitungen"].get(r, ""))

    elif menu == "🍳 Kochen":
        st.header("🍳 Kochen")
        tab1, tab2 = st.tabs(["Rezept", "Rest-O-Mat"])
        with tab1:
            w = st.selectbox("Rezept", ["-"] + list(alle_daten["globale_rezepte"].keys()))
            if w != "-":
                st.write(alle_daten["globale_anleitungen"].get(w, ""))
                req = alle_daten["globale_rezepte"][w]; miss = []
                for z, m in req.items():
                    ist = sum([i['menge'] for i in mein_h["vorrat"] if z.lower() in i['artikel'].lower()])
                    if ist < m: st.error(f"Fehlt: {z} ({m-ist})"); miss.append(z)
                    else: st.success(f"Ok: {z}")
                if not miss and st.button("Kochen"):
                    for z, m in req.items():
                        todo = m
                        for i in mein_h["vorrat"]:
                            if z.lower() in i['artikel'].lower():
                                take = min(i['menge'], todo); i['menge'] -= take; todo -= take
                    mein_h["vorrat"] = [x for x in mein_h["vorrat"] if x['menge'] > 0]
                    mein_h["stats"]["gegessen"] += 1; save_all(); st.balloons(); st.rerun()
        with tab2:
            s = st.text_input("Zutat suchen")
            if s: st.write([r for r, z in alle_daten["globale_rezepte"].items() if any(s.lower() in k.lower() for k in z)])

    elif menu == "🛒 Einkauf":
        st.header("🛒 Liste")
        new = st.text_input("Item")
        if st.button("Add") and new: mein_h["einkauf"].append(new); save_all(); st.rerun()
        for i in mein_h["einkauf"]:
            c1, c2 = st.columns([4,1])
            c1.write(f"- {i}")
            if c2.button("✓", key=f"s_{i}"): mein_h["einkauf"].remove(i); save_all(); st.rerun()
        if mein_h["einkauf"]:
            st.download_button("PDF", erstelle_pdf(mein_h["einkauf"], "Einkauf"), "liste.pdf")

    elif menu == "📊 Connect":
        st.header("📊 Connect")
        st.write(f"Du bist: **{h_name}**")
        f = st.text_input("Freund adden")
        if st.button("Link") and f in alle_daten["haushalte"]:
            mein_h["verlinkt"].append(f); save_all(); st.success("Verbunden!")
        st.write("Freunde:", mein_h["verlinkt"])
        c1, c2 = st.columns(2)
        c1.metric("Gegessen", mein_h["stats"]["gegessen"]); c2.metric("Weg", mein_h["stats"]["weg"])
