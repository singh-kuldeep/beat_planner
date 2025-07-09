import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt

class TerritoryManager:
    def __init__(self):
        pass
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees)
        Returns distance in meters
        """
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radius of earth in meters
        r = 6371000
        
        return c * r
    
    def get_merchants_in_circle(self, merchant_data, center_lat, center_lon, radius_meters):
        """
        Get list of merchant codes that fall within a circular territory
        
        Args:
            merchant_data: DataFrame with merchant information
            center_lat: Center latitude of the circle
            center_lon: Center longitude of the circle
            radius_meters: Radius of the circle in meters
            
        Returns:
            List of merchant codes within the circle
        """
        merchants_in_circle = []
        
        for idx, row in merchant_data.iterrows():
            distance = self.haversine_distance(
                center_lat, center_lon,
                row['latitude'], row['longitude']
            )
            
            if distance <= radius_meters:
                merchants_in_circle.append(row['merchant_code'])
        
        return merchants_in_circle
    
    def calculate_territory_overlap(self, territories):
        """
        Calculate which merchants are assigned to multiple territories
        
        Args:
            territories: List of territory dictionaries
            
        Returns:
            Dictionary with overlap information
        """
        merchant_assignments = {}
        
        for territory in territories:
            for merchant in territory['merchants']:
                if merchant not in merchant_assignments:
                    merchant_assignments[merchant] = []
                merchant_assignments[merchant].append(territory['name'])
        
        # Find overlaps
        overlapping_merchants = {
            merchant: territories 
            for merchant, territories in merchant_assignments.items() 
            if len(territories) > 1
        }
        
        return {
            'total_assignments': merchant_assignments,
            'overlapping_merchants': overlapping_merchants,
            'overlap_count': len(overlapping_merchants)
        }
    
    def export_territories(self, original_data, territories):
        """
        Create export DataFrame with territory assignments
        
        Args:
            original_data: Original merchant DataFrame
            territories: List of territory dictionaries
            
        Returns:
            DataFrame ready for CSV export
        """
        # Create a copy of original data
        export_df = original_data.copy()
        
        # Add territory assignment columns
        export_df['territory_name'] = 'Unassigned'
        export_df['territory_center_lat'] = None
        export_df['territory_center_lon'] = None
        export_df['territory_radius_meters'] = None
        export_df['territory_color'] = None
        
        # Assign territories (last assignment wins in case of overlap)
        for territory in territories:
            for merchant_code in territory['merchants']:
                mask = export_df['merchant_code'] == merchant_code
                export_df.loc[mask, 'territory_name'] = territory['name']
                export_df.loc[mask, 'territory_center_lat'] = territory['center_lat']
                export_df.loc[mask, 'territory_center_lon'] = territory['center_lon']
                export_df.loc[mask, 'territory_radius_meters'] = territory['radius']
                export_df.loc[mask, 'territory_color'] = territory['color']
        
        return export_df
    
    def get_territory_statistics(self, territories, merchant_data):
        """
        Generate statistics for all territories
        
        Args:
            territories: List of territory dictionaries
            merchant_data: Original merchant DataFrame
            
        Returns:
            Dictionary with various statistics
        """
        total_merchants = len(merchant_data)
        total_territories = len(territories)
        
        # Calculate assigned merchants
        assigned_merchants = set()
        for territory in territories:
            assigned_merchants.update(territory['merchants'])
        
        assigned_count = len(assigned_merchants)
        unassigned_count = total_merchants - assigned_count
        
        # Territory size distribution
        territory_sizes = [len(territory['merchants']) for territory in territories]
        
        # Calculate overlap
        overlap_info = self.calculate_territory_overlap(territories)
        
        stats = {
            'total_merchants': total_merchants,
            'total_territories': total_territories,
            'assigned_merchants': assigned_count,
            'unassigned_merchants': unassigned_count,
            'assignment_percentage': (assigned_count / total_merchants * 100) if total_merchants > 0 else 0,
            'average_territory_size': np.mean(territory_sizes) if territory_sizes else 0,
            'min_territory_size': min(territory_sizes) if territory_sizes else 0,
            'max_territory_size': max(territory_sizes) if territory_sizes else 0,
            'overlapping_merchants': overlap_info['overlap_count'],
            'overlap_details': overlap_info['overlapping_merchants']
        }
        
        return stats
    
    def validate_territory_data(self, territory):
        """
        Validate territory data structure
        
        Args:
            territory: Territory dictionary
            
        Returns:
            Dictionary with validation result
        """
        required_fields = ['name', 'center_lat', 'center_lon', 'radius', 'color', 'merchants', 'executive']
        
        for field in required_fields:
            if field not in territory:
                return {
                    'valid': False,
                    'error': f"Missing required field: {field}"
                }
        
        # Validate data types
        if not isinstance(territory['name'], str) or not territory['name'].strip():
            return {
                'valid': False,
                'error': "Territory name must be a non-empty string"
            }
        
        try:
            float(territory['center_lat'])
            float(territory['center_lon'])
            float(territory['radius'])
        except (ValueError, TypeError):
            return {
                'valid': False,
                'error': "Latitude, longitude, and radius must be numeric"
            }
        
        if not isinstance(territory['merchants'], list):
            return {
                'valid': False,
                'error': "Merchants must be a list"
            }
        
        return {'valid': True}
