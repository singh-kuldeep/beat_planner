import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from territory_manager import TerritoryManager
from utils import validate_csv_format, calculate_map_center, clean_merchant_data
import io

def _display_executive_map(selected_executive, filtered_data):
    """Display map and controls for a single executive"""
    if len(filtered_data) > 0:
        st.subheader(f"Map for {selected_executive}")
        
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
        
        # Add sales person location marker first (if available)
        if st.session_state.employee_data is not None:
            emp_location = st.session_state.employee_data[
                st.session_state.employee_data['emp_id'] == selected_executive
            ]
            
            if len(emp_location) > 0:
                try:
                    emp_lat = emp_location.iloc[0]['emp_latitude']
                    emp_lon = emp_location.iloc[0]['emp_longitude']
                    
                    # Add prominent "You are here" flag marker (3x larger than circle markers)
                    folium.Marker(
                        location=[emp_lat, emp_lon],
                        popup=f"🚩 You are here<br><b>{selected_executive}</b><br>Starting Location",
                        icon=folium.DivIcon(
                            html=f'<div style="background-color: green; color: white; border-radius: 50%; width: 75px; height: 75px; text-align: center; line-height: 75px; font-weight: bold; font-size: 30px; border: 4px solid white; box-shadow: 0 4px 8px rgba(0,0,0,0.3);">🚩</div>',
                            icon_size=(75, 75),
                            icon_anchor=(37, 37)
                        ),
                        tooltip="Sales Person Starting Location"
                    ).add_to(m)
                    
                except (KeyError, IndexError):
                    try:
                        emp_lat = emp_location.iloc[0]['latitude']
                        emp_lon = emp_location.iloc[0]['longitude']
                        
                        # Add prominent "You are here" flag marker (3x larger than circle markers)
                        folium.Marker(
                            location=[emp_lat, emp_lon],
                            popup=f"🚩 You are here<br><b>{selected_executive}</b><br>Starting Location",
                            icon=folium.DivIcon(
                                html=f'<div style="background-color: green; color: white; border-radius: 50%; width: 75px; height: 75px; text-align: center; line-height: 75px; font-weight: bold; font-size: 30px; border: 4px solid white; box-shadow: 0 4px 8px rgba(0,0,0,0.3);">🚩</div>',
                                icon_size=(75, 75),
                                icon_anchor=(37, 37)
                            ),
                            tooltip="Sales Person Starting Location"
                        ).add_to(m)
                        
                    except (KeyError, IndexError):
                        pass
        
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
                visit_day_text = f" (Day {assigned_circle.get('visit_day', 'N/A')})" if 'visit_day' in assigned_circle else ""
                popup_text = f"Merchant: {row['merchant_code']}<br>Circle: {assigned_circle['name']}{visit_day_text}"
            else:
                marker_color = 'blue'
                popup_text = f"Merchant: {row['merchant_code']}<br>Status: Unassigned"
            
            folium.CircleMarker(
                location=[row['merchant_latitude'], row['merchant_longitude']],
                radius=6,
                popup=popup_text,
                color='white',
                weight=1,
                fillColor=marker_color,
                fillOpacity=0.8
            ).add_to(m)
        
        # Add visit route visualization for circles with visit days
        visit_circles = [c for c in st.session_state.territories 
                        if c['executive'] == selected_executive and 'visit_day' in c]
        
        if visit_circles:
            # Sort circles by visit day for route visualization
            visit_circles.sort(key=lambda x: x['visit_day'])
            
            # Try to get employee starting location
            start_lat, start_lon = None, None
            if st.session_state.employee_data is not None:
                emp_location = st.session_state.employee_data[
                    st.session_state.employee_data['emp_id'] == selected_executive
                ]
                
                if len(emp_location) > 0:
                    # Try different possible column names for employee location
                    try:
                        start_lat = emp_location.iloc[0]['emp_latitude']
                        start_lon = emp_location.iloc[0]['emp_longitude']
                    except KeyError:
                        try:
                            start_lat = emp_location.iloc[0]['latitude']
                            start_lon = emp_location.iloc[0]['longitude']
                        except KeyError:
                            start_lat, start_lon = None, None
            
            # If no employee location, use center of first circle as starting point
            if start_lat is None or start_lon is None:
                start_lat = visit_circles[0]['center_lat']
                start_lon = visit_circles[0]['center_lon']
                
                # Add starting point marker (using first circle location)
                folium.Marker(
                    location=[start_lat, start_lon],
                    popup=f"Route Start: {selected_executive}",
                    icon=folium.Icon(color='darkgreen', icon='play', prefix='fa')
                ).add_to(m)
            else:
                # Add employee starting point marker for route (already added above, so just note the route start)
                pass
            
            # Create route path connecting all visit circles
            route_coordinates = [[start_lat, start_lon]]
            route_coordinates.extend([[c['center_lat'], c['center_lon']] for c in visit_circles])
            
            # Add thick, visible route line
            folium.PolyLine(
                locations=route_coordinates,
                color='red',
                weight=6,
                opacity=1.0,
                popup="Visit Route - Click for details"
            ).add_to(m)
            
            # Add numbered waypoint markers for each visit circle
            for i, circle in enumerate(visit_circles):
                folium.Marker(
                    location=[circle['center_lat'], circle['center_lon']],
                    popup=f"Stop {i+1}: {circle['name']} (Day {circle['visit_day']})",
                    icon=folium.DivIcon(
                        html=f'<div style="background-color: red; color: white; border-radius: 50%; width: 25px; height: 25px; text-align: center; line-height: 25px; font-weight: bold; font-size: 12px;">{i+1}</div>',
                        icon_size=(25, 25),
                        icon_anchor=(12, 12)
                    )
                ).add_to(m)
            
            # Add route direction arrows between stops
            for i in range(len(route_coordinates) - 1):
                mid_lat = (route_coordinates[i][0] + route_coordinates[i+1][0]) / 2
                mid_lon = (route_coordinates[i][1] + route_coordinates[i+1][1]) / 2
                
                folium.Marker(
                    location=[mid_lat, mid_lon],
                    icon=folium.DivIcon(
                        html=f'<div style="color: red; font-size: 20px; font-weight: bold; text-shadow: 1px 1px 1px white;">→</div>',
                        icon_size=(25, 25),
                        icon_anchor=(12, 12)
                    )
                ).add_to(m)

        # Add only circles with visit days assigned (hide circles without visit days)
        for i, circle in enumerate(st.session_state.territories):
            if circle['executive'] == selected_executive and 'visit_day' in circle:
                # Add the circle
                # Create popup content with visit day info
                visit_day_display = f"<br><b>Visit Day:</b> {circle.get('visit_day', 'Not assigned')}" if 'visit_day' in circle else ""
                popup_content = f"<b>Circle:</b> {circle['name']}{visit_day_display}<br><b>Merchants:</b> {circle['merchant_count']}<br><b>Radius:</b> {circle['radius']/1000:.1f} km"
                
                # Style for circles with visit days (only these are shown now)
                circle_opacity = 0.6
                circle_weight = 4
                
                folium.Circle(
                    location=[circle['center_lat'], circle['center_lon']],
                    radius=circle['radius'],
                    color=circle['color'],
                    weight=circle_weight,
                    fillOpacity=circle_opacity,
                    popup=popup_content
                ).add_to(m)
                
                # Add draggable center marker
                folium.Marker(
                    location=[circle['center_lat'], circle['center_lon']],
                    draggable=True,
                    tooltip=f"Drag to move {circle['name']}",
                    popup=f"<b>Drag me to move:</b> {circle['name']}",
                    icon=folium.Icon(color='red', icon='move', prefix='fa')
                ).add_to(m)
                
                # Add circle name label with visit day (all shown circles have visit days)
                label_text = f"{circle['name']} (Day {circle['visit_day']})"
                
                folium.Marker(
                    location=[circle['center_lat'], circle['center_lon']],
                    icon=folium.DivIcon(
                        html=f'<div style="background-color: {circle["color"]}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; margin-top: 25px;">{label_text}</div>',
                        icon_size=(100, 20),
                        icon_anchor=(50, 10)
                    )
                ).add_to(m)
        
        # Display map and handle interactions
        try:
            map_data = st_folium(m, width=700, height=500, returned_objects=["last_clicked", "all_drawings", "markers"])
            
            # Show manual reassignment interface for existing circles
            exec_circles = [t for t in st.session_state.territories if t.get('executive') == selected_executive]
            if exec_circles:
                st.subheader("🔄 Manual Reassignment")
                st.info("If you've dragged circles around, click 'Reassign All' to update merchant assignments")
                
                if st.button("🔄 Reassign All Circles", type="primary", key=f"reassign_all_{selected_executive}"):
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
                        st.write(f"**{circle['name']}** - {circle['merchant_count']} merchants")
                    with col2:
                        if st.button(f"Reassign", key=f"reassign_individual_{selected_executive}_{i}"):
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
            
            # Handle map clicks for new circle creation
            if map_data['last_clicked']:
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
                
                # No manual circle creation - only auto-recommendation available
        
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
            if st.button("Download Visit Schedule CSV", key=f"export_{selected_executive}"):
                export_data = st.session_state.territory_manager.export_territories(
                    st.session_state.merchant_data, st.session_state.territories
                )
                csv_buffer = io.StringIO()
                export_data.to_csv(csv_buffer, index=False)
                
                st.download_button(
                    label="Download CSV",
                    data=csv_buffer.getvalue(),
                    file_name=f"visit_schedule_{selected_executive}.csv",
                    mime="text/csv",
                    key=f"download_{selected_executive}"
                )
                

    else:
        st.warning(f"No merchants found for {selected_executive}")

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
if 'employee_data' not in st.session_state:
    st.session_state.employee_data = None

st.title("🗺️ Sales Visit Planning System")

# Create sidebar for file upload
with st.sidebar:
    st.header("📂 Upload Data Files")
    
    # Merchant data upload
    st.subheader("1. Merchant Data")
    uploaded_file = st.file_uploader(
        "Choose merchant CSV file",
        type="csv",
        help="Required columns: merchant_code, merchant_latitude, merchant_longitude, emp_id",
        key="merchant_file"
    )
    
    # Employee location upload (optional)
    st.subheader("2. Employee Location (Optional)")
    st.info("Upload employee locations for optimal visit day routing")
    employee_file = st.file_uploader(
        "Choose employee CSV file",
        type="csv", 
        help="Required columns: emp_id, latitude, longitude",
        key="employee_file"
    )
    
    # Handle employee file upload
    if employee_file is not None:
        try:
            emp_df = pd.read_csv(employee_file)
            required_emp_columns = ['emp_id', 'latitude', 'longitude']
            
            if all(col in emp_df.columns for col in required_emp_columns):
                # Rename columns to match internal format
                emp_df_normalized = emp_df.copy()
                emp_df_normalized = emp_df_normalized.rename(columns={
                    'latitude': 'emp_latitude',
                    'longitude': 'emp_longitude'
                })
                st.session_state.employee_data = emp_df_normalized
                st.success(f"✅ Loaded {len(emp_df)} employee locations")
            else:
                st.error(f"❌ Employee file must contain: {', '.join(required_emp_columns)}")
        except Exception as e:
            st.error(f"Error reading employee file: {str(e)}")
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            
            # Try cleaning the data first if validation fails
            validation_result = validate_csv_format(df)
            
            if not validation_result['valid']:
                if 'null_info' in validation_result or 'Null values found' in validation_result.get('error', ''):
                    st.warning("⚠️ Found null values in data. Attempting to clean...")
                    
                    # Clean the data
                    cleaned_df, cleaning_report = clean_merchant_data(df)
                    
                    # Show cleaning results
                    if cleaning_report['removed_count'] > 0:
                        st.info(f"""
                        **Data Cleaning Results:**
                        - Original records: {cleaning_report['original_count']:,}
                        - Records removed: {cleaning_report['removed_count']:,} ({cleaning_report['removal_percentage']:.1f}%)
                        - Final records: {cleaning_report['final_count']:,}
                        """)
                    
                    # Validate cleaned data
                    cleaned_validation = validate_csv_format(cleaned_df)
                    if cleaned_validation['valid']:
                        st.session_state.merchant_data = cleaned_df
                        st.success(f"✅ Loaded {len(cleaned_df)} merchants (after cleaning)")
                        validation_result = cleaned_validation  # Update validation result
                    else:
                        st.error(f"❌ Data cleaning failed: {cleaned_validation['error']}")
                else:
                    st.error(f"❌ {validation_result['error']}")
            else:
                st.session_state.merchant_data = df
                st.success(f"✅ Loaded {len(df)} merchants")
            
            if validation_result['valid']:
                
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
                                'merchant_count': len(merchants_in_circle),
                                'executive': row.get('emp_id', 'Unknown')
                            })
                    
                    if existing_circles:
                        st.session_state.territories = existing_circles
                        st.info(f"📍 Found {len(existing_circles)} existing visit circles in your data")
                
                # Get unique sales executives for selection
                sales_executives = df['emp_id'].unique().tolist()
                selected_executives = st.multiselect(
                    "Select Sales Executives:",
                    options=sales_executives,
                    default=sales_executives[:1] if sales_executives else []
                )
                
                # Auto-recommendation section
                st.subheader("🤖 Auto Recommend Circles")
                st.info("Automatically create optimal visit circles with integer names (1, 2, 3, etc.)")
                
                if selected_executives:
                    # Option to select one or multiple executives
                    auto_mode = st.radio(
                        "Auto-recommendation mode:",
                        ["Single Executive", "All Selected Executives"],
                        horizontal=True,
                        key="auto_mode"
                    )
                    
                    if auto_mode == "Single Executive":
                        auto_executive = st.selectbox("Executive for Auto-Recommendation:", options=selected_executives, key="auto_exec")
                        auto_executives_list = [auto_executive]
                    else:
                        auto_executives_list = selected_executives
                        st.write(f"**Will generate for:** {', '.join(auto_executives_list)}")
                    
                    auto_col1, auto_col2 = st.columns(2)
                    
                    with auto_col1:
                        auto_radius_km = st.slider("Auto Circle Radius (km):", 0.5, 30.0, 15.0, 0.5, key="auto_radius")
                        auto_max_merchants = st.number_input("Max merchants per auto circle:", min_value=1, max_value=50, value=15, key="auto_max")
                    
                    with auto_col2:
                        st.info("Circle names will be integers: 1, 2, 3, etc.")
                        if auto_mode == "Single Executive":
                            auto_color = st.color_picker("Auto Circle Color:", "#00FF00", key="auto_color")
                        else:
                            st.info("Colors will be auto-assigned per executive")
                    
                    if st.button("🤖 Generate Auto Recommendations", type="primary"):
                        total_circles_created = 0
                        results = []
                        
                        # Color palette for multiple executives
                        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57", "#FF9FF3", "#54A0FF", "#5F27CD"]
                        
                        for idx, exec_name in enumerate(auto_executives_list):
                            auto_filtered_data = df[df['emp_id'] == exec_name]
                            
                            if len(auto_filtered_data) > 0:
                                # Get merchants not already assigned to any circle for this executive
                                assigned_merchants = set()
                                for territory in st.session_state.territories:
                                    if territory.get('executive') == exec_name:
                                        assigned_merchants.update(territory['merchants'])
                                
                                unassigned_data = auto_filtered_data[
                                    ~auto_filtered_data['merchant_code'].isin(assigned_merchants)
                                ]
                                
                                if len(unassigned_data) > 0:
                                    # Use different color for each executive if multiple mode
                                    if auto_mode == "All Selected Executives":
                                        exec_color = colors[idx % len(colors)]
                                    else:
                                        exec_color = auto_color
                                    
                                    auto_circles = st.session_state.territory_manager.create_auto_recommended_circles(
                                        unassigned_data, 
                                        auto_radius_km * 1000, 
                                        auto_max_merchants, 
                                        "", 
                                        exec_color,
                                        exec_name
                                    )
                                    
                                    st.session_state.territories.extend(auto_circles)
                                    total_circles_created += len(auto_circles)
                                    results.append(f"✅ {exec_name}: {len(auto_circles)} circles ({len(unassigned_data)} merchants)")
                                else:
                                    results.append(f"⚠️ {exec_name}: All merchants already assigned")
                            else:
                                results.append(f"❌ {exec_name}: No merchant data found")
                        
                        # Display results
                        if total_circles_created > 0:
                            st.success(f"🎉 Created {total_circles_created} total auto-recommended circles!")
                            for result in results:
                                st.write(result)
                            st.rerun()
                        else:
                            st.warning("No new circles were created")
                            for result in results:
                                st.write(result)
                

                # Visit Day Assignment Section
                st.subheader("📅 Visit Day Assignment")
                st.info("Assign visit days to top circles based on merchant count with optimal routing")
                
                # Get all circles across all selected executives
                all_circles = []
                for exec_name in selected_executives:
                    exec_circles = [t for t in st.session_state.territories if t.get('executive') == exec_name]
                    all_circles.extend([(circle, exec_name) for circle in exec_circles])
                
                if all_circles:
                    visit_col1, visit_col2 = st.columns(2)
                    
                    with visit_col1:
                        top_circles_count = st.number_input(
                            "Number of top circles to assign visit days:",
                            min_value=1,
                            max_value=len(all_circles),
                            value=min(9, len(all_circles)),
                            help="Select how many circles (by merchant count) should get visit days"
                        )
                    
                    with visit_col2:
                        visit_day_mode = st.radio(
                            "Assignment mode:",
                            ["Per Executive", "Global Ranking"],
                            help="Per Executive: Top X circles per executive\nGlobal: Top X circles across all executives"
                        )
                    
                    if st.button("🗓️ Assign Visit Days", type="primary"):
                        try:
                            # Use territory manager to assign visit days
                            updated_territories = st.session_state.territory_manager.assign_visit_days(
                                st.session_state.territories,
                                st.session_state.employee_data,
                                top_circles_count,
                                visit_day_mode,
                                selected_executives
                            )
                            
                            st.session_state.territories = updated_territories
                            
                            # Show results
                            assigned_circles = [t for t in updated_territories if 'visit_day' in t]
                            total_circles = len([t for t in updated_territories if t.get('executive') in selected_executives])
                            
                            if assigned_circles:
                                st.success(f"✅ Assigned visit days to {len(assigned_circles)} top circles out of {total_circles} total circles!")
                                st.info(f"📊 {total_circles - len(assigned_circles)} circles did not receive visit days (only top {top_circles_count} circles get visit days)")
                                
                                # Show visit day assignments by executive
                                for exec_name in selected_executives:
                                    exec_assigned = [t for t in assigned_circles if t.get('executive') == exec_name]
                                    exec_total = len([t for t in updated_territories if t.get('executive') == exec_name])
                                    
                                    if exec_assigned:
                                        st.write(f"**{exec_name} Visit Schedule ({len(exec_assigned)}/{exec_total} circles):**")
                                        for circle in sorted(exec_assigned, key=lambda x: x.get('visit_day', 999)):
                                            st.write(f"  📅 Day {circle.get('visit_day', 'N/A')}: Circle {circle['name']} ({circle['merchant_count']} merchants)")
                                    else:
                                        st.write(f"**{exec_name}**: No circles in top {top_circles_count} (has {exec_total} total circles)")
                                
                                st.rerun()
                            else:
                                st.warning("No circles were assigned visit days")
                                
                        except Exception as e:
                            st.error(f"Error assigning visit days: {str(e)}")
                else:
                    st.info("Create some circles first to assign visit days")
                

                
            else:
                st.error(f"❌ {validation_result['error']}")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Main content
if st.session_state.merchant_data is not None and 'selected_executives' in locals() and selected_executives:
    # Create tabs for each selected executive
    if len(selected_executives) == 1:
        # Single executive - no tabs needed
        selected_executive = selected_executives[0]
        filtered_data = st.session_state.merchant_data[
            st.session_state.merchant_data['emp_id'] == selected_executive
        ]
        
        _display_executive_map(selected_executive, filtered_data)
    else:
        # Multiple executives - create tabs
        tabs = st.tabs([f"{exec_name}" for exec_name in selected_executives])
        
        for i, executive in enumerate(selected_executives):
            with tabs[i]:
                filtered_data = st.session_state.merchant_data[
                    st.session_state.merchant_data['emp_id'] == executive
                ]
                if len(filtered_data) > 0:
                    _display_executive_map(executive, filtered_data)
                else:
                    st.warning(f"No merchant data found for {executive}")

else:
    st.info("Please upload a CSV file to get started")
    
    # Show expected format
    st.subheader("Expected CSV Format")
    sample_data = pd.DataFrame({
        'merchant_code': ['M001', 'M002', 'M003'],
        'merchant_latitude': [28.6139, 28.7041, 28.5355],
        'merchant_longitude': [77.2090, 77.1025, 77.3910],
        'emp_id': ['SE001', 'SE002', 'SE001']
    })
    st.dataframe(sample_data)