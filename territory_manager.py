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
    
    def create_visit_circles_with_splitting(self, merchant_data, center_lat, center_lon, radius_meters, max_merchants_per_circle, visit_day, color):
        """
        Create visit circles and split them if they contain too many merchants
        
        Args:
            merchant_data: DataFrame with merchant information
            center_lat: Center latitude of the initial circle
            center_lon: Center longitude of the initial circle
            radius_meters: Initial radius in meters
            max_merchants_per_circle: Maximum merchants allowed per circle
            visit_day: Base name for the visit day
            color: Circle color
            
        Returns:
            List of circle dictionaries
        """
        circles = []
        
        # Get all merchants in the initial circle
        merchants_in_area = []
        for idx, row in merchant_data.iterrows():
            distance = self.haversine_distance(
                center_lat, center_lon,
                row['latitude'], row['longitude']
            )
            
            if distance <= radius_meters:
                merchants_in_area.append({
                    'merchant_code': row['merchant_code'],
                    'latitude': row['latitude'],
                    'longitude': row['longitude'],
                    'distance': distance
                })
        
        # If merchants count is within limit, create single circle
        if len(merchants_in_area) <= max_merchants_per_circle:
            merchant_codes = [m['merchant_code'] for m in merchants_in_area]
            circles.append({
                'name': visit_day,
                'center_lat': center_lat,
                'center_lon': center_lon,
                'radius': radius_meters,
                'color': color,
                'merchants': merchant_codes,
                'merchant_count': len(merchant_codes)
            })
        else:
            # Split into multiple circles
            # Sort merchants by distance from center
            merchants_in_area.sort(key=lambda x: x['distance'])
            
            circle_num = 1
            start_idx = 0
            
            while start_idx < len(merchants_in_area):
                end_idx = min(start_idx + max_merchants_per_circle, len(merchants_in_area))
                circle_merchants = merchants_in_area[start_idx:end_idx]
                
                # Calculate center for this sub-circle (average of merchant positions)
                if circle_merchants:
                    avg_lat = sum(m['latitude'] for m in circle_merchants) / len(circle_merchants)
                    avg_lon = sum(m['longitude'] for m in circle_merchants) / len(circle_merchants)
                    
                    # Calculate radius needed to include all merchants in this sub-circle
                    max_distance = max(self.haversine_distance(avg_lat, avg_lon, m['latitude'], m['longitude']) 
                                     for m in circle_merchants)
                    sub_radius = max_distance * 1.2  # Add 20% buffer
                    
                    merchant_codes = [m['merchant_code'] for m in circle_merchants]
                    circle_name = f"{visit_day}_Circle_{circle_num}" if circle_num > 1 else visit_day
                    
                    circles.append({
                        'name': circle_name,
                        'center_lat': avg_lat,
                        'center_lon': avg_lon,
                        'radius': sub_radius,
                        'color': color,
                        'merchants': merchant_codes,
                        'merchant_count': len(merchant_codes)
                    })
                    
                    circle_num += 1
                    start_idx = end_idx
        
        return circles
    
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
        Create export DataFrame with visit circle assignments
        
        Args:
            original_data: Original merchant DataFrame
            territories: List of visit circle dictionaries
            
        Returns:
            DataFrame ready for CSV export
        """
        # Create a copy of original data
        export_df = original_data.copy()
        
        # Add visit circle assignment columns
        export_df['visit_day'] = 'Unassigned'
        export_df['circle_name'] = 'Unassigned'
        export_df['circle_center_lat'] = None
        export_df['circle_center_lon'] = None
        export_df['circle_radius_meters'] = None
        export_df['circle_color'] = None
        
        # Assign visit circles (last assignment wins in case of overlap)
        for circle in territories:
            for merchant_code in circle['merchants']:
                mask = export_df['merchant_code'] == merchant_code
                export_df.loc[mask, 'visit_day'] = circle['name']
                export_df.loc[mask, 'circle_name'] = circle['name']
                export_df.loc[mask, 'circle_center_lat'] = circle['center_lat']
                export_df.loc[mask, 'circle_center_lon'] = circle['center_lon']
                export_df.loc[mask, 'circle_radius_meters'] = circle['radius']
                export_df.loc[mask, 'circle_color'] = circle['color']
        
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
    
    def create_auto_recommended_circles(self, merchant_data, radius_meters, max_merchants_per_circle, base_name, color, executive):
        """
        Create auto-recommended circles using clustering algorithm
        
        Args:
            merchant_data: DataFrame with unassigned merchant information
            radius_meters: Circle radius in meters
            max_merchants_per_circle: Maximum merchants allowed per circle
            base_name: Base name for generated circles
            color: Circle color
            executive: Executive name
            
        Returns:
            List of circle dictionaries
        """
        if len(merchant_data) == 0:
            return []
        
        circles = []
        remaining_merchants = merchant_data.copy()
        circle_count = 0
        
        # Create alphabetical sequence for naming: A, B, C, ..., Z, AA, AB, etc.
        def get_alphabetical_name(index):
            result = ""
            while index >= 0:
                result = chr(65 + (index % 26)) + result
                index = index // 26 - 1
            return result
        
        while len(remaining_merchants) > 0:
            # Find the best starting point (center of remaining merchants)
            center_lat = remaining_merchants['latitude'].mean()
            center_lon = remaining_merchants['longitude'].mean()
            
            # Alternatively, start with the merchant that has the most neighbors
            best_center_lat, best_center_lon = self._find_optimal_center(remaining_merchants, radius_meters)
            
            # Get merchants in this circle
            merchants_in_circle = self.get_merchants_in_circle(
                remaining_merchants, best_center_lat, best_center_lon, radius_meters
            )
            
            # If no merchants found, expand radius or use remaining merchants
            if len(merchants_in_circle) == 0:
                # Take the first remaining merchant as center
                first_merchant = remaining_merchants.iloc[0]
                best_center_lat = first_merchant['latitude']
                best_center_lon = first_merchant['longitude']
                merchants_in_circle = self.get_merchants_in_circle(
                    remaining_merchants, best_center_lat, best_center_lon, radius_meters
                )
            
            # If still too many merchants, split or take only max_merchants_per_circle
            if len(merchants_in_circle) > max_merchants_per_circle:
                # Take closest merchants to center
                merchant_distances = []
                for merchant_code in merchants_in_circle:
                    merchant_row = remaining_merchants[remaining_merchants['merchant_code'] == merchant_code].iloc[0]
                    distance = self.haversine_distance(
                        best_center_lat, best_center_lon,
                        merchant_row['latitude'], merchant_row['longitude']
                    )
                    merchant_distances.append((merchant_code, distance))
                
                # Sort by distance and take closest ones
                merchant_distances.sort(key=lambda x: x[1])
                merchants_in_circle = [m[0] for m in merchant_distances[:max_merchants_per_circle]]
            
            # Create circle with alphabetical naming
            alpha_suffix = get_alphabetical_name(circle_count)
            circle = {
                'name': f"{base_name}_{alpha_suffix}",
                'center_lat': best_center_lat,
                'center_lon': best_center_lon,
                'radius': radius_meters,
                'color': color,
                'merchants': merchants_in_circle,
                'merchant_count': len(merchants_in_circle),
                'executive': executive
            }
            
            circles.append(circle)
            
            # Remove assigned merchants from remaining
            remaining_merchants = remaining_merchants[
                ~remaining_merchants['merchant_code'].isin(merchants_in_circle)
            ]
            
            circle_count += 1
            
            # Safety check to prevent infinite loop
            if circle_count > 100:
                break
        
        return circles
    
    def _find_optimal_center(self, merchant_data, radius_meters):
        """
        Find optimal center point that maximizes merchant coverage
        
        Args:
            merchant_data: DataFrame with merchant locations
            radius_meters: Circle radius in meters
            
        Returns:
            Tuple of (optimal_lat, optimal_lon)
        """
        best_lat, best_lon = merchant_data['latitude'].mean(), merchant_data['longitude'].mean()
        max_merchants = 0
        
        # Try each merchant as a potential center
        for idx, row in merchant_data.iterrows():
            center_lat, center_lon = row['latitude'], row['longitude']
            
            # Count merchants within radius
            merchants_in_circle = self.get_merchants_in_circle(
                merchant_data, center_lat, center_lon, radius_meters
            )
            
            if len(merchants_in_circle) > max_merchants:
                max_merchants = len(merchants_in_circle)
                best_lat, best_lon = center_lat, center_lon
        
        return best_lat, best_lon
