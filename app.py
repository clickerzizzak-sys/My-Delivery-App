import streamlit as st
import folium
from streamlit_folium import st_folium
import itertools
from geopy.distance import geodesic
import urllib.parse
import pandas as pd

st.set_page_config(page_title="Delivery Pro", layout="wide")

st.title("🚚 Manual Control Delivery Router")
st.write("Search, filter, and choose your outlets manually.")

# --- CONNECT TO YOUR GOOGLE SHEET ---
# I have embedded your exact link here and added a cleaner function below to fix it!
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1koRRrPEzAIOlt1LW8sFW6WdY2aoR5l-qogaua3DH6zg/edit?usp=drivesdk"

@st.cache_data(ttl=2)
def load_sheet_data(url):
    try:
        # This cleaning step safely strips out 'edit?usp=drivesdk' or any other suffix automatically
        base_url = url.split('/edit')[0]
        csv_url = f"{base_url}/gviz/tq?tqx=out:csv"
        
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error("Connection Error. Please double-check that 'Anyone with the link' is set to Viewer inside Google Sheets Share settings.")
        return None

df_raw = load_sheet_data(GSHEET_URL)

if df_raw is None:
    st.info("Waiting for valid Google Sheet data connection...")
    st.stop()

# --- MANUAL SEARCH FILTER BAR ---
st.subheader("🔍 Filter Outlets")
search_query = st.text_input("Type a day (e.g., Wed, Mon) or name to filter your list:", "").strip()

if search_query:
    df_filtered = df_raw[
        df_raw['Cus;Name'].astype(str).str.contains(search_query, case=False, na=False) |
        df_raw['Service Day'].astype(str).str.contains(search_query, case=False, na=False)
    ]
else:
    df_filtered = df_raw.copy()

# Convert to coordinate dictionary
OUTLET_BANK = {}
for _, row in df_filtered.iterrows():
    name = str(row['Cus;Name']).strip()
    gps_str = str(row['GPS']).strip()
    if ',' in gps_str:
        try:
            lat, lon = map(float, gps_str.split(','))
            OUTLET_BANK[name] = (lat, lon)
        except ValueError:
            continue

if not OUTLET_BANK:
    st.warning("No outlets match your search filter or some GPS data is missing a comma.")
    st.stop()

# --- CHECKBOX SELECTION ---
st.subheader(f"📋 Outlets Found ({len(OUTLET_BANK)})")

col_toggle1, col_toggle2 = st.columns(2)
with col_toggle1:
    select_all = st.button("✅ Select All Visible")
with col_toggle2:
    clear_all = st.button("❌ Clear All")

if 'selected_list' not in st.session_state or clear_all:
    st.session_state.selected_list = []
if select_all:
    st.session_state.selected_list = list(OUTLET_BANK.keys())

selected_outlets = []
for outlet_name in OUTLET_BANK.keys():
    is_checked = outlet_name in st.session_state.selected_list or select_all
    if st.checkbox(f"📍 {outlet_name}", value=is_checked, key=f"check_{outlet_name}"):
        selected_outlets.append(outlet_name)

# --- ROUTE OPTIMIZATION ENGINE ---
if st.button("🚀 OPTIMIZE MY ROUTE", type="primary"):
    if not selected_outlets:
        st.error("Please select at least one outlet checkbox!")
    else:
        route_stops = selected_outlets
        coordinates = [OUTLET_BANK[name] for name in route_stops]
        
        start_coord = coordinates[0]
        dest_coords = coordinates[1:]
        dest_indices = list(range(len(dest_coords)))
        best_distance = float('inf')
        best_path = []
        
        for perm in itertools.permutations(dest_indices):
            current_distance = 0
            current_path = [0]
            
            if perm:
                current_distance += geodesic(start_coord, dest_coords[perm[0]]).kilometers
                current_path.append(perm[0] + 1)
                for i in range(len(perm) - 1):
                    current_distance += geodesic(dest_coords[perm[i]], dest_coords[perm[i+1]]).kilometers
                    current_path.append(perm[i+1] + 1)
                current_distance += geodesic(dest_coords[perm[-1]], start_coord).kilometers
                current_path.append(0)
            else:
                current_path.append(0)
                
            if current_distance < best_distance:
                best_distance = current_distance
                best_path = current_path

        st.session_state.best_path = best_path
        st.session_state.route_stops = route_stops
        st.session_state.total_distance = best_distance
        st.session_state.route_calculated = True

# --- DISPLAY MAP AND LINKS ---
if getattr(st.session_state, 'route_calculated', False):
    saved_stops = st.session_state.route_stops
    saved_path = st.session_state.best_path
    coords_list = [OUTLET_BANK[name] for name in saved_stops]
    
    st.success(f"✅ Route Optimized: {st.session_state.total_distance:.1f} km")
    
    # Official Google Maps Mobile Launch Deep Link
    gmaps_base = "https://www.google.com/maps/dir/"
    ordered_coords_strings = [f"{coords_list[idx][0]},{coords_list[idx][1]}" for idx in saved_path]
    full_gmaps_url = gmaps_base + "/".join(ordered_coords_strings[:10])

    st.link_button("🗺️ OPEN BATCH IN GOOGLE MAPS APP", full_gmaps_url, use_container_width=True)

    # Preview Map Frame
    m = folium.Map(location=coords_list[0], zoom_start=13)
    path_coords = [coords_list[idx] for idx in saved_path]
    folium.PolyLine(path_coords, color="blue", weight=5).add_to(m)
    
    for name, coord in OUTLET_BANK.items():
        if name in saved_stops:
            folium.Marker(coord, popup=name, icon=folium.Icon(color='green')).add_to(m)
            
    st_folium(m, width=700, height=350, key="manual_filtered_map")
    
    st.subheader("🏁 Driving Sequence")
    for step, idx in enumerate(saved_path[:-1]):
        stop_name = saved_stops[idx]
        lat, lon = OUTLET_BANK[stop_name]
        single_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
        
        label = f"STARTING POINT: {stop_name}" if step == 0 else f"STOP {step}: {stop_name}"
        st.link_button(f"🧭 {label}", single_url, use_container_width=True)
