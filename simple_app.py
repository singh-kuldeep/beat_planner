import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from territory_manager import TerritoryManager
from utils import validate_csv_format, calculate_map_center
from ai_optimizer import AITerritoryOptimizer
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
                location=[row['merchant_latitude'], row['merchant_longitude']],
                radius=6,
                popup=popup_text,
                color='white',
                weight=1,
                fillColor=marker_color,
                fillOpacity=0.8
            ).add_to(m)
        
        # Add existing visit circles with draggable markers
        for i, circle in enumerate(st.session_state.territories):
            if circle['executive'] == selected_executive:
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
                
                # Handle visit circle creation (only if not in move mode)
                else:
                    # Check if manual circle creation parameters are set
                    if hasattr(st.session_state, 'visit_day') and hasattr(st.session_state, 'target_executive') and hasattr(st.session_state, 'radius_km') and hasattr(st.session_state, 'circle_color'):
                        if (st.session_state.visit_day and st.session_state.target_executive == selected_executive and 
                            st.session_state.visit_day.strip()):
                            
                            radius_meters = st.session_state.radius_km * 1000
                            
                            # Get merchants in the circle
                            merchants_in_circle = st.session_state.territory_manager.get_merchants_in_circle(
                                filtered_data, clicked_lat, clicked_lon, radius_meters
                            )
                            
                            # Create a single circle (no automatic splitting)
                            new_circle = {
                                'name': st.session_state.visit_day.strip(),
                                'center_lat': clicked_lat,
                                'center_lon': clicked_lon,
                                'radius': radius_meters,
                                'color': st.session_state.circle_color,
                                'merchants': merchants_in_circle,
                                'merchant_count': len(merchants_in_circle),
                                'executive': selected_executive
                            }
                            
                            # Add to territories list
                            st.session_state.territories.append(new_circle)
                            
                            # Clear the creation parameters
                            del st.session_state.visit_day
                            del st.session_state.target_executive
                            del st.session_state.radius_km
                            del st.session_state.circle_color
                            
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
                
            # Show summary of visit circles
            st.subheader("📊 Visit Schedule Summary")
            exec_circles = [t for t in st.session_state.territories if t['executive'] == selected_executive]
            for circle in exec_circles:
                st.write(f"**{circle['name']}**: {circle['merchant_count']} merchants")
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

if 'ai_optimizer' not in st.session_state:
    st.session_state.ai_optimizer = AITerritoryOptimizer()
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
        help="Required columns: merchant_code, merchant_latitude, merchant_longitude, emp_id"
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
                
                # Visit circle creation (manual)
                if selected_executives:
                    st.subheader("Create Visit Circle (Manual)")
                    st.info("A visit circle represents the area a sales person will cover in one day")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        visit_day = st.text_input("Visit Day/Name:", placeholder="e.g., Monday, Day1, Circle_1")
                        radius_km = st.slider("Circle Radius (km):", 0.5, 30.0, 10.0, 0.5)
                        target_executive = st.selectbox("Assign to Executive:", options=selected_executives)
                    with col2:
                        circle_color = st.color_picker("Circle Color:", "#FF0000")
                        max_merchants_per_circle = st.number_input("Max merchants per circle:", min_value=1, max_value=50, value=11)
                    
                    if visit_day and target_executive:
                        # Store parameters in session state for map click handling
                        st.session_state.visit_day = visit_day
                        st.session_state.target_executive = target_executive
                        st.session_state.radius_km = radius_km
                        st.session_state.circle_color = circle_color
                        
                        st.success(f"Ready! Click on the {target_executive} map to create '{visit_day}' circle")
                        st.info("Circle will be created when you click on the map in the executive's tab below")
                
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
                        auto_radius_km = st.slider("Auto Circle Radius (km):", 0.5, 30.0, 10.0, 0.5, key="auto_radius")
                        auto_max_merchants = st.number_input("Max merchants per auto circle:", min_value=1, max_value=50, value=11, key="auto_max")
                    
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
                
                # Circle management for selected executives
                if selected_executives:
                    st.subheader("🔧 Circle Management")
                    
                    for exec_name in selected_executives:
                        st.write(f"**Circles for {exec_name}:**")
                        exec_circles = [t for t in st.session_state.territories if t.get('executive') == exec_name]
                        
                        # Sort circles alphabetically by name
                        exec_circles.sort(key=lambda x: x['name'])
                        
                        if exec_circles:
                            for i, circle in enumerate(exec_circles):
                                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                                
                                with col1:
                                    st.write(f"{circle['name']} - {circle['merchant_count']} merchants")
                                
                                with col2:
                                    if st.button("Edit", key=f"edit_{exec_name}_{i}"):
                                        st.session_state[f"editing_circle_{exec_name}_{i}"] = True
                                        st.rerun()
                                
                                with col3:
                                    if st.button("Move", key=f"move_{exec_name}_{i}"):
                                        st.session_state.move_mode = True
                                        st.session_state.selected_circle_to_move = i
                                        st.rerun()
                                
                                with col4:
                                    if st.button("Delete", key=f"delete_{exec_name}_{i}"):
                                        del st.session_state.territories[st.session_state.territories.index(circle)]
                                        st.success(f"Deleted circle '{circle['name']}'")
                                        st.rerun()
                                
                                # Edit interface
                                if st.session_state.get(f"editing_circle_{exec_name}_{i}", False):
                                    st.write("**Edit Circle:**")
                                    
                                    edit_col1, edit_col2 = st.columns(2)
                                    with edit_col1:
                                        new_name = st.text_input("Name:", value=circle['name'], key=f"edit_name_{exec_name}_{i}")
                                        new_radius_km = st.slider("Radius (km):", 0.5, 30.0, circle['radius']/1000, 0.5, key=f"edit_radius_{exec_name}_{i}")
                                    with edit_col2:
                                        new_color = st.color_picker("Color:", value=circle['color'], key=f"edit_color_{exec_name}_{i}")
                                    
                                    col_save, col_cancel = st.columns(2)
                                    with col_save:
                                        if st.button("Save Changes", key=f"save_{exec_name}_{i}"):
                                            # Update circle
                                            original_index = st.session_state.territories.index(circle)
                                            st.session_state.territories[original_index]['name'] = new_name
                                            st.session_state.territories[original_index]['color'] = new_color
                                            st.session_state.territories[original_index]['radius'] = new_radius_km * 1000
                                            
                                            # Recalculate merchants in updated circle
                                            filtered_data = df[df['emp_id'] == exec_name]
                                            new_merchants = st.session_state.territory_manager.get_merchants_in_circle(
                                                filtered_data, circle['center_lat'], circle['center_lon'], new_radius_km * 1000
                                            )
                                            st.session_state.territories[original_index]['merchants'] = new_merchants
                                            st.session_state.territories[original_index]['merchant_count'] = len(new_merchants)
                                            
                                            st.session_state[f"editing_circle_{exec_name}_{i}"] = False
                                            st.success("Changes saved!")
                                            st.rerun()
                                    
                                    with col_cancel:
                                        if st.button("Cancel", key=f"cancel_{exec_name}_{i}"):
                                            st.session_state[f"editing_circle_{exec_name}_{i}"] = False
                                            st.rerun()
                        else:
                            st.info(f"No circles created yet for {exec_name}")
                
                # AI-powered optimization section
                if st.session_state.territories:
                    st.subheader("🧠 AI Territory Optimization")
                    
                    if st.session_state.ai_optimizer.is_available():
                        st.info("AI-powered analysis to optimize your territory setup for maximum efficiency")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("📊 Analyze Current Setup", type="secondary"):
                                with st.spinner("AI analyzing territories..."):
                                    analysis = st.session_state.ai_optimizer.analyze_territory_efficiency(
                                        st.session_state.territories, 
                                        df
                                    )
                                    st.session_state.ai_analysis = analysis
                                st.rerun()
                        
                        with col2:
                            if st.button("💡 Get Optimization Suggestions", type="primary"):
                                with st.spinner("AI generating optimization suggestions..."):
                                    suggestions = st.session_state.ai_optimizer.get_optimization_suggestions(
                                        st.session_state.territories, 
                                        df
                                    )
                                    st.session_state.ai_suggestions = suggestions
                                st.rerun()
                        
                        # Display AI analysis results
                        if 'ai_analysis' in st.session_state:
                            analysis = st.session_state.ai_analysis
                            if "error" not in analysis:
                                st.subheader("📊 Territory Analysis")
                                
                                # Show efficiency scores
                                score_col1, score_col2, score_col3 = st.columns(3)
                                with score_col1:
                                    efficiency = analysis.get('efficiency_score', 0)
                                    st.metric("Efficiency Score", f"{efficiency}/100")
                                with score_col2:
                                    balance = analysis.get('balance_score', 0)
                                    st.metric("Balance Score", f"{balance}/100")
                                with score_col3:
                                    coverage = analysis.get('coverage_score', 0)
                                    st.metric("Coverage Score", f"{coverage}/100")
                                
                                # Show key insights
                                if 'key_insights' in analysis:
                                    st.write("**Key Insights:**")
                                    for insight in analysis['key_insights']:
                                        st.write(f"• {insight}")
                                
                                # Show strengths and weaknesses
                                col1, col2 = st.columns(2)
                                with col1:
                                    if 'strengths' in analysis:
                                        st.success("**Strengths:**")
                                        for strength in analysis['strengths']:
                                            st.write(f"✓ {strength}")
                                
                                with col2:
                                    if 'weaknesses' in analysis:
                                        st.warning("**Areas for Improvement:**")
                                        for weakness in analysis['weaknesses']:
                                            st.write(f"⚠️ {weakness}")
                            else:
                                st.error(f"Analysis failed: {analysis['error']}")
                        
                        # Display AI suggestions
                        if 'ai_suggestions' in st.session_state:
                            suggestions = st.session_state.ai_suggestions
                            if "error" not in suggestions:
                                st.subheader("💡 AI Optimization Suggestions")
                                
                                if 'overall_strategy' in suggestions:
                                    st.info(f"**Strategy:** {suggestions['overall_strategy']}")
                                
                                # Display suggestions by priority
                                if 'suggestions' in suggestions:
                                    for suggestion in suggestions['suggestions']:
                                        priority = suggestion.get('priority', 'medium')
                                        priority_color = {
                                            'high': '🔴',
                                            'medium': '🟡', 
                                            'low': '🟢'
                                        }.get(priority, '🟡')
                                        
                                        with st.expander(f"{priority_color} {suggestion.get('title', 'Suggestion')} ({priority} priority)"):
                                            st.write(f"**Description:** {suggestion.get('description', '')}")
                                            st.write(f"**Action:** {suggestion.get('action', '')}")
                                            if 'expected_improvement' in suggestion:
                                                st.write(f"**Expected Benefit:** {suggestion['expected_improvement']}")
                                
                                if 'implementation_order' in suggestions:
                                    st.info(f"**Implementation Order:** {suggestions['implementation_order']}")
                            else:
                                st.error(f"Suggestions failed: {suggestions['error']}")
                    
                    else:
                        st.warning("🔑 AI optimization requires an OpenAI API key")
                        st.info("Provide your OpenAI API key to unlock intelligent territory optimization suggestions")
                        if st.button("Set API Key"):
                            st.info("Please set the OPENAI_API_KEY environment variable to enable AI features")
                
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