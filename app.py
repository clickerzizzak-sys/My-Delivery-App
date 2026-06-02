import streamlit as st
import folium
from streamlit_folium import st_folium
import itertools
from geopy.distance import geodesic
import urllib.parse
import pandas as pd
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="Delivery Pro", layout="wide")

st.title("🚚 Manual Control Delivery Router")
st.write("Search, filter, and choose your outlets manually from your sheet.")

# --- CONNECT TO YOUR GOOGLE SHEET ---
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1koRRrPEzAIOlt1LW8sFW6WdY2aoR5l-qogaua3DH6zg/edit?usp=drivesdk"

@st.cache_data(ttl=2)
def load_sheet_data(url):
    try:
        base_url = url.split('/edit')[0]
        csv_url = f"{base_url}/gviz/tq?tqx=out:csv"
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error("Connection Error. Please verify your Google Sheets Share settings are set to 'Anyone with the link can view'.")
        return None

df_raw = load_sheet_data(GSHEET_URL)

if df_raw is None:
    st.info("Waiting for valid Google Sheet data connection...")
    st.stop()

# --- GET YOUR LIVE IPHONE GPS LOCATION WITH INSTANT FALLBACK ---
st.subheader("📍 Your Starting Location")
user_location = streamlit_js_eval(data_string="colloquial", function_name="get_location", key="get_user_gps")

# Updated per your exact coordinate request!
DEFAULT_START_LAT = 16.9128391
DEFAULT_START_LON = 96.1534666

if not user_location:
    st.info("🔄 Waiting for phone GPS signal... Using your custom starting position as the baseline.")
    current_gps = (DEFAULT_START_LAT, DEFAULT_START_LON)
else:
    current_gps = (user_location['coords']['latitude'], user_location['coords']['longitude'])
    st.success(f"✅ Live GPS Position Active: {current_gps[0]:.5f}, {current_gps[1]:.5f}")

# --- MANUAL SEARCH FILTER BAR ---
st.subheader("🔍 Filter Outlets")
search_query = st.text_input("Type a day (e.g., Wed, Mon) or name to filter your list:", "Tue").strip()

if search_query:
    df_filtered = df_raw[
        df_raw['Cus;Name'].astype(str).str.contains(search_query, case=False, na=False) |
        df_raw['Service Day'].astype(str).str.contains(search_query, case=False, na=False)
    ]
else:
    df_filtered = df_raw.copy()

# Convert raw sheet rows to clean coordinate dictionary coordinates
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
    st.warning("No outlets found matching your search term.")
    st.stop()

# --- CHECKBOX SELECTION LAYOUT ---
st.subheader(f"📋 Available Outlets ({len(OUTLET_BANK)})")

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
        st.error("Please select at least one destination checkbox above!")
    else:
        route_stops = selected_outlets
        coordinates = [OUTLET_BANK[name] for name in route_stops]
        
        # Set start point to your locked coordinates
        start_coord = current_gps
        dest_coords = coordinates
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
        st.session_state.route_stops = ["My Start Location"] + route_stops
        st.session_state.total_distance = best_distance
        st.session_state.route_calculated = True

# --- OUTPUT AND MAP LAYOUTS ---
if getattr(st.session_state, 'route_calculated', False):
    saved_stops = st.session_state.route_stops
    saved_path = st.session_state.best_path
    
    coords_list = [current_gps] + [OUTLET_BANK[name] for name in saved_stops[1:]]
    
    st.success(f"✅ Route Optimized! Combined Distance: {st.session_state.total_distance:.2f} km")
    
    # Clean universal navigation links
    origin_str = f"{current_gps[0]},{current_gps[1]}"
    ordered_destinations = [coords_list[idx] for idx in saved_path[1:-1]]
    
    if ordered_destinations:
        final_dest = f"{ordered_destinations[-1][0]},{ordered_destinations[-1][1]}"
        mid_waypoints = ordered_destinations[:-1]
        waypoint_coords_string = "|".join([f"{c[0]},{c[1]}" for c in mid_waypoints])
        encoded_waypoints = urllib.parse.quote(waypoint_coords_string)
        
        gmaps_url = f"https://www.google.com/maps/dir/?api=1&origin={origin_str}&destination={final_dest}&waypoints={encoded_waypoints}&travelmode=driving"
        st.link_button("🗺️ LAUNCH BATCH MAPS ROUTE", gmaps_url, use_container_width=True)

    # Render Visual Preview Map
    m = folium.Map(location=current_gps, zoom_start=13)
    path_coords = [coords_list[idx] for idx in saved_path]
    folium.PolyLine(path_coords, color="blue", weight=5).add_to(m)
    
    folium.Marker(current_gps, popup="My Start Position", icon=folium.Icon(color='red', icon='home')).add_to(m)
    for name, coord in OUTLET_BANK.items():
        if name in saved_stops:
            folium.Marker(coord, popup=name, icon=folium.Icon(color='green')).add_to(m)
            
    st_folium(m, width=700, height=350, key="manual_filtered_map")
    
    st.subheader("🏁 Driving Step Sequence")
    for step, idx in enumerate(saved_path[:-1]):
        stop_name = saved_stops[idx]
        target_lat, target_lon = coords_list[idx]
        
        single_stop_url = f"https://www.google.com/maps/search/?api=1&query={target_lat},{target_lon}"
        
        label_text = f"START HERE: {stop_name}" if step == 0 else f"STOP {step}: {stop_name}"
        st.link_button(f"🧭 {label_text}", single_stop_url, use_container_width=True)
