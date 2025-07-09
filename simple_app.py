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

st.title("🗺️ Sales Visit Planning System")

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
                
                # Check for existing circles in CSV
                existing_circles = []
                if 'visit_day' in df.columns and df['visit_day'].notna().any():
                    # Load existing circles from CSV
                    existing_circle_data = df[df['visit_day'].notna()].groupby(['visit_day']).first()
                    for visit_day, row in existing_circle_data.iterrows():
                        if pd.notna(row.get('circle_center_lat')) and pd.notna(row.get('circle_center_lon')):
                            merchants_in_circle = df[df['visit_day'] == visit_day]['merchant_code'].tolist()
                            existing_circles.append({
                                'name': visit_day,
                                'center_lat': row['circle_center_lat'],
                                'center_lon': row['circle_center_lon'],
                                'radius': row.get('circle_radius_meters', 2000),
                                'color': row.get('circle_color', '#FF0000'),
                                'merchants': merchants_in_circle,
                                'merchant_count': len(merchants_in_circle)
                            })
                    
                    if existing_circles:
                        st.session_state.territories = existing_circles
                        st.info(f"📍 Found {len(existing_circles)} existing visit circles in your data")
                
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
                
                # Visit circle creation
                st.subheader("Create Visit Circle")
                st.info("A visit circle represents the area a sales person will cover in one day")
                
                col1, col2 = st.columns(2)
                with col1:
                    visit_day = st.text_input("Visit Day/Name:", placeholder="e.g., Monday, Day1, Circle_1")
                    max_merchants_per_day = st.number_input("Max merchants per day:", min_value=1, max_value=50, value=10)
                with col2:
                    circle_color = st.color_picker("Circle Color:", "#FF0000")
                    radius_km = st.slider("Initial Radius (km):", 0.5, 10.0, 2.0, 0.5)
                
                if visit_day:
                    st.success(f"Ready! Click on map to create visit circle for {visit_day}")
                    st.info(f"Circle will be split if more than {max_merchants_per_day} merchants are found")
                
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
            # Check if merchant is assigned to any visit circle
            assigned_circle = None
            for circle in st.session_state.territories:
                if circle['executive'] == selected_executive and row['merchant_code'] in circle['merchants']:
                    assigned_circle = circle
                    break
            
            # Set marker color based on assignment
            if assigned_circle:
                marker_color = assigned_circle['color']
                popup_text = f"Merchant: {row['merchant_code']}<br>Visit Day: {assigned_circle['name']}"
            else:
                marker_color = 'blue'
                popup_text = f"Merchant: {row['merchant_code']}<br>Status: Unassigned"
            
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=6,
                popup=popup_text,
                color='white',
                weight=1,
                fillColor=marker_color,
                fillOpacity=0.8
            ).add_to(m)
        
        # Add existing visit circles
        for circle in st.session_state.territories:
            if circle['executive'] == selected_executive:
                folium.Circle(
                    location=[circle['center_lat'], circle['center_lon']],
                    radius=circle['radius'],
                    color=circle['color'],
                    weight=3,
                    fillOpacity=0.15,
                    popup=f"<b>Visit Day:</b> {circle['name']}<br><b>Merchants:</b> {circle['merchant_count']}<br><b>Radius:</b> {circle['radius']/1000:.1f} km"
                ).add_to(m)
                
                # Add circle center marker
                folium.Marker(
                    location=[circle['center_lat'], circle['center_lon']],
                    icon=folium.DivIcon(
                        html=f'<div style="background-color: {circle["color"]}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold;">{circle["name"]}</div>',
                        icon_size=(80, 20),
                        icon_anchor=(40, 10)
                    )
                ).add_to(m)
        
        # Display map
        try:
            map_data = st_folium(m, width=700, height=500, returned_objects=["last_clicked"])
            
            # Handle visit circle creation
            if map_data['last_clicked'] and visit_day and visit_day.strip():
                clicked_lat = map_data['last_clicked']['lat']
                clicked_lon = map_data['last_clicked']['lng']
                radius_meters = radius_km * 1000
                
                # Create visit circles with automatic splitting
                new_circles = st.session_state.territory_manager.create_visit_circles_with_splitting(
                    filtered_data, clicked_lat, clicked_lon, radius_meters, 
                    max_merchants_per_day, visit_day.strip(), circle_color
                )
                
                # Add executive info to each circle
                for circle in new_circles:
                    circle['executive'] = selected_executive
                
                # Add to territories list
                st.session_state.territories.extend(new_circles)
                
                # Show results
                if len(new_circles) == 1:
                    st.success(f"✅ Created visit circle '{new_circles[0]['name']}' with {new_circles[0]['merchant_count']} merchants")
                else:
                    total_merchants = sum(c['merchant_count'] for c in new_circles)
                    st.success(f"✅ Created {len(new_circles)} visit circles for {total_merchants} merchants:")
                    for circle in new_circles:
                        st.info(f"• {circle['name']}: {circle['merchant_count']} merchants")
                
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
            st.subheader("📥 Export Visit Schedule")
            if st.button("Download Visit Schedule CSV"):
                export_data = st.session_state.territory_manager.export_territories(
                    st.session_state.merchant_data, st.session_state.territories
                )
                csv_buffer = io.StringIO()
                export_data.to_csv(csv_buffer, index=False)
                
                st.download_button(
                    label="Download CSV",
                    data=csv_buffer.getvalue(),
                    file_name="visit_schedule.csv",
                    mime="text/csv"
                )
                
            # Show summary of visit circles
            st.subheader("📊 Visit Schedule Summary")
            exec_circles = [t for t in st.session_state.territories if t['executive'] == selected_executive]
            for circle in exec_circles:
                st.write(f"**{circle['name']}**: {circle['merchant_count']} merchants")
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