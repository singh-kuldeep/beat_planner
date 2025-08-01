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
    required_columns = ['merchant_code', 'merchant_latitude', 'merchant_longitude', 'emp_id']
    
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
        df['merchant_latitude'] = pd.to_numeric(df['merchant_latitude'], errors='coerce')
        df['merchant_longitude'] = pd.to_numeric(df['merchant_longitude'], errors='coerce')
        
        # Check for conversion errors
        if df['merchant_latitude'].isnull().any() or df['merchant_longitude'].isnull().any():
            return {
                'valid': False,
                'error': "Invalid merchant_latitude or merchant_longitude values (must be numeric)"
            }
        
        # Check latitude range (-90 to 90)
        invalid_lat = df[(df['merchant_latitude'] < -90) | (df['merchant_latitude'] > 90)]
        if len(invalid_lat) > 0:
            return {
                'valid': False,
                'error': f"Invalid merchant_latitude values (must be between -90 and 90): {len(invalid_lat)} rows"
            }
        
        # Check longitude range (-180 to 180)
        invalid_lon = df[(df['merchant_longitude'] < -180) | (df['merchant_longitude'] > 180)]
        if len(invalid_lon) > 0:
            return {
                'valid': False,
                'error': f"Invalid merchant_longitude values (must be between -180 and 180): {len(invalid_lon)} rows"
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
    center_lat = df['merchant_latitude'].mean()
    center_lon = df['merchant_longitude'].mean()
    
    return center_lat, center_lon

def clean_merchant_data(df):
    """
    Clean merchant data by removing null entries and invalid coordinates
    
    Args:
        df: Raw merchant DataFrame
        
    Returns:
        tuple: (cleaned_df, cleaning_report)
    """
    original_count = len(df)
    df_clean = df.copy()
    
    # Remove leading/trailing whitespace from string columns
    string_columns = ['merchant_code', 'emp_id']
    for col in string_columns:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].astype(str).str.strip()
    
    # Ensure numeric columns are properly typed
    numeric_columns = ['merchant_latitude', 'merchant_longitude']
    for col in numeric_columns:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    
    # Remove rows with null values in critical columns
    required_columns = ['merchant_code', 'merchant_latitude', 'merchant_longitude', 'emp_id']
    df_clean = df_clean.dropna(subset=required_columns)
    
    # Remove rows with invalid coordinates
    df_clean = df_clean[
        (df_clean['merchant_latitude'].between(-90, 90)) &
        (df_clean['merchant_longitude'].between(-180, 180))
    ]
    
    # Remove duplicate merchant codes
    df_clean = df_clean.drop_duplicates(subset=['merchant_code'])
    
    final_count = len(df_clean)
    removed_count = original_count - final_count
    
    cleaning_report = {
        'original_count': original_count,
        'final_count': final_count,
        'removed_count': removed_count,
        'removal_percentage': (removed_count / original_count * 100) if original_count > 0 else 0
    }
    
    return df_clean, cleaning_report

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
