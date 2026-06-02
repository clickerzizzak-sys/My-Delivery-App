import streamlit as st
import folium
from streamlit_folium import st_folium
import itertools
from geopy.distance import geodesic
import urllib.parse

st.set_page_config(page_title="Delivery Pro", layout="wide")

st.title("🚚 Delivery Router Pro")
st.write("Select your outlets below to generate the absolute best driving route.")

# --- THE GPS STORAGE BANK ---
OUTLET_BANK = {
    "Depot / Starting Point": (16.8409, 96.1735), 
    "Store Outlet 1 - Downtown": (16.7762, 96.1548),
    "Store Outlet 2 - North Junction": (16.8660, 96.1450),
    "Store Outlet 3 - East Market": (16.8050, 96.2100),
    "Store Outlet 4 - Hlaing Township": (16.8480, 96.1240),
    "Store Outlet 5 - Tamwe Plaza": (16.8120, 96.1680),
}

if 'route_calculated' not in st.session_state:
    st.session_state.route_calculated = False
if 'best_path' not in st.session_state:
    st.session_state.best_path = []
if 'route_stops' not in st.session_state:
    st.session_state.route_stops = []
if 'total_distance' not in st.session_state:
    st.session_state.total_distance = 0.0

st.subheader("📋 Select Today's Outlets")
start_node = "Depot / Starting Point"

selected_outlets = []
for outlet_name in OUTLET_BANK.keys():
    if outlet_name != start_node:
        if st.checkbox(f"📍 {outlet_name}", value=False, key=f"check_{outlet_name}"):
            selected_outlets.append(outlet_name)

if st.button("🚀 OPTIMIZE MY ROUTE", type="primary"):
    if not selected_outlets:
        st.error("Please select at least one outlet!")
        st.session_state.route_calculated = False
    else:
        route_stops = [start_node] + selected_outlets
        coordinates = [OUTLET_BANK[name] for name in route_stops]
        
        start_coord = coordinates[0]
        dest_coords = coordinates[1:]
        dest_indices = list(range(len(dest_coords)))
        best_distance = float('inf')
        best_path = []
        
        for perm in itertools.permutations(dest_indices):
            current_distance = 0
            current_path = [0]
            current_distance += geodesic(start_coord, dest_coords[perm[0]]).kilometers
            current_path.append(perm[0] + 1)
            for i in range(len(perm) - 1):
                current_distance += geodesic(dest_coords[perm[i]], dest_coords[perm[i+1]]).kilometers
                current_path.append(perm[i+1] + 1)
            current_distance += geodesic(dest_coords[perm[-1]], start_coord).kilometers
            current_path.append(0)
            
            if current_distance < best_distance:
                best_distance = current_distance
                best_path = current_path

        st.session_state.best_path = best_path
        st.session_state.route_stops = route_stops
        st.session_state.total_distance = best_distance
        st.session_state.route_calculated = True

if st.session_state.route_calculated:
    saved_stops = st.session_state.route_stops
    saved_path = st.session_state.best_path
    coords_list = [OUTLET_BANK[name] for name in saved_stops]
    
    st.success(f"✅ Route Optimized: {st.session_state.total_distance:.1f} km")
    
    # --- FIXED OFFICIAL GOOGLE MAPS MULTI-STOP LINK ---
    gmaps_base = "https://www.google.com/maps/dir/?api=1"
    origin = f"&origin={coords_list[0][0]},{coords_list[0][1]}"
    ordered_coords = [coords_list[idx] for idx in saved_path[1:-1]]
    
    if ordered_coords:
        # Keep inside Google Maps' max 9-waypoint mobile ceiling
        gmaps_batch = ordered_coords[:9]
        destination = f"&destination={gmaps_batch[-1][0]},{gmaps_batch[-1][1]}"
        waypoints = "|".join([f"{c[0]},{c[1]}" for c in gmaps_batch[:-1]])
        waypoint_str = f"&waypoints={urllib.parse.quote(waypoints)}" if waypoints else ""
        full_gmaps_url = f"{gmaps_base}{origin}{destination}{waypoint_str}&travelmode=driving"
        
        st.link_button("🗺️ OPEN BATCH IN GOOGLE MAPS", full_gmaps_url, use_container_width=True)

    # Preview Map Frame
    m = folium.Map(location=coords_list[0], zoom_start=12)
    path_coords = [coords_list[idx] for idx in saved_path]
    folium.PolyLine(path_coords, color="blue", weight=5).add_to(m)
    
    for idx, name in enumerate(saved_stops):
        coord = OUTLET_BANK[name]
        if name == start_node:
            folium.Marker(coord, popup=name, icon=folium.Icon(color='red', icon='home')).add_to(m)
        else:
            folium.Marker(coord, popup=name, icon=folium.Icon(color='green')).add_to(m)
            
    st_folium(m, width=700, height=350, key="fixed_pro_map")
    
    st.subheader("🏁 Stop-by-Stop Order")
    for step, idx in enumerate(saved_path[:-1]):
        stop_name = saved_stops[idx]
        lat, lon = OUTLET_BANK[stop_name]
        
        # Fixed single location launch URL
        single_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
        
        label = f"START: {stop_name}" if step == 0 else f"STOP {step}: {stop_name}"
        st.link_button(f"🧭 {label}", single_url, use_container_width=True)
