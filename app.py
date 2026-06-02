import streamlit as st
import folium
from streamlit_folium import st_folium
import itertools
from geopy.distance import geodesic

st.set_page_config(page_title="My Delivery Router", layout="wide")

st.title("🚚 My Private Delivery Router")
st.write("Select your outlets below to generate the absolute best driving route.")

# --- THE GPS STORAGE BANK ---
OUTLET_BANK = {
    "Depot / Starting Point": (16.8409, 96.1735), 
    "Daw Khin Hla - ": (16.8440648,96.1847088),
    "Store Outlet 2 - North Junction": (16.8660, 96.1450),
    "Store Outlet 3 - East Market": (16.8050, 96.2100),
    "Store Outlet 4 - Hlaing Township": (16.8480, 96.1240),
    "Store Outlet 5 - Tamwe Plaza": (16.8120, 96.1680),
}

# Initialize a memory bank so the map doesn't vanish on mobile
if 'route_calculated' not in st.session_state:
    st.session_state.route_calculated = False
if 'best_path' not in st.session_state:
    st.session_state.best_path = []
if 'route_stops' not in st.session_state:
    st.session_state.route_stops = []
if 'total_distance' not in st.session_state:
    st.session_state.total_distance = 0.0

st.header("📋 Select Today's Outlets")
start_node = "Depot / Starting Point"

selected_outlets = []
for outlet_name in OUTLET_BANK.keys():
    if outlet_name != start_node:
        # If you check or uncheck a box, clear the old map state
        if st.checkbox(f"📍 {outlet_name}", value=False, key=f"check_{outlet_name}"):
            selected_outlets.append(outlet_name)

# Trigger calculation
if st.button("🚀 Calculate Best Route", type="primary"):
    if not selected_outlets:
        st.error("Please check at least one store outlet to map your route!")
        st.session_state.route_calculated = False
    else:
        route_stops = [start_node] + selected_outlets
        coordinates = [OUTLET_BANK[name] for name in route_stops]
        
        with st.spinner("Calculating the shortest driving sequence..."):
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

            # Store results in memory so they persist across page refreshes
            st.session_state.best_path = best_path
            st.session_state.route_stops = route_stops
            st.session_state.total_distance = best_distance
            st.session_state.route_calculated = True

# --- RENDER MAP AND ROUTE IF CALCULATED ---
if st.session_state.route_calculated:
    st.success(f"✅ Route Optimized! Total Distance: {st.session_state.total_distance:.2f} km")
    
    col_map, col_list = st.columns([2, 1])
    
    # Rebuild coordinates from saved state
    saved_stops = st.session_state.route_stops
    saved_path = st.session_state.best_path
    coords_list = [OUTLET_BANK[name] for name in saved_stops]
    
    with col_list:
        st.subheader("Turn Order")
        for step, idx in enumerate(saved_path):
            stop_name = saved_stops[idx]
            lat, lon = OUTLET_BANK[stop_name]
            gmaps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            
            if step == 0:
                st.markdown(f"**Start:** [{stop_name}]({gmaps_url})")
            elif step == len(saved_path) - 1:
                st.markdown(f"**Return to:** [{stop_name}]({gmaps_url})")
            else:
                st.markdown(f"{step}. **Go to:** [{stop_name}]({gmaps_url}) 🚗")
    
    with col_map:
        m = folium.Map(location=coords_list[0], zoom_start=12)
        path_coords = [coords_list[idx] for idx in saved_path]
        folium.PolyLine(path_coords, color="blue", weight=5, opacity=0.8).add_to(m)
        
        for idx, name in enumerate(saved_stops):
            coord = OUTLET_BANK[name]
            if name == start_node:
                folium.Marker(coord, popup=name, icon=folium.Icon(color='red', icon='home')).add_to(m)
            else:
                folium.Marker(coord, popup=name, icon=folium.Icon(color='green')).add_to(m)
        
        # Using a fixed key prevents the component from unmounting instantly on mobile view
        st_folium(m, width=700, height=500, key="fixed_delivery_map")
