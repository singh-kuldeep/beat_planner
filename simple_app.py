import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
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

# Create sidebar for file upload
with st.sidebar:
    st.header("Upload Merchant Data")
    
    uploaded_file = st.file_uploader(
        "Choose CSV file",
        type="csv",
        help="Required columns: merchant_code, latitude, longitude, mobile_bde_id_2"
    )
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            validation_result = validate_csv_format(df)
            
            if validation_result['valid']:
                st.session_state.merchant_data = df
                st.success(f"✅ Loaded {len(df)} merchants")
                
                # Show sample data
                st.subheader("Data Preview")
                st.dataframe(df.head(3))
                
                # Sales executive dropdown
                st.subheader("Select Sales Executive")
                sales_executives = sorted(df['mobile_bde_id_2'].unique())
                selected_executive = st.selectbox(
                    "Sales Executive:",
                    options=sales_executives
                )
                
                # Territory creation
                st.subheader("Create Territory")
                territory_name = st.text_input("Territory Name:")
                territory_color = st.color_picker("Color:", "#FF0000")
                radius_km = st.slider("Radius (km):", 0.5, 10.0, 2.0, 0.5)
                
                if territory_name:
                    st.info("Click on the map to create territory")
                
            else:
                st.error(f"❌ {validation_result['error']}")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Main content
if st.session_state.merchant_data is not None and 'selected_executive' in locals():
    # Filter data for selected executive
    filtered_data = st.session_state.merchant_data[
        st.session_state.merchant_data['mobile_bde_id_2'] == selected_executive
    ]
    
    if len(filtered_data) > 0:
        st.subheader(f"Map for {selected_executive}")
        
        # Calculate map center
        center_lat, center_lon = calculate_map_center(filtered_data)
        
        # Create simple map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=10
        )
        
        # Add merchant markers
        for idx, row in filtered_data.iterrows():
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=5,
                popup=f"Merchant: {row['merchant_code']}",
                color='blue',
                fillColor='blue',
                fillOpacity=0.7
            ).add_to(m)
        
        # Add existing territories
        for territory in st.session_state.territories:
            if territory['executive'] == selected_executive:
                folium.Circle(
                    location=[territory['center_lat'], territory['center_lon']],
                    radius=territory['radius'],
                    color=territory['color'],
                    weight=3,
                    fillOpacity=0.2
                ).add_to(m)
        
        # Display map
        try:
            map_data = st_folium(m, width=700, height=500, returned_objects=["last_clicked"])
            
            # Handle territory creation
            if map_data['last_clicked'] and territory_name and territory_name.strip():
                clicked_lat = map_data['last_clicked']['lat']
                clicked_lon = map_data['last_clicked']['lng']
                radius_meters = radius_km * 1000
                
                # Get merchants in circle
                assigned_merchants = st.session_state.territory_manager.get_merchants_in_circle(
                    filtered_data, clicked_lat, clicked_lon, radius_meters
                )
                
                # Create territory
                new_territory = {
                    'name': territory_name.strip(),
                    'center_lat': clicked_lat,
                    'center_lon': clicked_lon,
                    'radius': radius_meters,
                    'color': territory_color,
                    'merchants': assigned_merchants,
                    'executive': selected_executive
                }
                
                st.session_state.territories.append(new_territory)
                st.success(f"Created territory '{territory_name}' with {len(assigned_merchants)} merchants")
                st.rerun()
                
        except Exception as e:
            st.error(f"Map loading error: {str(e)}")
            st.info("Please refresh the page and try again")
        
        # Show statistics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Merchants", len(filtered_data))
        with col2:
            assigned_count = sum(len(t['merchants']) for t in st.session_state.territories if t['executive'] == selected_executive)
            st.metric("Assigned", assigned_count)
        
        # Export functionality
        if st.session_state.territories:
            if st.button("📥 Download Territory Data"):
                export_data = st.session_state.territory_manager.export_territories(
                    st.session_state.merchant_data, st.session_state.territories
                )
                csv_buffer = io.StringIO()
                export_data.to_csv(csv_buffer, index=False)
                
                st.download_button(
                    label="Download CSV",
                    data=csv_buffer.getvalue(),
                    file_name="territory_assignments.csv",
                    mime="text/csv"
                )
    else:
        st.warning(f"No merchants found for {selected_executive}")
else:
    st.info("Please upload a CSV file to get started")
    
    # Show expected format
    st.subheader("Expected CSV Format")
    sample_data = pd.DataFrame({
        'merchant_code': ['M001', 'M002', 'M003'],
        'latitude': [28.6139, 28.7041, 28.5355],
        'longitude': [77.2090, 77.1025, 77.3910],
        'mobile_bde_id_2': ['SE001', 'SE002', 'SE001']
    })
    st.dataframe(sample_data)