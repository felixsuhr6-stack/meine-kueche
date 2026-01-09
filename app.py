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
                if "einkauf" not in data: data["einkauf"] = []
                return data
            except:
                return {"vorrat": [], "rezepte": {}, "einkauf": []}
    return {"vorrat": [], "rezepte": {}, "einkauf": []}

def daten_speichern():
    daten = {
        "vorrat": st.session_state.vorrat, 
        "rezepte": st.session_state.rezepte,
        "einkauf": st.session_state.einkauf
    }
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
    st.session_state.einkauf = daten.get("einkauf", [])
    st.session_state.daten_geladen = True

# --- NAVIGATION ---
st.sidebar.title("🍎 Küchen-Manager")
menu = st.sidebar.radio("Navigation", ["📦 Vorrat", "➕ Neu hinzufügen", "📖 Rezepte", "🍳 Kochen", "🛒 Einkaufsliste"])

# --- 1. VORRAT (MIT TAGE-ANZEIGE) ---
if menu == "📦 Vorrat":
    st.header("🏠 Dein Bestand")
    if not st.session_state.vorrat:
        st.info("Deine Vorratskammer ist leer.")
    else:
        for ort in ORTE:
            artikel_am_ort = [i for i in st.session_state.vorrat if i.get('ort') == ort]
            if artikel_am_ort:
                with st.expander(f"📍 {ort} ({len(artikel_am_ort)} Artikel)", expanded=True):
                    # Sortieren nach Datum
                    artikel_am_ort.sort(key=lambda x: x.get('mhd', '9999-12-31'))
                    
                    for item in artikel_am_ort:
                        heute = date.today()
                        try:
                            mhd_dt = datetime.strptime(item['mhd'], '%Y-%m-%d').date()
                            tage = (mhd_dt - heute).days
                        except:
                            tage = 0
                        
                        # Ampel & Text-Logik
                        if tage < 0:
                            color = "🔴"
                            zeit_text = f"Seit {abs(tage)} Tagen abgelaufen!"
                        elif tage == 0:
                            color = "🔴"
                            zeit_text = "Heute fällig!"
                        elif tage <= 3:
                            color = "🔴"
                            zeit_text = f"Nur noch {tage} Tage"
                        elif tage <= 7:
                            color = "🟡"
                            zeit_text = f"Noch {tage} Tage"
                        else:
                            color = "🟢"
                            zeit_text = f"Noch {tage} Tage"

                        c1, c2, c3 = st.columns([0.1, 0.7, 0.2])
                        c1.write(color)
                        c2.write(f"**{item['artikel']}** ({item['menge']} {item['einheit']}) — {zeit_text} ({item['mhd']})")
                        if c3.button("Löschen", key=f"del_v_{item['artikel']}_{item['mhd']}"):
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
                st.session_state.vorrat.append({"artikel": name, "menge": menge, "einheit": einheit, "ort": ort, "mhd": str(mhd)})
                daten_speichern()
                st.success(f"✅ {name} gespeichert!")

# --- 3. REZEPTE ---
elif menu == "📖 Rezepte":
    st.header("📖 Rezeptbuch")
    with st.expander("➕ Neues Rezept erstellen"):
        r_name = st.text_input("Name des Gerichts")
        if 'temp_z' not in st.session_state: st.session_state.temp_z = {}
        c1, c2, c3 = st.columns([3, 2, 1])
        z_n = c1.text_input("Zutat")
        z_m = c2.number_input("Menge nötig", min_value=0.1)
        if c3.button("Hinzufügen"):
            if z_n: st.session_state.temp_z[z_n] = z_m
            st.rerun()
        if st.session_state.temp_z:
            for z, m in st.session_state.temp_z.items(): st.write(f"- {z}: {m}")
            if st.button("Rezept speichern"):
                if r_name:
                    st.session_state.rezepte[r_name] = st.session_state.temp_z
                    st.session_state.temp_z = {}
                    daten_speichern(); st.rerun()

    for r, zutaten in st.session_state.rezepte.items():
        with st.expander(f"🍽️ {r}"):
            for z, m in zutaten.items(): st.write(f"- {z}: {m}")
            if st.button("Rezept löschen", key=f"rdel_{r}"):
                del st.session_state.rezepte[r]; daten_speichern(); st.rerun()

# --- 4. KOCHEN (MIT SMARTEN VORSCHLÄGEN) ---
elif menu == "🍳 Kochen":
    st.header("🍳 Was kochen wir?")
    
    # --- SMART VORSCHLAG LOGIK ---
    heute = date.today()
    kritische_zutaten = []
    
    # 1. Finde Zutaten, die in <= 7 Tagen ablaufen
    for item in st.session_state.vorrat:
        try:
            mhd_dt = datetime.strptime(item['mhd'], '%Y-%m-%d').date()
            if (mhd_dt - heute).days <= 7:
                kritische_zutaten.append(item['artikel'].lower())
        except: pass
    
    # 2. Finde Rezepte, die diese Zutaten nutzen
    vorschlaege = []
    if kritische_zutaten:
        for r_name, zutaten_dict in st.session_state.rezepte.items():
            # Prüfe ob irgendeine Zutat des Rezepts in der kritischen Liste ist
            for z_rezept in zutaten_dict.keys():
                if any(k in z_rezept.lower() for k in kritische_zutaten):
                    if r_name not in vorschlaege:
                        vorschlaege.append(r_name)
    
    if vorschlaege:
        st.info(f"💡 **Tipp gegen Verschwendung:** Deine Zutaten laufen bald ab! Koche am besten: **{', '.join(vorschlaege)}**")
    else:
        if kritische_zutaten:
            st.warning("⚠️ Du hast ablaufende Zutaten, aber kein passendes Rezept dafür gespeichert.")
    
    st.write("---")

    # --- NORMALE KOCHEN LOGIK ---
    wahl = st.selectbox("Rezept wählen", ["-"] + list(st.session_state.rezepte.keys()))
    if wahl != "-":
        zutaten_req = st.session_state.rezepte[wahl]
        vorrat_summe = {i['artikel'].lower(): 0 for i in st.session_state.vorrat}
        for i in st.session_state.vorrat: vorrat_summe[i['artikel'].lower()] += i['menge']
        
        alles_da = True
        for z, m_soll in zutaten_req.items():
            m_ist = vorrat_summe.get(z.lower(), 0)
            if m_ist >= m_soll: st.success(f"✅ {z}")
            else:
                st.error(f"❌ {z} (Fehlt: {m_soll - m_ist})")
                alles_da = False
                if st.button(f"'{z}' auf Einkaufsliste setzen"):
                    item_str = f"{z} ({m_soll - m_ist})"
                    if item_str not in st.session_state.einkauf:
                        st.session_state.einkauf.append(item_str)
                        daten_speichern(); st.success("Hinzugefügt!")

        if alles_da and st.button("Jetzt Kochen"):
            for z, m_soll in zutaten_req.items():
                m_abz = m_soll
                for item in st.session_state.vorrat:
                    if item['artikel'].lower() == z.lower():
                        if item['menge'] >= m_abz: item['menge'] -= m_abz; m_abz = 0
                        else: m_abz -= item['menge']; item['menge'] = 0
                if m_abz <= 0: break
            st.session_state.vorrat = [i for i in st.session_state.vorrat if i['menge'] > 0]
            daten_speichern(); st.balloons(); st.rerun()

# --- 5. EINKAUFSLISTE ---
elif menu == "🛒 Einkaufsliste":
    st.header("🛒 Deine Einkaufsliste")
    with st.form("manual_shop"):
        new_item = st.text_input("Was fehlt noch?")
        if st.form_submit_button("Hinzufügen"):
            if new_item:
                st.session_state.einkauf.append(new_item)
                daten_speichern(); st.rerun()

    if not st.session_state.einkauf:
        st.info("Deine Liste ist leer.")
    else:
        for item in st.session_state.einkauf:
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"- {item}")
            if c2.button("Gekauft", key=f"shop_{item}"):
                st.session_state.einkauf.remove(item)
                daten_speichern(); st.rerun()
        
        if st.button("Liste leeren"):
            st.session_state.einkauf = []
            daten_speichern(); st.rerun()
            
        pdf_data = erstelle_pdf(st.session_state.einkauf, "Einkaufsliste")
        st.download_button("📄 Liste als PDF", data=pdf_data, file_name="einkauf.pdf")
