# Sales Visit Planning System

## Overview

This is a Sales Visit Planning System built with Streamlit that allows users to upload merchant data and create daily visit schedules through an interactive map interface. The system supports multiple sales executives simultaneously, enables manual and automatic visit circle creation, merchant assignment based on geographic proximity, and full circle management with drag-and-drop functionality for easy territory adjustment. Multi-executive auto-recommendation feature allows generating optimal circles for all selected executives at once with pure integer naming (1, 2, 3, etc.).

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
  - `create_visit_circles_with_splitting()`: Advanced circle creation with automatic splitting
- **Design Pattern**: Utility class with mathematical, geographic, and planning operations

### 3. Utilities (utils.py)
- **Purpose**: Data validation and helper functions
- **Key Functions**:
  - `validate_csv_format()`: Ensures uploaded CSV meets required schema
  - Data type validation and null value checking
  - Geographic coordinate range validation



## Data Flow

1. **Data Ingestion**: User uploads CSV file containing merchant data
2. **Validation**: System validates required columns (merchant_code, merchant_latitude, merchant_longitude, emp_id)
3. **Storage**: Valid data stored in session state for persistent access
4. **Visualization**: Merchant locations plotted on interactive Folium map
5. **Territory Creation**: Users define circular territories on map
6. **Assignment**: System calculates which merchants fall within each territory using Haversine distance

## External Dependencies

### Core Libraries
- **streamlit**: Web application framework
- **pandas**: Data manipulation and CSV processing
- **folium**: Interactive map generation
- **streamlit_folium**: Streamlit-Folium integration
- **numpy**: Numerical computations for geographic calculations

### Data Requirements
- **Input Format**: CSV files with specific schema
- **Required Fields**: merchant_code, merchant_latitude, merchant_longitude, emp_id
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
   - **Solution**: CSV file upload with validation
   - **Pros**: Universal format, easy data preparation, validation layer
   - **Cons**: Manual upload process, no real-time data integration