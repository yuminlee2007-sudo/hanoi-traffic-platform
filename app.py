import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import pandas as pd
import numpy as np
import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="Hanoi Traffic & Mobility Platform",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Municipal Dashboard Styling ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .main-header { font-size: 24px; font-weight: 700; color: #0f172a; letter-spacing: -0.5px; }
    .sub-header { font-size: 13px; color: #64748b; margin-bottom: 20px; }
    .metric-card { background-color: #ffffff; border: 1px solid #e2e8f0; padding: 12px; border-radius: 6px; }
    </style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown('<div class="main-header">HANOI MUNICIPAL TRAFFIC & MOBILITY PLATFORM</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Real-time Traffic Monitoring, Weather-adjusted Predictive Analytics, and Point-to-Point Route Optimization</div>', unsafe_allow_html=True)

# --- Default API Key Configuration ---
DEFAULT_API_KEY = "6a382ec4-fa1c-4046-8e9c-2945cd81610b"

# --- Key Nodes in Hanoi Metropolitan Area ---
HANOI_NODES = {
    "Hà Đông Center": [20.9712, 105.7766],
    "Cầu Giấy District": [21.0362, 105.7906],
    "Hoàn Kiếm (Old Quarter)": [21.0285, 105.8542],
    "Nam Từ Liêm (Mỹ Đình)": [21.0172, 105.7708],
    "Thanh Xuân Interchange": [20.9982, 105.8055],
    "Ba Đình Hub": [21.0341, 105.8318],
    "Tây Hồ (West Lake South)": [21.0505, 105.8200],
    "Hai Bà Trưng Zone": [21.0100, 105.8500]
}

# --- Major Arterial Corridors ---
HANOI_CORRIDORS = {
    "Trần Phú - Nguyễn Trãi Corridor": {
        "coords": [[20.9712, 105.7766], [20.9830, 105.7920], [20.9982, 105.8055]],
        "base_density": 82
    },
    "Tố Hữu - Lê Văn Lương Axis": {
        "coords": [[20.9690, 105.7500], [20.9780, 105.7680], [21.0030, 105.8000]],
        "base_density": 75
    },
    "Ring Road 3 Elevated Arterial": {
        "coords": [[20.9982, 105.8055], [21.0172, 105.7708], [21.0362, 105.7906]],
        "base_density": 88
    },
    "Kim Mã - Nguyễn Thái Học Central Link": {
        "coords": [[21.0341, 105.8318], [21.0300, 105.8420], [21.0285, 105.8542]],
        "base_density": 60
    },
    "Võ Chí Công - West Lake Highway": {
        "coords": [[21.0362, 105.7906], [21.0505, 105.8200], [21.0750, 105.8150]],
        "base_density": 38
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

# Peak Hour Weighting
peak_multiplier = 1.35 if (7 <= target_hour <= 9 or 17 <= target_hour <= 19) else 1.0
base_network_index = min(100, int(38 * peak_multiplier * weather_factor))

# Navigation Tabs
tab1, tab2 = st.tabs(["🗺️ Citywide Real-Time & Predictive Traffic Map", "🚗 Point-to-Point Route Duration Planner"])

# ==========================================
# TAB 1: CITYWIDE TRAFFIC MAP
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
        st.subheader(f"Hanoi Metropolitan Traffic Map ({target_time.strftime('%H:%M')} Target)")
        m = folium.Map(location=[21.0150, 105.8150], zoom_start=12, tiles="cartodbpositron")
        
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
                    weight=7,
                    opacity=0.85,
                    tooltip=f"<b>{c['Corridor Name']}</b><br>Status: {c['Flow Status']}<br>Speed: {c['Est Speed']}"
                ).add_to(m)
            
        st_folium(m, width=820, height=520)

    with col_info:
        st.subheader("Corridor Metrics")
        df_display = pd.DataFrame(corridor_summary)[["Corridor Name", "Congestion Index", "Flow Status", "Est Speed"]]
        st.dataframe(df_display, hide_index=True, use_container_width=True)
        
        st.markdown("""
        **Traffic Flow Index Legend:**
        * 🔵 **BLUE:** Free Flow (> 35 km/h)
        * 🟡 **YELLOW:** Moderate Density (20 - 35 km/h)
        * 🔴 **RED:** Heavy Congestion (< 20 km/h)
        """)

# ==========================================
# TAB 2: POINT-TO-POINT ROUTE PLANNER (FROM -> TO)
# ==========================================
with tab2:
    st.subheader("📍 Point-to-Point Driving Route Estimator")
    st.write("Real-time network routing for travel distance, speed, and time delays across Hanoi.")
    
    col_from, col_to = st.columns(2)
    with col_from:
        origin = st.selectbox("Origin (From):", list(HANOI_NODES.keys()), index=0)
    with col_to:
        destination = st.selectbox("Destination (To):", list(HANOI_NODES.keys()), index=2)
        
    if origin == destination:
        st.warning("Please select two distinct locations to calculate route metrics.")
    else:
        orig_coords = HANOI_NODES[origin]
        dest_coords = HANOI_NODES[destination]
        
        # Real OSRM Global Driving Engine API
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
                    zoom_start=13,
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
