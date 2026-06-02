import streamlit as st
import folium
from streamlit_folium import st_folium
import itertools
from geopy.distance import geodesic
import urllib.parse
import pandas as pd
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="Delivery Pro", layout="wide")

st.title("🚚 Live Location Delivery Router")
st.write("Routes will automatically start from your current iPhone GPS position.")

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
        st.error("Connection Error. Please double-check that 'Anyone with the link' is set to Viewer inside Google Sheets Share settings.")
        return None

df_raw = load_sheet_data(GSHEET_URL)

if df_raw is None:
    st.info("Waiting for valid Google Sheet data connection...")
    st.stop()

# --- GET YOUR LIVE IPHONE GPS LOCATION ---
st.subheader("📍 Your Current Location")
# This triggers the standard iPhone pop-up asking for permission to use your location
user_location = streamlit_js_eval(data_string="colloquial", function_name="get_location", key="get_user_gps")

if not user_location:
    st.warning("🔄 Fetching your current phone GPS location... Please tap 'Allow' if your iPhone asks for location permissions.")
    current_gps = (16.8409, 96.1735) # Fallback to your standard depot location if GPS loads slowly
else:
    current_gps = (user_location['coords']['latitude'], user_location['coords']['longitude'])
    st.success(f"📍 GPS Location Locked: {current_gps[0]:.4f}, {current_gps[1]:.4f}")

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
        
        # Inject your live phone location as Stop #0
        start_coord = current_gps
        dest_coords = coordinates
        dest_indices = list(range(len(dest_coords)))
        
        best_distance = float('inf')
        best_path = []
        
        # Calculate best driving loop starting from where you stand
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
        st.session_state.route_stops = ["My Current Location"] + route_stops
        st.session_state.total_distance = best_distance
        st.session_state.route_calculated = True

# --- DISPLAY MAP AND LINKS ---
if getattr(st.session_state, 'route_calculated', False):
    saved_stops = st.session_state.route_stops
    saved_path = st.session_state.best_path
    
    # Reconstruct the tracking layout array
    coords_list = [current_gps] + [OUTLET_BANK[name] for name in saved_stops[1:]]
    
    st.success(f"✅ Route Optimized: {st.session_state.total_distance:.1f} km")
    
    # Official Google Maps Mobile Launch Deep Link
    gmaps_base = "https://www.google.com/maps/dir/?api=1&origin=Paris%2CFrance&destination=Cherbourg%2CFrance&travelmode=driving&waypoints=Versailles%2CFrance%7CChartres%2CFrance%7CLe+Mans%2CFrance%7CCaen%2CFrance"
    ordered_coords_strings = [f"{coords_list[idx][0]},{coords_list[idx][1]}" for idx in saved_path]
    full_gmaps_url = gmaps_base + "/".join(ordered_coords_strings[:10])

    st.link_button("🗺️ OPEN BATCH IN GOOGLE MAPS APP", full_gmaps_url, use_container_width=True)

    # Preview Map Frame
    m = folium.Map(location=current_gps, zoom_start=13)
    path_coords = [coords_list[idx] for idx in saved_path]
    folium.PolyLine(path_coords, color="blue", weight=5).add_to(m)
    
    folium.Marker(current_gps, popup="My Position", icon=folium.Icon(color='red', icon='android')).add_to(m)
    for name, coord in OUTLET_BANK.items():
        if name in saved_stops:
            folium.Marker(coord, popup=name, icon=folium.Icon(color='green')).add_to(m)
            
    st_folium(m, width=700, height=350, key="manual_filtered_map")
    
    st.subheader("🏁 Driving Sequence")
    for step, idx in enumerate(saved_path[:-1]):
        stop_name = saved_stops[idx]
        lat, lon = coords_list[idx]
        single_url = f"
