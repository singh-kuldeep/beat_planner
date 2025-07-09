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
if 'move_mode' not in st.session_state:
    st.session_state.move_mode = False
if 'selected_circle_to_move' not in st.session_state:
    st.session_state.selected_circle_to_move = None

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
                
                # Add "All Sales Persons" option
                all_options = ["All Sales Persons"] + sales_executives
                selected_executive = st.selectbox(
                    "Sales Executive:",
                    options=all_options
                )
                
                # Visit circle creation
                if selected_executive != "All Sales Persons":
                    st.subheader("Create Visit Circle")
                    st.info("A visit circle represents the area a sales person will cover in one day")
                else:
                    st.subheader("Circle Creation")
                    st.info("ℹ️ Manual circle creation available for individual executives. Auto-recommendation for all executives available below.")
                
                if selected_executive != "All Sales Persons":
                    col1, col2 = st.columns(2)
                    with col1:
                        visit_day = st.text_input("Visit Day/Name:", placeholder="e.g., Monday, Day1, Circle_1")
                        radius_km = st.slider("Circle Radius (km):", 0.5, 30.0, 2.0, 0.5)
                    with col2:
                        circle_color = st.color_picker("Circle Color:", "#FF0000")
                        max_merchants_per_circle = st.number_input("Max merchants per circle:", min_value=1, max_value=50, value=10)
                    
                    if visit_day:
                        st.success(f"Ready! Click on map to create visit circle for {visit_day}")
                        st.info("You can adjust the circle size later using the Edit button")
                    
                    # Auto-recommendation section for individual executive
                    st.subheader("🤖 Auto Recommend Circles")
                    st.info("Automatically create optimal visit circles with alphabetical naming (A, B, C, etc.)")
                    
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        base_name = st.text_input("Base name for circles:", placeholder="Day", value="Day")
                    with col2:
                        if st.button("🎯 Auto Recommend Circles", type="primary"):
                            if base_name.strip():
                                # Get filtered data for this executive
                                exec_data = st.session_state.merchant_data[
                                    st.session_state.merchant_data['mobile_bde_id_2'] == selected_executive
                                ]
                                
                                # Get all unassigned merchants for this executive
                                unassigned_merchants = exec_data.copy()
                                
                                # Remove already assigned merchants
                                assigned_merchant_codes = set()
                                for territory in st.session_state.territories:
                                    if territory.get('executive') == selected_executive:
                                        assigned_merchant_codes.update(territory['merchants'])
                                
                                unassigned_merchants = unassigned_merchants[
                                    ~unassigned_merchants['merchant_code'].isin(assigned_merchant_codes)
                                ]
                                
                                if len(unassigned_merchants) > 0:
                                    # Create auto-recommended circles
                                    auto_circles = st.session_state.territory_manager.create_auto_recommended_circles(
                                        unassigned_merchants, radius_km * 1000, max_merchants_per_circle, 
                                        base_name.strip(), circle_color, selected_executive
                                    )
                                    
                                    # Add to territories
                                    st.session_state.territories.extend(auto_circles)
                                    
                                    st.success(f"Created {len(auto_circles)} auto-recommended circles covering {sum(c['merchant_count'] for c in auto_circles)} merchants")
                                    st.rerun()
                                else:
                                    st.warning("No unassigned merchants found for auto-recommendation")
                            else:
                                st.error("Please enter a base name for the circles")
                    
                    with col3:
                        if st.button("🗑️ Clear All", help="Clear all circles for this executive"):
                            # Remove all circles for this executive
                            st.session_state.territories = [
                                t for t in st.session_state.territories 
                                if t.get('executive') != selected_executive
                            ]
                            st.success("Cleared all circles")
                            st.rerun()
                
                else:
                    # Auto-recommendation section for ALL executives
                    st.subheader("🤖 Auto Recommend Circles for All Executives")
                    st.info("Create optimal visit circles for ALL sales executives at once")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        radius_km_all = st.slider("Circle Radius (km) for all:", 0.5, 30.0, 2.0, 0.5, key="radius_all")
                        max_merchants_all = st.number_input("Max merchants per circle for all:", min_value=1, max_value=50, value=10, key="merchants_all")
                    with col2:
                        base_name_all = st.text_input("Base name for circles:", placeholder="Day", value="Day", key="base_all")
                        
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("🎯 Auto Recommend for ALL Executives", type="primary"):
                            if base_name_all.strip():
                                # Get all unique executives
                                executives = st.session_state.merchant_data['mobile_bde_id_2'].unique()
                                total_circles_created = 0
                                total_merchants_assigned = 0
                                
                                # Color palette for different executives
                                colors = ["#FF0000", "#00FF00", "#0000FF", "#FFA500", "#800080", "#FFC0CB", "#A52A2A", "#008000"]
                                
                                for idx, executive in enumerate(executives):
                                    # Get data for this executive
                                    exec_data = st.session_state.merchant_data[
                                        st.session_state.merchant_data['mobile_bde_id_2'] == executive
                                    ]
                                    
                                    # Get unassigned merchants for this executive
                                    unassigned_merchants = exec_data.copy()
                                    
                                    # Remove already assigned merchants
                                    assigned_merchant_codes = set()
                                    for territory in st.session_state.territories:
                                        if territory.get('executive') == executive:
                                            assigned_merchant_codes.update(territory['merchants'])
                                    
                                    unassigned_merchants = unassigned_merchants[
                                        ~unassigned_merchants['merchant_code'].isin(assigned_merchant_codes)
                                    ]
                                    
                                    if len(unassigned_merchants) > 0:
                                        # Use different color for each executive
                                        exec_color = colors[idx % len(colors)]
                                        
                                        # Create auto-recommended circles for this executive
                                        auto_circles = st.session_state.territory_manager.create_auto_recommended_circles(
                                            unassigned_merchants, radius_km_all * 1000, max_merchants_all, 
                                            base_name_all.strip(), exec_color, executive
                                        )
                                        
                                        # Add to territories
                                        st.session_state.territories.extend(auto_circles)
                                        total_circles_created += len(auto_circles)
                                        total_merchants_assigned += sum(c['merchant_count'] for c in auto_circles)
                                
                                if total_circles_created > 0:
                                    st.success(f"✅ Created {total_circles_created} circles across all executives, covering {total_merchants_assigned} merchants")
                                    st.rerun()
                                else:
                                    st.warning("No unassigned merchants found for any executive")
                            else:
                                st.error("Please enter a base name for the circles")
                    
                    with col2:
                        if st.button("🗑️ Clear All Executive Circles", help="Clear all circles for ALL executives"):
                            st.session_state.territories = []
                            st.success("Cleared all circles for all executives")
                            st.rerun()
                
                # Existing circles management
                if st.session_state.territories:
                    st.subheader("Manage Existing Circles")
                    if selected_executive == "All Sales Persons":
                        exec_circles = st.session_state.territories.copy()
                        st.info("Showing all circles. Switch to individual executive to edit circles.")
                    else:
                        exec_circles = [t for t in st.session_state.territories if t.get('executive') == selected_executive]
                    
                    if exec_circles:
                        for i, circle in enumerate(exec_circles):
                            if selected_executive == "All Sales Persons":
                                # Read-only view for "All Sales Persons"
                                st.write(f"**{circle['name']}** ({circle['executive']}) - {circle['merchant_count']} merchants")
                            else:
                                # Full management view for individual executives
                                # Highlight circle being moved
                                if st.session_state.move_mode and st.session_state.selected_circle_to_move == i:
                                    st.markdown(f"<div style='background-color: #fff3cd; border: 2px solid #ffeaa7; border-radius: 5px; padding: 10px; margin: 5px 0;'>", unsafe_allow_html=True)
                                
                                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                                with col1:
                                    st.write(f"**{circle['name']}** - {circle['merchant_count']} merchants")
                                with col2:
                                    if st.button("Edit", key=f"edit_{i}"):
                                        st.session_state[f"editing_circle_{i}"] = True
                                with col3:
                                    if st.button("Move", key=f"move_{i}"):
                                        # Clear any editing states
                                        for j in range(len(exec_circles)):
                                            st.session_state[f"editing_circle_{j}"] = False
                                        st.session_state.move_mode = True
                                        st.session_state.selected_circle_to_move = i
                                        st.rerun()
                                with col4:
                                    if st.button("Copy", key=f"copy_{i}"):
                                        # Create a duplicate circle with "_Copy" suffix
                                        new_circle = circle.copy()
                                        new_circle['name'] = f"{circle['name']}_Copy"
                                        # Offset the copy slightly
                                        new_circle['center_lat'] += 0.005
                                        new_circle['center_lon'] += 0.005
                                        st.session_state.territories.append(new_circle)
                                        st.success(f"Created copy '{new_circle['name']}'")
                                        st.rerun()
                                with col5:
                                    if st.button("Delete", key=f"delete_{i}"):
                                        # Remove circle from territories
                                        original_index = st.session_state.territories.index(circle)
                                        st.session_state.territories.pop(original_index)
                                        st.success(f"Deleted circle '{circle['name']}'")
                                        st.rerun()
                                
                                if st.session_state.move_mode and st.session_state.selected_circle_to_move == i:
                                    st.markdown("</div>", unsafe_allow_html=True)
                            
                            # Edit mode for this circle (only for individual executives)
                            if selected_executive != "All Sales Persons" and st.session_state.get(f"editing_circle_{i}", False):
                                with st.expander(f"Edit {circle['name']}", expanded=True):
                                    new_name = st.text_input("New name:", value=circle['name'], key=f"name_{i}")
                                    new_color = st.color_picker("New color:", value=circle['color'], key=f"color_{i}")
                                    new_radius = st.slider("New radius (km):", 0.5, 30.0, circle['radius']/1000, 0.5, key=f"radius_{i}")
                                    
                                    col_save, col_cancel = st.columns(2)
                                    with col_save:
                                        if st.button("Save Changes", key=f"save_{i}"):
                                            # Update circle
                                            original_index = st.session_state.territories.index(circle)
                                            st.session_state.territories[original_index]['name'] = new_name
                                            st.session_state.territories[original_index]['color'] = new_color
                                            st.session_state.territories[original_index]['radius'] = new_radius * 1000
                                            
                                            # Recalculate merchants in updated circle
                                            new_merchants = st.session_state.territory_manager.get_merchants_in_circle(
                                                filtered_data, circle['center_lat'], circle['center_lon'], new_radius * 1000
                                            )
                                            st.session_state.territories[original_index]['merchants'] = new_merchants
                                            st.session_state.territories[original_index]['merchant_count'] = len(new_merchants)
                                            
                                            st.session_state[f"editing_circle_{i}"] = False
                                            st.success("Changes saved!")
                                            st.rerun()
                                    
                                    with col_cancel:
                                        if st.button("Cancel", key=f"cancel_{i}"):
                                            st.session_state[f"editing_circle_{i}"] = False
                                            st.rerun()
                    else:
                        st.info("No circles created yet for this sales executive")
                
            else:
                st.error(f"❌ {validation_result['error']}")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Main content
if st.session_state.merchant_data is not None and 'selected_executive' in locals():
    # Filter data based on selection
    if selected_executive == "All Sales Persons":
        filtered_data = st.session_state.merchant_data.copy()
        display_title = "All Sales Persons"
    else:
        filtered_data = st.session_state.merchant_data[
            st.session_state.merchant_data['mobile_bde_id_2'] == selected_executive
        ]
        display_title = selected_executive
    
    if len(filtered_data) > 0:
        st.subheader(f"Map for {display_title}")
        
        # Map instructions
        st.info("""
        **Map Controls:**
        • Red markers = Drag these to move circles, then click "Reassign" button
        • Click empty areas to create new circles
        • Blue dots = Unassigned merchants, Colored dots = Assigned merchants
        """)
        
        # Show mode indicators
        if st.session_state.move_mode and st.session_state.selected_circle_to_move is not None:
            exec_circles = [t for t in st.session_state.territories if t.get('executive') == selected_executive]
            if st.session_state.selected_circle_to_move < len(exec_circles):
                circle_name = exec_circles[st.session_state.selected_circle_to_move]['name']
                st.warning(f"🔄 MOVE MODE: Click on map to move '{circle_name}' to new location")
                if st.button("Cancel Move"):
                    st.session_state.move_mode = False
                    st.session_state.selected_circle_to_move = None
                    st.rerun()
        
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
                # For "All Sales Persons", check all circles; otherwise filter by executive
                circle_matches = (selected_executive == "All Sales Persons" or 
                                circle['executive'] == selected_executive)
                if circle_matches and row['merchant_code'] in circle['merchants']:
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
        
        # Add existing visit circles with draggable markers
        for i, circle in enumerate(st.session_state.territories):
            # Show circles for selected executive or all executives if "All Sales Persons" is selected
            show_circle = (selected_executive == "All Sales Persons" or 
                          circle['executive'] == selected_executive)
            if show_circle:
                # Add the circle
                folium.Circle(
                    location=[circle['center_lat'], circle['center_lon']],
                    radius=circle['radius'],
                    color=circle['color'],
                    weight=3,
                    fillOpacity=0.15,
                    popup=f"<b>Visit Day:</b> {circle['name']}<br><b>Merchants:</b> {circle['merchant_count']}<br><b>Radius:</b> {circle['radius']/1000:.1f} km"
                ).add_to(m)
                
                # Add draggable center marker
                folium.Marker(
                    location=[circle['center_lat'], circle['center_lon']],
                    draggable=True,
                    tooltip=f"Drag to move {circle['name']}",
                    popup=f"<b>Drag me to move:</b> {circle['name']}",
                    icon=folium.Icon(color='red', icon='move', prefix='fa')
                ).add_to(m)
                
                # Add circle name label
                folium.Marker(
                    location=[circle['center_lat'], circle['center_lon']],
                    icon=folium.DivIcon(
                        html=f'<div style="background-color: {circle["color"]}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; margin-top: 25px;">{circle["name"]}</div>',
                        icon_size=(80, 20),
                        icon_anchor=(40, 10)
                    )
                ).add_to(m)
        
        # Display map
        try:
            map_data = st_folium(m, width=700, height=500, returned_objects=["last_clicked", "all_drawings", "markers"])
            
            # Show manual reassignment interface for existing circles
            if selected_executive == "All Sales Persons":
                exec_circles = st.session_state.territories.copy()
                reassignment_note = "Note: Only reassignment is available in 'All Sales Persons' view. Switch to individual executive to create/edit circles."
            else:
                exec_circles = [t for t in st.session_state.territories if t.get('executive') == selected_executive]
                reassignment_note = ""
            
            if exec_circles:
                st.subheader("🔄 Manual Reassignment")
                if reassignment_note:
                    st.warning(reassignment_note)
                else:
                    st.info("If you've dragged circles around, click 'Reassign All' to update merchant assignments")
                
                if st.button("🔄 Reassign All Circles", type="primary"):
                    # Get current marker positions and update all circles
                    if map_data.get('markers') and len(map_data['markers']) > 0:
                        for marker_idx, marker in enumerate(map_data['markers']):
                            if marker_idx < len(exec_circles):
                                original_circle = exec_circles[marker_idx]
                                original_index = st.session_state.territories.index(original_circle)
                                
                                # Update circle position to current marker position
                                st.session_state.territories[original_index]['center_lat'] = marker['lat']
                                st.session_state.territories[original_index]['center_lon'] = marker['lng']
                                
                                # Recalculate merchants in moved circle
                                new_merchants = st.session_state.territory_manager.get_merchants_in_circle(
                                    filtered_data, marker['lat'], marker['lng'], original_circle['radius']
                                )
                                st.session_state.territories[original_index]['merchants'] = new_merchants
                                st.session_state.territories[original_index]['merchant_count'] = len(new_merchants)
                        
                        st.success("All circles have been reassigned with updated merchant assignments!")
                        st.rerun()
                    else:
                        st.warning("No marker data available. Please refresh the page and try again.")
                
                # Individual reassignment buttons
                st.write("**Or reassign individual circles:**")
                for i, circle in enumerate(exec_circles):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if selected_executive == "All Sales Persons":
                            st.write(f"**{circle['name']}** ({circle['executive']}) - {circle['merchant_count']} merchants")
                        else:
                            st.write(f"**{circle['name']}** - {circle['merchant_count']} merchants")
                    with col2:
                        if st.button(f"Reassign", key=f"reassign_individual_{i}"):
                            if map_data.get('markers') and len(map_data['markers']) > i:
                                marker = map_data['markers'][i]
                                original_index = st.session_state.territories.index(circle)
                                
                                # Update circle position to current marker position
                                st.session_state.territories[original_index]['center_lat'] = marker['lat']
                                st.session_state.territories[original_index]['center_lon'] = marker['lng']
                                
                                # Recalculate merchants in moved circle
                                new_merchants = st.session_state.territory_manager.get_merchants_in_circle(
                                    filtered_data, marker['lat'], marker['lng'], circle['radius']
                                )
                                st.session_state.territories[original_index]['merchants'] = new_merchants
                                st.session_state.territories[original_index]['merchant_count'] = len(new_merchants)
                                
                                st.success(f"Reassigned '{circle['name']}' - now has {len(new_merchants)} merchants")
                                st.rerun()
                            else:
                                st.warning("No marker data available for this circle. Please refresh the page and try again.")
            
            # Handle map clicks for new circle creation (only for individual executives)
            if map_data['last_clicked'] and selected_executive != "All Sales Persons":
                clicked_lat = map_data['last_clicked']['lat']
                clicked_lon = map_data['last_clicked']['lng']
                
                # Check if in move mode
                if st.session_state.move_mode and st.session_state.selected_circle_to_move is not None:
                    exec_circles = [t for t in st.session_state.territories if t.get('executive') == selected_executive]
                    if st.session_state.selected_circle_to_move < len(exec_circles):
                        # Move the selected circle
                        circle_to_move = exec_circles[st.session_state.selected_circle_to_move]
                        original_index = st.session_state.territories.index(circle_to_move)
                        
                        # Update circle position
                        st.session_state.territories[original_index]['center_lat'] = clicked_lat
                        st.session_state.territories[original_index]['center_lon'] = clicked_lon
                        
                        # Recalculate merchants in moved circle
                        new_merchants = st.session_state.territory_manager.get_merchants_in_circle(
                            filtered_data, clicked_lat, clicked_lon, circle_to_move['radius']
                        )
                        st.session_state.territories[original_index]['merchants'] = new_merchants
                        st.session_state.territories[original_index]['merchant_count'] = len(new_merchants)
                        
                        # Exit move mode
                        st.session_state.move_mode = False
                        st.session_state.selected_circle_to_move = None
                        
                        st.success(f"✅ Moved '{circle_to_move['name']}' to new location with {len(new_merchants)} merchants")
                        st.rerun()
                
                # Handle visit circle creation (only if not in move mode)
                elif visit_day and visit_day.strip():
                    radius_meters = radius_km * 1000
                    
                    # Get merchants in the circle
                    merchants_in_circle = st.session_state.territory_manager.get_merchants_in_circle(
                        filtered_data, clicked_lat, clicked_lon, radius_meters
                    )
                    
                    # Create a single circle (no automatic splitting)
                    new_circle = {
                        'name': visit_day.strip(),
                        'center_lat': clicked_lat,
                        'center_lon': clicked_lon,
                        'radius': radius_meters,
                        'color': circle_color,
                        'merchants': merchants_in_circle,
                        'merchant_count': len(merchants_in_circle),
                        'executive': selected_executive
                    }
                    
                    # Add to territories list
                    st.session_state.territories.append(new_circle)
                    
                    # Show results
                    st.success(f"✅ Created visit circle '{new_circle['name']}' with {new_circle['merchant_count']} merchants")
                    
                    st.rerun()
                
        except Exception as e:
            st.error(f"Map loading error: {str(e)}")
            st.info("Please refresh the page and try again")
        
        # Show statistics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Merchants", len(filtered_data))
        with col2:
            if selected_executive == "All Sales Persons":
                assigned_count = sum(len(t['merchants']) for t in st.session_state.territories)
            else:
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
            if selected_executive == "All Sales Persons":
                # Group circles by executive
                exec_dict = {}
                for circle in st.session_state.territories:
                    exec_name = circle['executive']
                    if exec_name not in exec_dict:
                        exec_dict[exec_name] = []
                    exec_dict[exec_name].append(circle)
                
                for exec_name, circles in exec_dict.items():
                    st.write(f"**{exec_name}:**")
                    for circle in circles:
                        st.write(f"  • {circle['name']}: {circle['merchant_count']} merchants")
            else:
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