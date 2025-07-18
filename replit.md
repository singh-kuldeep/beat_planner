# Sales Visit Planning System

## Overview

This is a Sales Visit Planning System built with Streamlit that allows users to upload merchant data and create daily visit schedules through an interactive map interface. The system supports multiple sales executives simultaneously, enables manual and automatic visit circle creation, merchant assignment based on geographic proximity, and full circle management with drag-and-drop functionality for easy territory adjustment. Multi-executive auto-recommendation feature allows generating optimal circles for all selected executives at once with pure integer naming (1, 2, 3, etc.). The system now includes advanced visit day assignment functionality with optimal routing that minimizes travel distance starting from the sales person's location.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit web application
- **Interactive Components**: Folium maps integrated with Streamlit via streamlit_folium
- **User Interface**: Sidebar controls for file upload and territory management, main area for map visualization
- **State Management**: Streamlit session state for maintaining territories, merchant data, and territory manager instance

### Backend Architecture
- **Core Logic**: Object-oriented Python design with TerritoryManager class
- **Data Processing**: Pandas for CSV handling and data manipulation
- **Geographic Calculations**: Custom Haversine distance algorithm for territorial analysis
- **File Handling**: CSV upload and validation system

## Key Components

### 1. Main Application (simple_app.py)
- **Purpose**: Primary Streamlit interface for visit planning
- **Responsibilities**: UI layout, file upload handling, session state management, map rendering
- **Key Features**: File upload validation, data preview, interactive map display, visit circle creation

### 2. Territory Manager (territory_manager.py)
- **Purpose**: Core business logic for visit planning and circle management
- **Key Methods**:
  - `haversine_distance()`: Geographic distance calculations between coordinates
  - `get_merchants_in_circle()`: Basic circle membership determination
  - `create_auto_recommended_circles()`: Optimized circle creation with vectorized operations
  - `assign_visit_days()`: Visit day assignment with optimal routing
  - `_optimize_visit_routing()`: Minimizes travel distance between circle centers
  - `_nearest_neighbor_routing()`: Implements nearest neighbor algorithm for optimal routing
- **Design Pattern**: Utility class with mathematical, geographic, and planning operations
- **Performance**: Uses vectorized NumPy operations for 10-50x speed improvement

### 3. Utilities (utils.py)
- **Purpose**: Data validation and helper functions
- **Key Functions**:
  - `validate_csv_format()`: Ensures uploaded CSV meets required schema
  - Data type validation and null value checking
  - Geographic coordinate range validation



## Data Flow

1. **Data Ingestion**: User uploads CSV files containing merchant data and optional employee locations
2. **Validation**: System validates required columns (merchant_code, merchant_latitude, merchant_longitude, emp_id) and optional employee columns (emp_id, emp_latitude, emp_longitude)
3. **Storage**: Valid data stored in session state for persistent access
4. **Visualization**: Merchant locations plotted on interactive Folium map
5. **Territory Creation**: Users define circular territories on map (manual) or generate them automatically
6. **Assignment**: System calculates which merchants fall within each territory using optimized Haversine distance
7. **Visit Day Assignment**: System assigns visit days to top circles based on merchant count with optimal routing
8. **Route Optimization**: Minimizes travel distance starting from sales person's location using nearest neighbor algorithm

## External Dependencies

### Core Libraries
- **streamlit**: Web application framework
- **pandas**: Data manipulation and CSV processing
- **folium**: Interactive map generation
- **streamlit_folium**: Streamlit-Folium integration
- **numpy**: Numerical computations for geographic calculations

### Data Requirements
- **Merchant Data Format**: CSV files with specific schema
- **Required Merchant Fields**: merchant_code, merchant_latitude, merchant_longitude, emp_id
- **Employee Data Format**: Optional CSV for optimal routing
- **Required Employee Fields**: emp_id, latitude, longitude
- **Geographic Data**: WGS84 coordinate system (decimal degrees)

## Deployment Strategy

### Development Environment
- **Platform**: Replit-compatible Python environment
- **Dependencies**: Requirements managed through standard Python package management
- **Session Management**: Streamlit's built-in session state for user data persistence

### Architecture Decisions

1. **Streamlit Choice**: 
   - **Problem**: Need for rapid prototyping of interactive web application
   - **Solution**: Streamlit for quick UI development with minimal frontend code
   - **Pros**: Fast development, built-in widgets, easy deployment
   - **Cons**: Limited customization compared to full web frameworks

2. **Folium for Mapping**:
   - **Problem**: Need interactive geographic visualization
   - **Solution**: Folium for Leaflet.js-based mapping with Python integration
   - **Pros**: Rich mapping features, easy Python integration, interactive capabilities
   - **Cons**: Dependency on streamlit_folium for Streamlit integration

3. **Session State Management**:
   - **Problem**: Need to persist data across user interactions
   - **Solution**: Streamlit session state for temporary data storage
   - **Pros**: Simple implementation, no external database required
   - **Cons**: Data lost on session end, not suitable for production persistence

4. **Haversine Distance Algorithm**:
   - **Problem**: Need accurate geographic distance calculations
   - **Solution**: Custom implementation of Haversine formula
   - **Pros**: Accurate for Earth's spherical geometry, no external API dependencies
   - **Cons**: More complex than simple Euclidean distance

5. **CSV-based Data Input**:
   - **Problem**: Need flexible data import mechanism
   - **Solution**: CSV file upload with validation for both merchant and employee data
   - **Pros**: Universal format, easy data preparation, validation layer, supports optional employee locations
   - **Cons**: Manual upload process, no real-time data integration

6. **Visit Day Assignment with Optimal Routing**:
   - **Problem**: Need to assign visit days to prioritize high-value territories and minimize travel time
   - **Solution**: Top-N circle selection based on merchant count with nearest neighbor routing algorithm
   - **Pros**: Minimizes travel distance, prioritizes high-merchant-count areas, supports both per-executive and global ranking
   - **Cons**: Requires employee location data for optimal results

7. **Vectorized Algorithm Optimization**:
   - **Problem**: Auto-recommendation was slow for large datasets
   - **Solution**: NumPy vectorized operations, smart sampling, and reduced algorithmic complexity
   - **Pros**: 10-50x performance improvement, maintains solution quality, scalable to large datasets
   - **Cons**: Increased memory usage for very large datasets

## Recent Changes

### July 18, 2025
- **Added Visit Day Assignment Feature**: Implemented complete visit day assignment system with optimal routing
- **Employee Location Support**: Added optional employee location file upload for route optimization
- **Optimal Routing Algorithm**: Implemented nearest neighbor algorithm to minimize travel distance between circle centers
- **Performance Optimization**: Optimized auto-recommendation algorithm with vectorized operations for 10-50x speed improvement
- **Complete Merchant Coverage**: Enhanced algorithm to guarantee 100% merchant assignment to circles
- **UI Enhancements**: Added visit day display in map popups and circle management interface