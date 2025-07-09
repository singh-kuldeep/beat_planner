import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
from territory_manager import TerritoryManager
from utils import validate_csv_format, calculate_map_center
import io

# Set page config
st.set_page_config(
    page_title="Sales Territory Management",
    page_icon="🗺️",
    layout="wide"
)

# Initialize session state
if 'territories' not in st.session_state:
    st.session_state.territories = []
if 'merchant_data' not in st.session_state:
    st.session_state.merchant_data = None
if 'territory_manager' not in st.session_state:
    st.session_state.territory_manager = TerritoryManager()

st.title("🗺️ Sales Territory Management System")

# Sidebar for controls
with st.sidebar:
    st.header("Controls")
    
    # File upload section
    st.subheader("📁 Upload Merchant Data")
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type="csv",
        help="CSV should contain: merchant_code, latitude, longitude, mobile_bde_id_2"
    )
    
    if uploaded_file is not None:
        try:
            # Read and validate CSV
            df = pd.read_csv(uploaded_file)
            validation_result = validate_csv_format(df)
            
            if validation_result['valid']:
                st.session_state.merchant_data = df
                st.success(f"✅ Loaded {len(df)} merchants successfully!")
                
                # Display data preview
                st.subheader("📊 Data Preview")
                st.dataframe(df.head(), use_container_width=True)
                
                # Sales executive selection
                st.subheader("👤 Select Sales Executive")
                sales_executives = sorted(df['mobile_bde_id_2'].unique())
                selected_executive = st.selectbox(
                    "Choose Sales Executive:",
                    options=sales_executives,
                    key="selected_executive"
                )
                
                # Territory management
                st.subheader("🎯 Territory Management")
                
                # New territory creation
                with st.expander("Create New Territory"):
                    territory_name = st.text_input(
                        "Territory Name:",
                        placeholder="Enter territory name..."
                    )
                    
                    territory_color = st.color_picker(
                        "Territory Color:",
                        value="#FF0000"
                    )
                    
                    st.info("💡 Click on the map to create a circle territory")
                
                # Existing territories
                if st.session_state.territories:
                    st.write("**Existing Territories:**")
                    for i, territory in enumerate(st.session_state.territories):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"🎯 {territory['name']}")
                            st.write(f"   📍 {len(territory['merchants'])} merchants")
                        with col2:
                            if st.button("🗑️", key=f"delete_{i}"):
                                st.session_state.territories.pop(i)
                                st.rerun()
                
                # Export section
                st.subheader("💾 Export Data")
                if st.session_state.territories:
                    if st.button("📥 Download Territory Assignments", use_container_width=True):
                        # Generate export CSV
                        export_data = st.session_state.territory_manager.export_territories(
                            st.session_state.merchant_data,
                            st.session_state.territories
                        )
                        
                        # Create download
                        csv_buffer = io.StringIO()
                        export_data.to_csv(csv_buffer, index=False)
                        csv_string = csv_buffer.getvalue()
                        
                        st.download_button(
                            label="📥 Download CSV",
                            data=csv_string,
                            file_name="territory_assignments.csv",
                            mime="text/csv"
                        )
                else:
                    st.info("Create territories to enable export")
                    
            else:
                st.error(f"❌ CSV validation failed: {validation_result['error']}")
                st.info("Required columns: merchant_code, latitude, longitude, mobile_bde_id_2")
                
        except Exception as e:
            st.error(f"❌ Error reading CSV file: {str(e)}")

# Main content area
if st.session_state.merchant_data is not None and 'selected_executive' in st.session_state:
    # Filter data for selected executive
    filtered_data = st.session_state.merchant_data[
        st.session_state.merchant_data['mobile_bde_id_2'] == st.session_state.selected_executive
    ].copy()
    
    if len(filtered_data) > 0:
        # Create map
        center_lat, center_lon = calculate_map_center(filtered_data)
        
        # Create folium map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=10,
            tiles="OpenStreetMap"
        )
        
        # Add merchant markers
        for idx, row in filtered_data.iterrows():
            # Check if merchant is assigned to any territory
            assigned_territory = None
            for territory in st.session_state.territories:
                if row['merchant_code'] in territory['merchants']:
                    assigned_territory = territory
                    break
            
            # Set marker color based on assignment
            if assigned_territory:
                marker_color = assigned_territory['color']
                popup_text = f"Merchant: {row['merchant_code']}<br>Territory: {assigned_territory['name']}"
            else:
                marker_color = 'blue'
                popup_text = f"Merchant: {row['merchant_code']}<br>Status: Unassigned"
            
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=6,
                popup=folium.Popup(popup_text, max_width=300),
                color='white',
                weight=2,
                fillColor=marker_color,
                fillOpacity=0.7
            ).add_to(m)
        
        # Add existing territories to map
        for territory in st.session_state.territories:
            folium.Circle(
                location=[territory['center_lat'], territory['center_lon']],
                radius=territory['radius'],
                color=territory['color'],
                weight=3,
                fillOpacity=0.1,
                popup=folium.Popup(f"Territory: {territory['name']}", max_width=300)
            ).add_to(m)
        
        # Display map and capture interactions
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader(f"📍 Merchants for {st.session_state.selected_executive}")
            map_data = st_folium(
                m,
                width=800,
                height=500,
                returned_objects=["last_object_clicked_tooltip", "last_clicked"],
                key="territory_map"
            )
            
            # Handle map clicks for territory creation
            if map_data['last_clicked'] is not None and 'territory_name' in locals():
                if territory_name and territory_name.strip():
                    # Create new territory
                    clicked_lat = map_data['last_clicked']['lat']
                    clicked_lon = map_data['last_clicked']['lng']
                    
                    # Default radius (can be made configurable)
                    radius_meters = 2000  # 2km radius
                    
                    # Calculate which merchants fall within this territory
                    assigned_merchants = st.session_state.territory_manager.get_merchants_in_circle(
                        filtered_data,
                        clicked_lat,
                        clicked_lon,
                        radius_meters
                    )
                    
                    new_territory = {
                        'name': territory_name.strip(),
                        'center_lat': clicked_lat,
                        'center_lon': clicked_lon,
                        'radius': radius_meters,
                        'color': territory_color,
                        'merchants': assigned_merchants,
                        'executive': st.session_state.selected_executive
                    }
                    
                    st.session_state.territories.append(new_territory)
                    st.success(f"✅ Created territory '{territory_name}' with {len(assigned_merchants)} merchants")
                    st.rerun()
                    
        with col2:
            st.subheader("📊 Statistics")
            
            total_merchants = len(filtered_data)
            assigned_merchants = set()
            for territory in st.session_state.territories:
                if territory['executive'] == st.session_state.selected_executive:
                    assigned_merchants.update(territory['merchants'])
            
            unassigned_count = total_merchants - len(assigned_merchants)
            
            st.metric("Total Merchants", total_merchants)
            st.metric("Assigned", len(assigned_merchants))
            st.metric("Unassigned", unassigned_count)
            
            # Territory breakdown
            if st.session_state.territories:
                st.subheader("🎯 Territory Breakdown")
                for territory in st.session_state.territories:
                    if territory['executive'] == st.session_state.selected_executive:
                        st.write(f"**{territory['name']}**")
                        st.write(f"📍 {len(territory['merchants'])} merchants")
                        st.write("---")
            
    else:
        st.warning(f"No merchants found for {st.session_state.selected_executive}")
        
else:
    # Welcome screen
    st.info("👋 Welcome! Please upload a CSV file to get started.")
    
    # Display expected CSV format
    st.subheader("📋 Expected CSV Format")
    sample_data = pd.DataFrame({
        'merchant_code': ['M001', 'M002', 'M003'],
        'latitude': [40.7128, 40.7589, 40.7505],
        'longitude': [-74.0060, -73.9851, -73.9934],
        'mobile_bde_id_2': ['SE001', 'SE002', 'SE001']
    })
    st.dataframe(sample_data, use_container_width=True)
