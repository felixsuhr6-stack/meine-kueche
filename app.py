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

# ADMIN ZUGANGSDATEN (Hier ändern!)
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

# --- FUNKTIONEN ---
def daten_laden():
    if os.path.exists(DATEI_NAME):
        with open(DATEI_NAME, "r", encoding="utf-8") as f:
            try: 
                data = json.load(f)
                # --- NOTFALL-REPARATUR FÜR ALTE STRUKTUREN ---
                if "haushalte" not in data and "globale_rezepte" not in data:
                    old_data = data.copy()
                    data = {"haushalte": old_data, "globale_rezepte": {}, "globale_anleitungen": {}}
                
                # Sicherstellen, dass alle Haupt-Keys da sind
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
st.set_page_config(page_title="Küchen-Chef Pro", layout="wide", page_icon="🍎")

def apply_dark_mode():
    st.markdown("""<style>.stApp { background-color: #1E1E1E; color: white; } div[data-testid="stSidebar"] { background-color: #262730; } .stTextInput>div>div>input, .stTextArea>div>div>textarea { color: black; }</style>""", unsafe_allow_html=True)

if 'haushalt' not in st.session_state: st.session_state.haushalt = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

alle_daten = daten_laden()

def save_all():
    daten_speichern(alle_daten)

# --- LOGIN SCREEN ---
if st.session_state.haushalt is None and not st.session_state.is_admin:
    st.header("🔐 Login")
    
    # 1. ADMIN LOGIN CHECK
    with st.expander("🛠️ Entwickler-Login"):
        a_user = st.text_input("Admin Name")
        a_pass = st.text_input("Admin Passwort", type="password")
        if st.button("Als Entwickler starten"):
            if a_user == ADMIN_USER and a_pass == ADMIN_PASS:
                st.session_state.is_admin = True
                st.session_state.haushalt = "ADMIN"
                st.rerun()
            else:
                st.error("Zugriff verweigert!")

    # 2. NORMALER LOGIN
    st.subheader("Haushalt Login")
    with st.form("login_form"):
        h_name = st.text_input("Haushalts-Name").strip()
        h_pass = st.text_input("Passwort", type="password")
        c1, c2 = st.columns(2)
        
        if c1.form_submit_button("Anmelden"):
            if h_name in alle_daten["haushalte"]:
                if alle_daten["haushalte"][h_name]['passwort'] == hash_passwort(h_pass):
                    st.session_state.haushalt = h_name
                    st.rerun()
                else: st.error("Passwort falsch!")
            else: st.error("Haushalt nicht gefunden!")
                
        if c2.form_submit_button("Registrieren"):
            if h_name and h_pass and h_name not in alle_daten["haushalte"] and h_name != ADMIN_USER:
                alle_daten["haushalte"][h_name] = {
                    "passwort": hash_passwort(h_pass), "vorrat": [], 
                    "wochenplan": {t: "-" for t in TAGE}, "einkauf": [], 
                    "stats": {"weg": 0, "gegessen": 0}, "verlinkt": []
                }
                save_all(); st.success("Erstellt! Bitte einloggen.")
            else: st.warning("Name ungültig oder vergeben.")
    st.stop()

# --- SIDEBAR SETUP ---
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
    st.title("🛠️ Entwickler-Konsole")
    st.warning("⚠️ Du hast volle Schreibrechte auf alle Datenbanken!")
    
    admin_menu = st.sidebar.radio("Admin Menü", ["👥 User-Verwaltung", "💾 Datenbank Raw", "📖 Rezepte bearbeiten"])
    
    if admin_menu == "👥 User-Verwaltung":
        st.subheader("Alle Haushalte verwalten")
        users = list(alle_daten["haushalte"].keys())
        
        if not users: st.info("Keine User vorhanden.")
        
        for user in users:
            with st.expander(f"👤 {user} bearbeiten"):
                u_data = alle_daten["haushalte"][user]
                
                # Info
                st.write(f"Vorrat-Items: {len(u_data.get('vorrat', []))}")
                st.write(f"Einkaufsliste: {len(u_data.get('einkauf', []))}")
                
                # Passwort Reset
                new_pw = st.text_input(f"Neues Passwort für {user}", key=f"pw_{user}")
                if st.button(f"Passwort ändern für {user}", key=f"btn_pw_{user}"):
                    if new_pw:
                        alle_daten["haushalte"][user]["passwort"] = hash_passwort(new_pw)
                        save_all(); st.success(f"Passwort für {user} geändert!")
                
                # Vorrat einsehen
                if st.checkbox(f"Vorrat von {user} anzeigen", key=f"view_{user}"):
                    st.json(u_data.get("vorrat", []))

                # Löschen
                st.write("---")
                if st.button(f"❌ ACCOUNT {user} LÖSCHEN", key=f"del_{user}"):
                    del alle_daten["haushalte"][user]
                    save_all(); st.rerun()

    elif admin_menu == "💾 Datenbank Raw":
        st.subheader("JSON Rohdaten")
        st.write("Hier siehst du die komplette Speicher-Struktur:")
        st.json(alle_daten)

    elif admin_menu == "📖 Rezepte bearbeiten":
        st.subheader("Globale Rezepte verwalten")
        for r in list(alle_daten["globale_rezepte"].keys()):
            c1, c2 = st.columns([4,1])
            c1.write(f"**{r}**")
            if c2.button("Löschen", key=f"admin_del_r_{r}"):
                del alle_daten["globale_rezepte"][r]
                if r in alle_daten["globale_anleitungen"]: del alle_daten["globale_anleitungen"][r]
                save_all(); st.rerun()

# ==========================================
#         NORMALER USER BEREICH
# ==========================================
else:
    # Daten laden für normalen User
    mein_h = alle_daten["haushalte"][h_name]
    
    # Sicherstellen, dass Felder existieren (Reparatur zur Laufzeit)
    if "verlinkt" not in mein_h: mein_h["verlinkt"] = []
    if "stats" not in mein_h: mein_h["stats"] = {"weg": 0, "gegessen": 0}
    if "wochenplan" not in mein_h: mein_h["wochenplan"] = {t: "-" for t in TAGE}
    if "einkauf" not in mein_h: mein_h["einkauf"] = []
    if "vorrat" not in mein_h: mein_h["vorrat"] = []

    menu = st.sidebar.radio("Menü", ["📅 Wochenplan", "📦 Vorrat", "➕ Neu", "📖 Gemeinschafts-Rezepte", "🍳 Kochen", "🛒 Einkauf", "📊 Statistik & Connect"])

    # Umrechner in Sidebar
    with st.sidebar.expander("🧮 Umrechner"):
        wert = st.number_input("Wert", value=100.0)
        von = st.selectbox("Von", ["g", "kg", "ml", "L"])
        if von == "g": st.write(f"= {wert/1000} kg")
        elif von == "kg": st.write(f"= {wert*1000} g")
        elif von == "ml": st.write(f"= {wert/1000} L")
        elif von == "L": st.write(f"= {wert*1000} ml")

    # --- MODUL: WOCHENPLAN ---
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
                if st.form_submit_button("Plan speichern"): save_all(); st.success("Gespeichert!")
        with c2:
            st.write("---")
            if st.button("🛒 Zutaten auf Einkaufsliste"):
                count = 0
                for t, g in mein_h["wochenplan"].items():
                    if g != "-":
                        for z, m in alle_daten["globale_rezepte"][g].items():
                            mein_h["einkauf"].append(f"{z} ({m})"); count+=1
                save_all(); st.success(f"{count} Zutaten hinzugefügt!")
            
            pdf_text = [f"{t}: {mein_h['wochenplan'][t]}" for t in TAGE]
            st.download_button("📄 PDF Download", erstelle_pdf(pdf_text, "Wochenplan"), "plan.pdf")

    # --- MODUL: VORRAT ---
    elif menu == "📦 Vorrat":
        st.header("📦 Vorräte")
        t1, t2 = st.tabs(["🏠 Mein Vorrat", "🔗 Freunde"])
        with t1:
            sort_mode = st.radio("Sortierung", ["MHD", "A-Z"], horizontal=True)
            for ort in ORTE:
                items = [i for i in mein_h["vorrat"] if i.get('ort') == ort]
                if items:
                    items.sort(key=lambda x: x.get('mhd', '9999') if "MHD" in sort_mode else x.get('artikel', '').lower())
                    with st.expander(f"📍 {ort} ({len(items)})", expanded=True):
                        for item in items:
                            c1, c2, c3, c4 = st.columns([0.5, 4, 1, 1])
                            c2.write(f"**{item['artikel']}** ({item['menge']} {item['einheit']}) - MHD: {item['mhd']}")
                            if c3.button("🍽️", key=f"e_{item['artikel']}_{item['mhd']}"):
                                mein_h["vorrat"].remove(item); mein_h["stats"]["gegessen"] += 1; save_all(); st.rerun()
                            if c4.button("🗑️", key=f"t_{item['artikel']}_{item['mhd']}"):
                                mein_h["vorrat"].remove(item); mein_h["stats"]["weg"] += 1; save_all(); st.rerun()
        with t2:
            if not mein_h["verlinkt"]: st.info("Keine Freunde verknüpft.")
            for f_name in mein_h["verlinkt"]:
                if f_name in alle_daten["haushalte"]:
                    f_h = alle_daten["haushalte"][f_name]
                    with st.expander(f"👤 {f_name}"):
                        for i in f_h["vorrat"]:
                            c1, c2 = st.columns([4,1])
                            c1.write(f"{i['artikel']} ({i['menge']} {i['einheit']})")
                            if c2.button("Ausleihen", key=f"lend_{f_name}_{i['artikel']}"):
                                alle_daten["haushalte"][f_name]["vorrat"].remove(i)
                                mein_h["vorrat"].append(i); save_all(); st.rerun()

    # --- MODUL: NEU ---
    elif menu == "➕ Neu":
        st.header("➕ Artikel hinzufügen")
        with st.form("add_form"):
            n = st.text_input("Name"); o = st.selectbox("Ort", ORTE)
            c1, c2 = st.columns(2)
            m = c1.number_input("Menge", 1.0); e = c2.selectbox("Einh.", ["Stück", "g", "kg", "ml", "L", "Pk."])
            d = st.date_input("MHD")
            if st.form_submit_button("Speichern"):
                mein_h["vorrat"].append({"artikel": n, "menge": m, "einheit": e, "ort": o, "mhd": str(d)})
                save_all(); st.success("Gespeichert!")

    # --- MODUL: REZEPTE (WIEDER MIT DETAILS!) ---
    elif menu == "📖 Gemeinschafts-Rezepte":
        st.header("📖 Alle Rezepte")
        with st.expander("➕ Neues Rezept erstellen"):
            rn = st.text_input("Rezept Name")
            
            # Zutateneingabe
            st.write("**Zutaten:**")
            if 'tmp_z' not in st.session_state: st.session_state.tmp_z = {}
            c1, c2, c3 = st.columns([2,1,1])
            zn = c1.text_input("Zutat Name"); zm = c2.number_input("Menge", 0.0)
            if c3.button("Zutat dazu"): 
                if zn: st.session_state.tmp_z[zn] = zm; st.rerun()
            
            # Anzeige der aktuellen Zutatenliste
            if st.session_state.tmp_z:
                st.write(st.session_state.tmp_z)
                if st.button("Zutatenliste leeren"): st.session_state.tmp_z = {}; st.rerun()

            anl = st.text_area("Zubereitungsschritte")
            
            if st.button("Rezept speichern"):
                if rn and st.session_state.tmp_z:
                    alle_daten["globale_rezepte"][rn] = st.session_state.tmp_z
                    alle_daten["globale_anleitungen"][rn] = anl
                    st.session_state.tmp_z = {}; save_all(); st.success("Rezept für alle veröffentlicht!"); st.rerun()
                else: st.error("Name oder Zutaten fehlen.")

        # Liste anzeigen
        for r in list(alle_daten["globale_rezepte"].keys()):
            with st.expander(f"🍽️ {r}"):
                st.write("**Zutaten:**", alle_daten["globale_rezepte"][r])
                st.write("**Anleitung:**", alle_daten["globale_anleitungen"].get(r, "-"))

    # --- MODUL: KOCHEN ---
    elif menu == "🍳 Kochen":
        st.header("🍳 Kochen")
        tab_k, tab_r = st.tabs(["Nach Rezept", "Rest-O-Mat"])
        with tab_k:
            wahl = st.selectbox("Rezept", ["-"] + list(alle_daten["globale_rezepte"].keys()))
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
                                take = min(i['menge'], todo); i['menge'] -= take; todo -= take
                    mein_h["vorrat"] = [x for x in mein_h["vorrat"] if x['menge'] > 0]
                    mein_h["stats"]["gegessen"] += 1; save_all(); st.balloons(); st.rerun()
        with tab_r:
            s = st.text_input("Zutat suchen")
            if s:
                hits = [r for r, z in alle_daten["globale_rezepte"].items() if any(s.lower() in k.lower() for k in z)]
                st.write("Rezepte:", hits)

    # --- MODUL: EINKAUF ---
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

    # --- MODUL: CONNECT ---
    elif menu == "📊 Statistik & Connect":
        st.header("📊 Einstellungen")
        st.write(f"Dein Code: **{h_name}**")
        f = st.text_input("Freund verbinden (Name)")
        if st.button("Verbinden") and f in alle_daten["haushalte"]:
            mein_h["verlinkt"].append(f); save_all(); st.success("Verbunden!")
        st.write("Freunde:", mein_h["verlinkt"])
        c1, c2 = st.columns(2)
        c1.metric("Gegessen", mein_h["stats"]["gegessen"]); c2.metric("Weg", mein_h["stats"]["weg"])
