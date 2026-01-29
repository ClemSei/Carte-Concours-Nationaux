import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.distance import distance as geopy_dist
import re

# --- CONFIGURATION GÉNÉRALE ---
st.set_page_config(layout="wide", page_title="Concours Nationaux Colombophiles")

# --- DONNÉES CONCOURS NATIONAUX ---
all_points = [
    {"nom": "Saverdun", "lat": 43.2427778, "lon": 1.57250, "rayon": 490000, "coul": "green"},
    {"nom": "Mondavezan", "lat": 43.24033, "lon": 1.07522, "rayon": 490000, "coul": "blue"},
]

# Couleurs pour le score d'éligibilité
couleurs_zones = {
    0: "#000000", 1: "#808080", 2: "#d62728", 3: "#ff7f0e",
    4: "#bcbd22", 5: "#17becf", 6: "#1f77b4", 7: "#2ca02c"
}

# --- MENU DE NAVIGATION ---
st.sidebar.title("🕊️ Portail National")
page = st.sidebar.radio("Navigation", ["Analyse des Concours", "Informations"])

# ---------------------------------------------------------
# PAGE 1 : ANALYSE DES CONCOURS
# ---------------------------------------------------------
if page == "Analyse des Concours":
    st.title("🗺️ Analyse d'Éligibilité - Concours Nationaux")

    # --- BARRE LATÉRALE ---
    st.sidebar.header("1. Recherche Pigeonnier")
    mode_saisie = st.sidebar.radio("Mode de saisie :", ["Adresse postale", "Coordonnées GPS"])
    
    point_recherche = None
    label_position = ""

    if mode_saisie == "Adresse postale":
        adresse = st.sidebar.text_input("📍 Entrez une adresse :", placeholder="ex: Lille, France")
        if adresse:
            geolocator = Nominatim(user_agent="colombo_app_v3")
            try:
                loc = geolocator.geocode(adresse)
                if loc:
                    point_recherche = (loc.latitude, loc.longitude)
                    label_position = loc.address
                else:
                    st.sidebar.error("Adresse introuvable.")
            except:
                st.sidebar.error("Erreur service localisation.")
    
    else:
        st.sidebar.write("🌐 Saisissez les coordonnées :")
        col_lat, col_lon = st.sidebar.columns(2)
        lat_input = col_lat.text_input("Latitude", placeholder="ex: 423618.2")
        lon_input = col_lon.text_input("Longitude", placeholder="ex: 30121.7")

        if lat_input and lon_input:
            try:
                def convertir_valeur(val_str):
                    val = float(val_str.replace(',', '.').strip())
                    if abs(val) > 1000:
                        deg = int(val / 10000)
                        reste = val - (deg * 10000)
                        minutes = int(reste / 100)
                        secondes = reste - (minutes * 100)
                        return deg + (minutes / 60) + (secondes / 3600)
                    return val

                lat_dec = convertir_valeur(lat_input)
                lon_dec = convertir_valeur(lon_input)
                point_recherche = (lat_dec, lon_dec)
                label_position = f"GPS : {lat_dec:.5f}, {lon_dec:.5f}"
                st.sidebar.success(f"Converti : {lat_dec:.4f} / {lon_dec:.4f}")
            except:
                st.sidebar.error("Format invalide")

    st.sidebar.markdown("---")
    st.sidebar.header("2. Sélection des Concours")
    active_points = []
    cols_check = st.sidebar.columns(2)
    for i, p in enumerate(all_points):
        col = cols_check[i % 2]
        if col.checkbox(f"{p['nom']}", value=True, key=f"city_{p['nom']}"):
            active_points.append(p)

    # --- CALCULS ---
    resultats_adresse = {"ok": [], "ko": []}
    score_adresse = 0

    if point_recherche:
        for p in active_points:
            dist = geodesic(point_recherche, (p['lat'], p['lon'])).meters
            info = {"nom": p['nom'], "dist": round(dist/1000, 1), "min": round(p['rayon']/1000, 1)}
            if dist > p['rayon']:
                resultats_adresse["ok"].append(info)
                score_adresse += 1
            else:
                resultats_adresse["ko"].append(info)

    # --- MISE EN PAGE ---
    col_map, col_details = st.columns([3, 1])

    with col_map:
        start_loc = point_recherche if point_recherche else [48.0, 2.0]
        start_zoom = 7 if point_recherche else 5
        m = folium.Map(location=start_loc, zoom_start=start_zoom)

        def generer_arc_nord(centre_lat, centre_lon, rayon_metres):
            coords = []
            for azimut in range(270, 451, 3):
                dest = geopy_dist(meters=rayon_metres).destination((centre_lat, centre_lon), azimut)
                coords.append([dest.latitude, dest.longitude])
            return coords

        for p in active_points:
            points_arc = generer_arc_nord(p['lat'], p['lon'], p['rayon'])
            folium.PolyLine(
                locations=points_arc, color=p['coul'], weight=4, opacity=0.9,
                tooltip=f"Ligne {p['nom']} ({p['rayon']/1000} km)"
            ).add_to(m)

        if point_recherche:
            folium.Marker(
                point_recherche, popup=label_position,
                icon=folium.Icon(color="black", icon="home")
            ).add_to(m)

        st_folium(m, width="100%", height=750)

    with col_details:
        st.subheader("📋 Analyse Détaillée")
        if point_recherche:
            st.info(f"Position : {label_position}")
            st.markdown(f"### Score : {score_adresse} / {len(active_points)}")
            c_score = couleurs_zones.get(score_adresse, "#000")
            st.markdown(f'<div style="background-color:{c_score};height:15px;width:100%;border-radius:5px;"></div><br>', unsafe_allow_html=True)
            
            with st.expander("✅ JOUABLES", expanded=True):
                if resultats_adresse["ok"]:
                    for c in resultats_adresse["ok"]:
                        st.success(f"**{c['nom']}**\n\n+ {c['dist']} km (Min {c['min']})")
                else: st.write("Aucun.")

            with st.expander("❌ INTERDITS", expanded=True):
                if resultats_adresse["ko"]:
                    for c in resultats_adresse["ko"]:
                        st.error(f"**{c['nom']}**\n\n{c['dist']} km (Min {c['min']})")
                else: st.write("Aucun.")
        else:
            st.warning("👈 Recherchez une position à gauche.")

# ---------------------------------------------------------
# PAGE 2 : INFORMATIONS
# ---------------------------------------------------------
elif page == "Informations":
    st.title("ℹ️ À propos")
    st.write("Ce portail national permet aux amateurs de visualiser les zones d'éligibilité pour les grands concours de fond.")
    st.markdown("""
    ### Utilisation
    1. Sélectionnez votre mode de recherche (Adresse ou GPS).
    2. Visualisez sur la carte les arcs de cercles représentant les distances minimales.
    3. Vérifiez dans le panneau latéral droit quels concours vous sont accessibles.
    """)