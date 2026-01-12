import streamlit as st
import json
import os
import hashlib
from datetime import datetime, date
from fpdf import FPDF

# --- KONFIGURATION ---
DATEI_NAME = "multi_haushalt_daten.json"
ORTE = ["Kühlschrank", "Vorratsregal", "Tiefkühler", "Gewürzschrank", "Keller", "Sonstiges"]

# --- FUNKTIONEN ---
def daten_laden():
    if os.path.exists(DATEI_NAME):
        with open(DATEI_NAME, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}
    return {}

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
st.set_page_config(page_title="Küchen-Chef Ultra", layout="wide", page_icon="🍎")

def apply_dark_mode():
    st.markdown("""
    <style>
    .stApp { background-color: #1E1E1E; color: white; }
    div[data-testid="stSidebar"] { background-color: #262730; }
    .stTextInput>div>div>input { color: black; }
    .stTextArea>div>div>textarea { color: black; }
    </style>
    """, unsafe_allow_html=True)

if 'haushalt' not in st.session_state:
    st.session_state.haushalt = None

# --- LOGIN SCREEN ---
if st.session_state.haushalt is None:
    st.header("🔐 Küchen-Chef Login")
    with st.form("login_form"):
        h_name = st.text_input("Haushalts-Name").strip()
        h_pass = st.text_input("Passwort", type="password")
        c1, c2 = st.columns(2)
        if c1.form_submit_button("Anmelden"):
            data = daten_laden()
            if h_name in data and data[h_name]['passwort'] == hash_passwort(h_pass):
                st.session_state.haushalt = h_name; st.rerun()
            else: st.error("Falsch!")
        if c2.form_submit_button("Registrieren"):
            data = daten_laden()
            if h_name and h_pass and h_name not in data:
                # Struktur erweitert um "anleitungen"
                data[h_name] = {
                    "passwort": hash_passwort(h_pass), 
                    "vorrat": [], 
                    "rezepte": {}, 
                    "anleitungen": {}, 
                    "einkauf": [], 
                    "stats": {"weg": 0, "gegessen": 0}
                }
                daten_speichern(data); st.success("Erstellt!")
            else: st.warning("Fehler bei Registrierung")
    st.stop()

# --- HAUPT-APP ---
h_name = st.session_state.haushalt
alle_daten = daten_laden()
mein_h = alle_daten[h_name]

# Sicherstellen, dass neue Felder existieren (für alte Accounts)
if "stats" not in mein_h: mein_h["stats"] = {"weg": 0, "gegessen": 0}
if "anleitungen" not in mein_h: mein_h["anleitungen"] = {}

def save():
    alle_daten[h_name] = mein_h
    daten_speichern(alle_daten)

# --- SIDEBAR ---
st.sidebar.title(f"🏠 {h_name}")
dark_mode = st.sidebar.checkbox("🌑 Dark Mode", value=False)
if dark_mode: apply_dark_mode()

menu = st.sidebar.radio("Menü", ["📦 Vorrat", "➕ Neu", "📖 Rezepte", "🍳 Kochen", "🛒 Einkauf", "📊 Statistik"])

with st.sidebar.expander("🧮 Umrechner"):
    wert = st.number_input("Wert", value=100.0)
    von = st.selectbox("Von", ["g", "kg", "ml", "L"])
    if von == "g": st.write(f"= {wert/1000} kg")
    elif von == "kg": st.write(f"= {wert*1000} g")
    elif von == "ml": st.write(f"= {wert/1000} L")
    elif von == "L": st.write(f"= {wert*1000} ml")

if st.sidebar.button("Logout"):
    st.session_state.haushalt = None; st.rerun()

# --- MODUL 1: VORRAT ---
if menu == "📦 Vorrat":
    st.header("📦 Dein Vorrat")
    sort_mode = st.radio("Sortierung:", ["Nach Haltbarkeit (MHD)", "Alphabetisch (A-Z)"], horizontal=True)
    if not mein_h["vorrat"]: st.info("Leer.")
    
    for ort in ORTE:
        items = [i for i in mein_h["vorrat"] if i.get('ort') == ort]
        if items:
            if "MHD" in sort_mode: items.sort(key=lambda x: x.get('mhd', '9999'))
            else: items.sort(key=lambda x: x.get('artikel', '').lower())

            with st.expander(f"📍 {ort} ({len(items)})", expanded=True):
                for item in items:
                    days = (datetime.strptime(item['mhd'], '%Y-%m-%d').date() - date.today()).days
                    color = "🔴" if days < 0 else "🟡" if days <= 5 else "🟢"
                    col1, col2, col3, col4 = st.columns([0.5, 4, 1, 1])
                    col1.write(color)
                    col2.write(f"**{item['artikel']}** ({item['menge']} {item['einheit']}) \n MHD: {item['mhd']} ({days} Tage)")
                    if col3.button("🍽️", key=f"eat_{item['artikel']}_{item['mhd']}"):
                        mein_h["vorrat"].remove(item); mein_h["stats"]["gegessen"] += 1; save(); st.rerun()
                    if col4.button("🗑️", key=f"trash_{item['artikel']}_{item['mhd']}"):
                        mein_h["vorrat"].remove(item); mein_h["stats"]["weg"] += 1; save(); st.rerun()

# --- MODUL 2: NEU HINZUFÜGEN ---
elif menu == "➕ Neu":
    st.header("➕ Artikel scannen/eingeben")
    with st.form("new_item"):
        name = st.text_input("Name")
        ort = st.selectbox("Ort", ORTE)
        col1, col2 = st.columns(2)
        menge = col1.number_input("Menge", 1.0)
        einheit = col2.selectbox("Einh.", ["Stück", "Pk.", "g", "kg", "ml", "L"])
        mhd = st.date_input("MHD", date.today())
        if st.form_submit_button("Speichern"):
            mein_h["vorrat"].append({"artikel": name, "menge": menge, "einheit": einheit, "ort": ort, "mhd": str(mhd)})
            save(); st.success("Gespeichert!")

# --- MODUL 3: REZEPTE (MIT TEXT) ---
elif menu == "📖 Rezepte":
    st.header("📖 Rezeptbuch")
    
    # Neues Rezept
    with st.expander("➕ Neues Rezept erstellen", expanded=False):
        rn = st.text_input("Gericht Name")
        
        # 1. Zutaten sammeln
        st.write("**Schritt 1: Zutaten**")
        if 'tmp_z' not in st.session_state: st.session_state.tmp_z = {}
        c1, c2, c3 = st.columns([2,1,1])
        zn = c1.text_input("Zutat")
        zm = c2.number_input("Menge", 0.1)
        if c3.button("Dazu"): st.session_state.tmp_z[zn] = zm; st.rerun()
        st.write(st.session_state.tmp_z)
        
        # 2. Anleitung schreiben
        st.write("**Schritt 2: Zubereitung**")
        anleitung_text = st.text_area("Wie kocht man das?", placeholder="Erst Wasser kochen, dann...")

        if st.button("Rezept komplett speichern"):
            if rn and st.session_state.tmp_z:
                mein_h["rezepte"][rn] = st.session_state.tmp_z
                mein_h["anleitungen"][rn] = anleitung_text # Speichere Text separat
                st.session_state.tmp_z = {}
                save(); st.rerun()
            else:
                st.error("Bitte Namen und Zutaten eingeben.")
            
    # Liste anzeigen
    for r in mein_h["rezepte"]:
        with st.expander(f"🍽️ {r}"):
            st.subheader("Zutaten:")
            st.write(mein_h["rezepte"][r])
            
            st.subheader("Zubereitung:")
            # Zeige Anleitung oder Standardtext
            st.info(mein_h["anleitungen"].get(r, "Keine Anleitung gespeichert."))
            
            if st.button("Löschen", key=r):
                del mein_h["rezepte"][r]
                if r in mein_h["anleitungen"]: del mein_h["anleitungen"][r]
                save(); st.rerun()

# --- MODUL 4: KOCHEN & REST-O-MAT ---
elif menu == "🍳 Kochen":
    st.header("🍳 Küche")
    tab1, tab2 = st.tabs(["📝 Rezept-Planer", "🔍 Rest-O-Mat (Suche)"])
    
    with tab1:
        bad = [i['artikel'] for i in mein_h["vorrat"] if (datetime.strptime(i['mhd'], '%Y-%m-%d').date() - date.today()).days <= 3]
        if bad: st.warning(f"⚠️ Schnell verbrauchen: {', '.join(bad)}")
        
        wahl = st.selectbox("Rezept wählen", ["-"] + list(mein_h["rezepte"].keys()))
        if wahl != "-":
            # Zeige Anleitung beim Kochen
            with st.expander("📜 Zubereitung anzeigen", expanded=True):
                st.write(mein_h["anleitungen"].get(wahl, "Keine Anleitung verfügbar."))
            
            st.write("---")
            req = mein_h["rezepte"][wahl]
            missing = []
            for z, m in req.items():
                found = sum([i['menge'] for i in mein_h["vorrat"] if z.lower() in i['artikel'].lower()])
                if found >= m: st.success(f"✅ {z}")
                else: 
                    st.error(f"❌ {z} (Fehlt: {m-found})")
                    missing.append(f"{z} ({m-found})")
            
            if not missing and st.button("Kochen & Abbuchen"):
                for z, m in req.items():
                    todo = m
                    for i in mein_h["vorrat"]:
                        if z.lower() in i['artikel'].lower():
                            take = min(i['menge'], todo)
                            i['menge'] -= take; todo -= take
                    mein_h["stats"]["gegessen"] += 1
                mein_h["vorrat"] = [i for i in mein_h["vorrat"] if i['menge'] > 0]
                save(); st.balloons(); st.rerun()
            elif missing and st.button("Fehlendes auf Einkaufsliste"):
                mein_h["einkauf"].extend(missing); save(); st.success("Auf Liste gesetzt!")

    with tab2:
        st.subheader("🔍 Suche")
        suche = st.text_input("Zutat eingeben (z.B. Eier)")
        if suche:
            hits = [r for r, zut in mein_h["rezepte"].items() if any(suche.lower() in z.lower() for z in zut)]
            if hits: st.success(f"Gefunden: {', '.join(hits)}")
            else: st.info("Nichts gefunden.")

# --- MODUL 5: EINKAUF ---
elif menu == "🛒 Einkauf":
    st.header("🛒 Einkaufsliste")
    new = st.text_input("Neues Item", key="shop_in")
    if st.button("Hinzufügen") and new: mein_h["einkauf"].append(new); save(); st.rerun()
    for item in mein_h["einkauf"]:
        c1, c2 = st.columns([4,1])
        c1.write(f"- {item}")
        if c2.button("✓", key=f"s_{item}"): mein_h["einkauf"].remove(item); save(); st.rerun()
    if mein_h["einkauf"]:
        pdf = erstelle_pdf(mein_h["einkauf"], "Einkaufsliste")
        st.download_button("📄 PDF", pdf, "liste.pdf")

# --- MODUL 6: STATISTIK ---
elif menu == "📊 Statistik":
    st.header("📊 Statistik")
    w = mein_h["stats"]["weg"]; g = mein_h["stats"]["gegessen"]; total = w + g
    c1, c2 = st.columns(2)
    c1.metric("Gerettet", g); c2.metric("Weggeworfen", w)
    if total > 0: st.progress(g / total)
