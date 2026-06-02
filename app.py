import streamlit as st
import folium
from streamlit_folium import st_folium
import itertools
from geopy.distance import geodesic

st.set_page_config(page_title="My Delivery Router", layout="wide")

st.title("🚚 My Private Delivery Router")
st.write("Select your outlets below to generate the absolute best driving route.")

# --- THE GPS STORAGE BANK ---
# This is your permanent database. You can add all 60+ of your outlets here!
# Format: "Outlet Nickname": (Latitude, Longitude)
OUTLET_BANK = {
    "Depot / Starting Point": (16.8409, 96.1735), # Replace with your home/depot GPS
    "Store Outlet 1 - Downtown": (16.7762, 96.1548),
    "Store Outlet 2 - North Junction": (16.8660, 96.1450),
    "Store Outlet 3 - East Market": (16.8050, 96.2100),
    "Store Outlet 4 - Hlaing Township": (16.8480, 96.1240),
    "Store Outlet 5 - Tamwe Plaza": (16.8120, 96.1680),
    # You can easily paste all 60+ of your outlets here following this exact format!
}

# --- STORE SELECTOR SCREEN ---
st.header("📋 Select Today's Outlets")
st.write(f"Total outlets in your database: {len(OUTLET_BANK) - 1}")

start_node = "Depot / Starting Point"

# Generate checkboxes for all outlets in your bank
selected_outlets = []
for outlet_name in OUTLET_BANK.keys():
    if outlet_name != start_node:
        if st.checkbox(f"📍 {outlet_name}", value=False, key=outlet_name):
            selected_outlets.append(outlet_name)

# --- ROUTE OPTIMIZATION ENGINE ---
if st.button("🚀 Calculate Best Route", type="primary"):
    if not selected_outlets:
        st.error("Please check at least one store outlet to map your route!")
    else:
        # Combine start point with selected stores
        route_stops = [start_node] + selected_outlets
        coordinates = [OUTLET_BANK[name] for name in route_stops]
        
        with st.spinner("Calculating the shortest driving sequence..."):
            # Math: Solve Traveling Salesperson Problem for selected stops
            start_coord = coordinates[0]
            dest_coords = coordinates[1:]
            dest_indices = list(range(len(dest_coords)))
            
            best_distance = float('inf')
            best_path = []
            
            # Shuffles and checks every combination to find the absolute shortest path
            for perm in itertools.permutations(dest_indices):
                current_distance = 0
                current_path = [0]
                
                current_distance += geodesic(start_coord, dest_coords[perm[0]]).kilometers
                current_path.append(perm[0] + 1)
                
                for i in range(len(perm) - 1):
                    current_distance += geodesic(dest_coords[perm[i]], dest_coords[perm[i+1]]).kilometers
                    current_path.append(perm[i+1] + 1)
                
                # Back to start
                current_distance += geodesic(dest_coords[perm[-1]], start_coord).kilometers
                current_path.append(0)
                
                if current_distance < best_distance:
                    best_distance = current_distance
                    best_path = current_path

            # --- DISPLAY THE AUTOMATED RESULTS ---
            st.success(f"✅ Route Optimized! Total Distance: {best_distance:.2f} km")
            
            col_map, col_list = st.columns([2, 1])
            
            with col_list:
                st.subheader("Turn Order")
                for step, idx in enumerate(best_path):
                    stop_name = route_stops[idx]
                    lat, lon = OUTLET_BANK[stop_name]
                    
                    # Generates a direct single-click link to open Google Maps navigation for this specific stop
                    gmaps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                    
                    if step == 0:
                        st.markdown(f"**Start:** [{stop_name}]({gmaps_url})")
                    elif step == len(best_path) - 1:
                        st.markdown(f"**Return to:** [{stop_name}]({gmaps_url})")
                    else:
                        st.markdown(f"{step}. **Go to:** [{stop_name}]({gmaps_url}) 🚗")
            
            with col_map:
                # Create the live interactive tracking map
                m = folium.Map(location=start_coord, zoom_start=12)
                path_coords = [coordinates[idx] for idx in best_path]
                folium.PolyLine(path_coords, color="blue", weight=5, opacity=0.8).add_to(m)
                
                for idx, name in enumerate(route_stops):
                    coord = OUTLET_BANK[name]
                    if name == start_node:
                        folium.Marker(coord, popup=name, icon=folium.Icon(color='red', icon='home')).add_to(m)
                    else:
                        folium.Marker(coord, popup=name, icon=folium.Icon(color='green')).add_to(m)
                
                st_folium(m, width=700, height=500)
