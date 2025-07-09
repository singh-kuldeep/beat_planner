import pandas as pd
import numpy as np

def validate_csv_format(df):
    """
    Validate that the uploaded CSV has the required columns and format
    
    Args:
        df: pandas DataFrame to validate
        
    Returns:
        Dictionary with validation result
    """
    required_columns = ['merchant_code', 'latitude', 'longitude', 'mobile_bde_id_2']
    
    # Optional columns for existing circles
    optional_columns = ['visit_day', 'circle_name', 'circle_center_lat', 'circle_center_lon', 'circle_radius_meters', 'circle_color']
    
    # Check if all required columns exist
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return {
            'valid': False,
            'error': f"Missing required columns: {', '.join(missing_columns)}"
        }
    
    # Check for empty DataFrame
    if len(df) == 0:
        return {
            'valid': False,
            'error': "CSV file is empty"
        }
    
    # Check for null values in required columns
    null_columns = []
    for col in required_columns:
        if df[col].isnull().any():
            null_count = df[col].isnull().sum()
            null_columns.append(f"{col} ({null_count} null values)")
    
    if null_columns:
        return {
            'valid': False,
            'error': f"Null values found in: {', '.join(null_columns)}"
        }
    
    # Validate latitude and longitude ranges
    try:
        # Convert to numeric if they're strings
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        
        # Check for conversion errors
        if df['latitude'].isnull().any() or df['longitude'].isnull().any():
            return {
                'valid': False,
                'error': "Invalid latitude or longitude values (must be numeric)"
            }
        
        # Check latitude range (-90 to 90)
        invalid_lat = df[(df['latitude'] < -90) | (df['latitude'] > 90)]
        if len(invalid_lat) > 0:
            return {
                'valid': False,
                'error': f"Invalid latitude values (must be between -90 and 90): {len(invalid_lat)} rows"
            }
        
        # Check longitude range (-180 to 180)
        invalid_lon = df[(df['longitude'] < -180) | (df['longitude'] > 180)]
        if len(invalid_lon) > 0:
            return {
                'valid': False,
                'error': f"Invalid longitude values (must be between -180 and 180): {len(invalid_lon)} rows"
            }
            
    except Exception as e:
        return {
            'valid': False,
            'error': f"Error validating coordinates: {str(e)}"
        }
    
    # Check for duplicate merchant codes
    duplicate_merchants = df[df.duplicated(subset=['merchant_code'], keep=False)]
    if len(duplicate_merchants) > 0:
        return {
            'valid': False,
            'error': f"Duplicate merchant codes found: {len(duplicate_merchants)} duplicates"
        }
    
    return {'valid': True}

def calculate_map_center(df):
    """
    Calculate the center point for the map based on merchant locations
    
    Args:
        df: DataFrame with latitude and longitude columns
        
    Returns:
        Tuple of (center_latitude, center_longitude)
    """
    if len(df) == 0:
        # Default to a central location if no data
        return 40.7128, -74.0060  # New York City
    
    # Calculate the geographic center
    center_lat = df['latitude'].mean()
    center_lon = df['longitude'].mean()
    
    return center_lat, center_lon

def clean_merchant_data(df):
    """
    Clean and standardize merchant data
    
    Args:
        df: Raw merchant DataFrame
        
    Returns:
        Cleaned DataFrame
    """
    df_clean = df.copy()
    
    # Remove leading/trailing whitespace from string columns
    string_columns = ['merchant_code', 'mobile_bde_id_2']
    for col in string_columns:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].astype(str).str.strip()
    
    # Ensure numeric columns are properly typed
    numeric_columns = ['latitude', 'longitude']
    for col in numeric_columns:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    
    # Remove rows with invalid coordinates
    df_clean = df_clean.dropna(subset=['latitude', 'longitude'])
    
    return df_clean

def format_distance(distance_meters):
    """
    Format distance in meters to a human-readable string
    
    Args:
        distance_meters: Distance in meters
        
    Returns:
        Formatted distance string
    """
    if distance_meters < 1000:
        return f"{distance_meters:.0f} m"
    else:
        return f"{distance_meters/1000:.1f} km"

def get_color_palette():
    """
    Get a predefined color palette for territories
    
    Returns:
        List of hex color codes
    """
    return [
        '#FF0000',  # Red
        '#00FF00',  # Green
        '#0000FF',  # Blue
        '#FFFF00',  # Yellow
        '#FF00FF',  # Magenta
        '#00FFFF',  # Cyan
        '#FFA500',  # Orange
        '#800080',  # Purple
        '#FFC0CB',  # Pink
        '#A52A2A',  # Brown
        '#808080',  # Gray
        '#000080',  # Navy
        '#008000',  # Dark Green
        '#800000',  # Maroon
        '#808000'   # Olive
    ]

def calculate_territory_bounds(center_lat, center_lon, radius_meters):
    """
    Calculate the bounding box for a circular territory
    
    Args:
        center_lat: Center latitude
        center_lon: Center longitude
        radius_meters: Radius in meters
        
    Returns:
        Dictionary with north, south, east, west bounds
    """
    # Rough conversion from meters to degrees (approximate)
    # 1 degree latitude ≈ 111,000 meters
    # 1 degree longitude ≈ 111,000 * cos(latitude) meters
    
    lat_delta = radius_meters / 111000
    lon_delta = radius_meters / (111000 * np.cos(np.radians(center_lat)))
    
    return {
        'north': center_lat + lat_delta,
        'south': center_lat - lat_delta,
        'east': center_lon + lon_delta,
        'west': center_lon - lon_delta
    }

def export_territory_summary(territories):
    """
    Create a summary DataFrame of all territories
    
    Args:
        territories: List of territory dictionaries
        
    Returns:
        DataFrame with territory summary
    """
    summary_data = []
    
    for territory in territories:
        summary_data.append({
            'territory_name': territory['name'],
            'executive': territory['executive'],
            'center_latitude': territory['center_lat'],
            'center_longitude': territory['center_lon'],
            'radius_meters': territory['radius'],
            'merchant_count': len(territory['merchants']),
            'color': territory['color']
        })
    
    return pd.DataFrame(summary_data)
