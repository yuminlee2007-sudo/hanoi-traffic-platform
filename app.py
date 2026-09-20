import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import pandas as pd
import numpy as np
import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="TNS Traffic & Mobility Portal",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .main-header { font-size: 24px; font-weight: 700; color: #1e293b; letter-spacing: -0.5px; }
    .sub-header { font-size: 13px; color: #64748b; margin-bottom: 20px; }
    .highlight { color: #2563eb; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown('<div class="main-header">🏫 TRUE NORTH INTERNATIONAL SCHOOL (TNS) TRAFFIC PORTAL</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Real-time Traffic Monitoring & Predictive Route Planner for Mỗ Lao, Hà Đông Area</div>', unsafe_allow_html=True)

# --- Default API Key ---
DEFAULT_API_KEY = "6a382ec4-fa1c-4046-8e9c-2945cd81610b"

# --- True North School & Key Nearby Locations (Ha Dong) ---
TNS_COORDS = [20.9835, 105.7865]

HANOI_NODES = {
    "🏫 True North Int'l School (TNS Campus)": [20.9835, 105.7865],
    "🚉 Mỗ Lao Metro Station (Trần Phú)": [20.9785, 105.7890],
    "🚦 Tố Hữu - Vũ Trọng Khánh Junction": [20.9850, 105.7830],
    "🛍️ AEON Mall Hà Đông": [20.9880, 105.7580],
    "🌳 Văn Quán Lake Park": [20.9740, 105.7920],
    "🏢 Thanh Xuân Interchange (Ring Road 3)": [20.9982, 105.8055],
    "🏛️ Ba Đình / Old Quarter Center": [21.0285, 105.8542],
    "🏢 Cầu Giấy District Hub": [21.0362, 105.7906]
}

# --- School Surrounding Arterial Corridors ---
HANOI_CORRIDORS = {
    "Vũ Trọng Khánh (TNS Main School Front Road)": {
        "coords": [[20.9785, 105.7890], [20.9835, 105.7865], [20.9850, 105.7830]],
        "base_density": 85
    },
    "Tố Hữu Arterial Axis (Mỗ Lao Intersection)": {
        "coords": [[20.9780, 105.7680], [20.9850, 105.7830], [20.9910, 105.7950]],
        "base_density": 80
    },
    "Trần Phú Avenue (Hà Đông Main Link)": {
        "coords": [[20.9712, 105.7766], [20.9785, 105.7890], [20.9830, 105.7920]],
        "base_density": 75
    },
    "Nguyễn Văn Lộc Food & Commercial Street": {
        "coords": [[20.9785, 105.7890], [20.9820, 105.7880], [20.9860, 105.7870]],
        "base_density": 65
    }
}

# --- Sidebar Controls ---
st.sidebar.markdown("### ⚙️ System Controls")

api_key = st.sidebar.text_input(
    "TomTom Traffic API Key:",
    value=DEFAULT_API_KEY,
    type="password"
)

forecast_mins = st.sidebar.select_slider(
    "Predictive Time Horizon",
    options=[0, 15, 30, 45, 60, 90],
    value=0,
    format_func=lambda x: "Real-Time (Live Feed)" if x == 0 else f"+{x} Minutes Ahead"
)

weather = st.sidebar.selectbox(
    "Environmental Weather Factor",
    ["Clear / Dry", "Light Rain", "Heavy Rain / Storm", "Dense Fog"]
)

weather_factor = {
    "Clear / Dry": 1.0,
    "Light Rain": 1.18,
    "Heavy Rain / Storm": 1.45,
    "Dense Fog": 1.25
}[weather]

# Time computation
now = datetime.datetime.now()
target_time = now + datetime.timedelta(minutes=forecast_mins)
target_hour = target_time.hour

# School Pick-up / Drop-off Peak Hour Weighting (7-9 AM, 3-6 PM)
is_school_peak = (7 <= target_hour <= 9 or 15 <= target_hour <= 18)
peak_multiplier = 1.40 if is_school_peak else 1.0
base_network_index = min(100, int(40 * peak_multiplier * weather_factor))

# Navigation Tabs
tab1, tab2 = st.tabs(["🗺️ TNS Vicinity Live & Predictive Traffic Map", "🚗 School Commute Route Planner"])

# ==========================================
# TAB 1: VICINITY TRAFFIC MAP
# ==========================================
with tab1:
    col_map, col_info = st.columns([2.2, 1])
    
    corridor_summary = []
    
    for c_name, c_data in HANOI_CORRIDORS.items():
        c_index = min(100, int(base_network_index * (c_data["base_density"] / 50.0)))
        
        if c_index < 45:
            color = "#0066ff"  # Blue (Free Flow)
            status = "BLUE (Free Flow)"
            avg_speed = int(45 * (1 - c_index / 220))
        elif c_index < 70:
            color = "#f39c12"  # Yellow (Moderate)
            status = "YELLOW (Moderate)"
            avg_speed = int(28 * (1 - c_index / 220))
        else:
            color = "#e74c3c"  # Red (Congested)
            status = "RED (Congested)"
            avg_speed = max(8, int(15 * (1 - c_index / 220)))
            
        corridor_summary.append({
            "Corridor Name": c_name,
            "Congestion Index": f"{c_index} / 100",
            "Flow Status": status,
            "Est Speed": f"{avg_speed} km/h",
            "raw_color": color,
            "raw_coords": c_data["coords"]
        })

    with col_map:
        st.subheader(f"True North School Vicinity Traffic ({target_time.strftime('%H:%M')} Target)")
        
        # Center directly on True North International School with close zoom
        m = folium.Map(location=TNS_COORDS, zoom_start=15, tiles="cartodbpositron")
        
        # Mark True North International School
        folium.Marker(
            TNS_COORDS,
            popup="<b>True North International School</b><br>Mo Lao, Ha Dong",
            tooltip="🏫 True North School Campus",
            icon=folium.Icon(color="red", icon="star")
        ).add_to(m)

        # Inject Live Traffic Tile Overlay if API Key exists & real-time mode selected
        if api_key and forecast_mins == 0:
            traffic_tile_url = f"https://api.tomtom.com/traffic/map/4/tile/flow/relative0/{{z}}/{{x}}/{{y}}.png?key={api_key}"
            folium.TileLayer(
                tiles=traffic_tile_url,
                attr="TomTom Traffic Feed",
                name="Live Traffic Layer",
                overlay=True,
                control=True
            ).add_to(m)
        else:
            # Synthetic PolyLine corridors for predictive mode
            for c in corridor_summary:
                folium.PolyLine(
                    locations=c["raw_coords"],
                    color=c["raw_color"],
                    weight=8,
                    opacity=0.85,
                    tooltip=f"<b>{c['Corridor Name']}</b><br>Status: {c['Flow Status']}<br>Speed: {c['Est Speed']}"
                ).add_to(m)
            
        st_folium(m, width=820, height=520)

    with col_info:
        st.subheader("School Road Metrics")
        df_display = pd.DataFrame(corridor_summary)[["Corridor Name", "Congestion Index", "Flow Status", "Est Speed"]]
        st.dataframe(df_display, hide_index=True, use_container_width=True)
        
        st.markdown("""
        **Traffic Flow Index Legend:**
        * 🔵 **BLUE:** Free Flow (> 35 km/h)
        * 🟡 **YELLOW:** Moderate Density (20 - 35 km/h)
        * 🔴 **RED:** Heavy Congestion (< 20 km/h)
        
        *🏫 **School Peak Hours:** 07:00-09:00 & 15:00-18:00*
        """)

# ==========================================
# TAB 2: COMMUTE ROUTE PLANNER
# ==========================================
with tab2:
    st.subheader("📍 TNS Commute & Driving Route Planner")
    st.write("Calculate driving distance, estimated travel time, and delays to/from True North International School.")
    
    col_from, col_to = st.columns(2)
    with col_from:
        origin = st.selectbox("Origin (From):", list(HANOI_NODES.keys()), index=0)
    with col_to:
        destination = st.selectbox("Destination (To):", list(HANOI_NODES.keys()), index=1)
        
    if origin == destination:
        st.warning("Please select two distinct locations to calculate route metrics.")
    else:
        orig_coords = HANOI_NODES[origin]
        dest_coords = HANOI_NODES[destination]
        
        # Real OSRM Driving Engine API
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{orig_coords[1]},{orig_coords[0]};{dest_coords[1]},{dest_coords[0]}?overview=full&geometries=geojson"
        
        try:
            res = requests.get(osrm_url, timeout=5)
            if res.status_code == 200:
                route_data = res.json()["routes"][0]
                
                dist_km = round(route_data["distance"] / 1000.0, 1)
                base_duration_min = route_data["duration"] / 60.0
                
                # Dynamic Congestion Adjustment
                traffic_delay_factor = (base_network_index / 35.0)
                actual_duration_min = round(base_duration_min * max(1.0, traffic_delay_factor))
                delay_min = max(0, actual_duration_min - round(base_duration_min))
                avg_speed = round(dist_km / (actual_duration_min / 60.0), 1) if actual_duration_min > 0 else 0
                
                # Display Route Metrics
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Driving Distance", f"{dist_km} km")
                m2.metric("Est. Travel Time", f"{actual_duration_min} mins")
                m3.metric("Traffic Delay", f"+{delay_min} mins")
                m4.metric("Avg Speed", f"{avg_speed} km/h")
                
                # Render Route Map
                route_map = folium.Map(
                    location=[(orig_coords[0]+dest_coords[0])/2, (orig_coords[1]+dest_coords[1])/2],
                    zoom_start=14,
                    tiles="cartodbpositron"
                )
                
                raw_coords = route_data["geometry"]["coordinates"]
                poly_coords = [[c[1], c[0]] for c in raw_coords]
                
                route_color = "#0066ff" if base_network_index < 45 else ("#f39c12" if base_network_index < 70 else "#e74c3c")
                
                folium.PolyLine(poly_coords, color=route_color, weight=6, opacity=0.85).add_to(route_map)
                folium.Marker(orig_coords, popup=f"Origin: {origin}", icon=folium.Icon(color="green", icon="play")).add_to(route_map)
                folium.Marker(dest_coords, popup=f"Destination: {destination}", icon=folium.Icon(color="red", icon="stop")).add_to(route_map)
                
                st_folium(route_map, width=850, height=420)
            else:
                st.error("Could not fetch route metrics. Please try again.")
        except Exception as e:
            st.error("Network connection error while computing route.")
