import streamlit as st
import folium
from streamlit_folium import st_folium
import itertools
from geopy.distance import geodesic
import urllib.parse

st.set_page_config(page_title="Delivery Pro", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS to make it look like a high-end dark-mode mobile app
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    h1 { color: #FF4B4B; font-size: 24px !important; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3rem; font-size: 16px; font-weight: bold; }
    .nav-box {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border-left: 5px solid #FF4B4B;
    }
    </style>
""", unsafe_allowed_html=True)

st.title("🚚 Delivery Router Pro")

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
        
        # TSP Solver Engine
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
    
    st.success(f"Route Optimized: {st.session_state.total_distance:.1f} km")
    
    # --- GOOGLE MAPS MULTI-STOP HACK ---
    # This builds a single link containing the first 9 stops in order
    gmaps_base = "https://www.google.com/maps/dir/?api=1"
    origin = f"&origin={coords_list[0][0]},{coords_list[0][1]}"
    
    # Get ordered coordinates for stops (excluding start and final return)
    ordered_coords = [coords_list[idx] for idx in saved_path[1:-1]]
    
    if ordered_coords:
        destination = f"&destination={ordered_coords[-1][0]},{ordered_coords[-1][1]}"
        waypoints = "|".join([f"{c[0]},{c[1]}" for c in ordered_coords[:-1]])
        waypoint_str = f"&waypoints={urllib.parse.quote(waypoints)}" if waypoints else ""
        full_gmaps_url = f"{gmaps_base}{origin}{destination}{waypoint_str}&travelmode=driving"
        
        st.markdown(f'<a href="{full_gmaps_url}" target="_blank"><button style="width:100%; background-color:#4CAF50; color:white; border:none; border-radius:10px; height:3.5rem; font-weight:bold; font-size:16px; margin-bottom:20px; cursor:pointer;">🗺️ OPEN ENTIRE ROUTE IN GOOGLE MAPS</button></a>', unsafe_allowed_html=True)

    # Clean App Interface Layout
    m = folium.Map(location=coords_list[0], zoom_start=12, zoom_control=False)
    path_coords = [coords_list[idx] for idx in saved_path]
    folium.PolyLine(path_coords, color="#FF4B4B", weight=5).add_to(m)
    st_folium(m, width=700, height=300, key="pro_map")
    
    st.subheader("🏁 Stop-by-Stop Order")
    for step, idx in enumerate(saved_path[:-1]):
        stop_name = saved_stops[idx]
        lat, lon = OUTLET_BANK[stop_name]
        single_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
        
        st.markdown(f"""
            <div class="nav-box">
                <small style="color:#aaa;">STOP {step if step > 0 else 'START'}</small>
                <div style="font-size:18px; font-weight:bold; margin-bottom:10px;">{stop_name}</div>
                <a href="{single_url}" target="_blank" style="text-decoration:none;">
                    <button style="background-color:#008CBA; color:white; border:none; padding:5px 15px; border-radius:5px; font-weight:bold; width:auto; height:auto; cursor:pointer;">🧭 Open Map</button>
                </a>
            </div>
        """, unsafe_allowed_html=True)
