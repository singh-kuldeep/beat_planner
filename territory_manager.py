import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import haversine_distances

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
                row['merchant_latitude'], row['merchant_longitude']
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
                row['merchant_latitude'], row['merchant_longitude']
            )
            
            if distance <= radius_meters:
                merchants_in_area.append({
                    'merchant_code': row['merchant_code'],
                    'merchant_latitude': row['merchant_latitude'],
                    'merchant_longitude': row['merchant_longitude'],
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
                    avg_lat = sum(m['merchant_latitude'] for m in circle_merchants) / len(circle_merchants)
                    avg_lon = sum(m['merchant_longitude'] for m in circle_merchants) / len(circle_merchants)
                    
                    # Calculate radius needed to include all merchants in this sub-circle
                    max_distance = max(self.haversine_distance(avg_lat, avg_lon, m['merchant_latitude'], m['merchant_longitude']) 
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
        
        # Sort territories alphabetically by name for consistent export order
        sorted_territories = sorted(territories, key=lambda x: x['name'])
        
        # Assign visit circles (last assignment wins in case of overlap)
        for circle in sorted_territories:
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
        Create auto-recommended circles using optimized clustering algorithm
        
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
        
        # Use optimized algorithm for better performance
        return self._create_circles_optimized(merchant_data, radius_meters, max_merchants_per_circle, color, executive)
    
    def _create_circles_optimized(self, merchant_data, radius_meters, max_merchants_per_circle, color, executive):
        """
        Optimized circle creation ensuring all merchants are covered
        """
        circles = []
        remaining_data = merchant_data.copy().reset_index(drop=True)
        circle_count = 0
        
        while len(remaining_data) > 0:
            if len(remaining_data) <= max_merchants_per_circle:
                # If remaining merchants are few, create one final circle covering all
                center_lat = remaining_data['merchant_latitude'].mean()
                center_lon = remaining_data['merchant_longitude'].mean()
                merchants_in_circle = remaining_data['merchant_code'].tolist()
                
                # Ensure radius covers all remaining merchants
                if len(remaining_data) > 1:
                    max_distance = 0
                    for _, merchant in remaining_data.iterrows():
                        distance = self.haversine_distance(
                            center_lat, center_lon,
                            merchant['merchant_latitude'], merchant['merchant_longitude']
                        )
                        max_distance = max(max_distance, distance)
                    # Add 20% buffer to ensure coverage
                    actual_radius = max(radius_meters, max_distance * 1.2)
                else:
                    actual_radius = radius_meters
            else:
                # Find optimal center using fast algorithm
                center_lat, center_lon = self._find_optimal_center_fast(remaining_data, radius_meters, max_merchants_per_circle)
                
                # Get merchants within radius
                merchants_in_circle = self._get_merchants_in_circle_fast(
                    remaining_data, center_lat, center_lon, radius_meters, max_merchants_per_circle
                )
                
                # If no merchants found (shouldn't happen but safety check)
                if not merchants_in_circle:
                    # Take the closest merchant
                    first_merchant = remaining_data.iloc[0]
                    center_lat = first_merchant['merchant_latitude']
                    center_lon = first_merchant['merchant_longitude']
                    merchants_in_circle = [first_merchant['merchant_code']]
                
                actual_radius = radius_meters
            
            # Ensure we have at least one merchant
            if not merchants_in_circle and len(remaining_data) > 0:
                merchants_in_circle = [remaining_data.iloc[0]['merchant_code']]
                center_lat = remaining_data.iloc[0]['merchant_latitude']
                center_lon = remaining_data.iloc[0]['merchant_longitude']
                actual_radius = radius_meters
            
            # Create circle only if we have merchants
            if merchants_in_circle:
                circle = {
                    'name': str(circle_count + 1),
                    'center_lat': center_lat,
                    'center_lon': center_lon,
                    'radius': actual_radius,
                    'color': color,
                    'merchants': merchants_in_circle,
                    'merchant_count': len(merchants_in_circle),
                    'executive': executive
                }
                
                circles.append(circle)
                
                # Remove assigned merchants
                remaining_data = remaining_data[~remaining_data['merchant_code'].isin(merchants_in_circle)].reset_index(drop=True)
                circle_count += 1
            else:
                # Emergency exit if no merchants can be assigned
                break
            
            # Safety check to prevent infinite loop
            if circle_count > 100:
                # If we hit the limit, assign all remaining merchants to the last circle
                if len(remaining_data) > 0:
                    final_merchants = remaining_data['merchant_code'].tolist()
                    if circles:  # Add to last circle
                        circles[-1]['merchants'].extend(final_merchants)
                        circles[-1]['merchant_count'] = len(circles[-1]['merchants'])
                    else:  # Create a final circle
                        center_lat = remaining_data['merchant_latitude'].mean()
                        center_lon = remaining_data['merchant_longitude'].mean()
                        final_circle = {
                            'name': str(circle_count + 1),
                            'center_lat': center_lat,
                            'center_lon': center_lon,
                            'radius': radius_meters * 2,  # Larger radius to ensure coverage
                            'color': color,
                            'merchants': final_merchants,
                            'merchant_count': len(final_merchants),
                            'executive': executive
                        }
                        circles.append(final_circle)
                break
        
        return circles
    
    def _find_optimal_center_fast(self, merchant_data, radius_meters, max_merchants_per_circle):
        """
        Fast optimal center finding ensuring good coverage
        """
        if len(merchant_data) == 0:
            return 0, 0
        
        if len(merchant_data) == 1:
            return merchant_data.iloc[0]['merchant_latitude'], merchant_data.iloc[0]['merchant_longitude']
        
        if len(merchant_data) <= 10:  # For small datasets, use simple method
            return self._find_optimal_center_simple(merchant_data, radius_meters)
        
        # For larger datasets, use sampling approach
        sample_size = min(15, len(merchant_data))
        
        # Always include geometric center as a candidate
        geo_center_lat = merchant_data['merchant_latitude'].mean()
        geo_center_lon = merchant_data['merchant_longitude'].mean()
        
        # Sample additional points
        sample_indices = np.random.choice(len(merchant_data), sample_size - 1, replace=False)
        sample_data = merchant_data.iloc[sample_indices]
        
        best_center = (geo_center_lat, geo_center_lon)
        max_coverage = 0
        
        # Check geometric center first
        distances = self._calculate_distances_vectorized(
            merchant_data['merchant_latitude'].values,
            merchant_data['merchant_longitude'].values,
            geo_center_lat, geo_center_lon
        )
        merchants_in_radius = np.sum(distances <= radius_meters)
        max_coverage = merchants_in_radius
        
        # Check sampled points
        for _, row in sample_data.iterrows():
            center_lat, center_lon = row['merchant_latitude'], row['merchant_longitude']
            
            distances = self._calculate_distances_vectorized(
                merchant_data['merchant_latitude'].values,
                merchant_data['merchant_longitude'].values,
                center_lat, center_lon
            )
            
            merchants_in_radius = np.sum(distances <= radius_meters)
            
            if merchants_in_radius > max_coverage:
                max_coverage = merchants_in_radius
                best_center = (center_lat, center_lon)
        
        return best_center
    
    def _find_optimal_center_simple(self, merchant_data, radius_meters):
        """
        Simple center finding for small datasets
        """
        # For small datasets, just use geometric center
        return merchant_data['merchant_latitude'].mean(), merchant_data['merchant_longitude'].mean()
    
    def _get_merchants_in_circle_fast(self, merchant_data, center_lat, center_lon, radius_meters, max_merchants):
        """
        Fast merchant selection ensuring at least one merchant is always selected
        """
        if len(merchant_data) == 0:
            return []
        
        # Calculate all distances at once
        distances = self._calculate_distances_vectorized(
            merchant_data['merchant_latitude'].values,
            merchant_data['merchant_longitude'].values,
            center_lat, center_lon
        )
        
        # Get indices of merchants within radius
        within_radius = distances <= radius_meters
        merchants_within_count = np.sum(within_radius)
        
        if merchants_within_count == 0:
            # If no merchants within radius, take the closest ones up to max_merchants
            # This ensures we always assign merchants
            closest_indices = np.argsort(distances)[:min(max_merchants, len(merchant_data))]
            return merchant_data.iloc[closest_indices]['merchant_code'].tolist()
        
        # Get merchants within radius
        merchants_in_radius = merchant_data[within_radius]
        
        if len(merchants_in_radius) <= max_merchants:
            return merchants_in_radius['merchant_code'].tolist()
        else:
            # Take closest merchants if too many
            radius_distances = distances[within_radius]
            closest_indices = np.argsort(radius_distances)[:max_merchants]
            return merchants_in_radius.iloc[closest_indices]['merchant_code'].tolist()
    
    def _calculate_distances_vectorized(self, lats, lons, center_lat, center_lon):
        """
        Vectorized haversine distance calculation for much better performance
        """
        # Convert to radians
        lat1 = np.radians(center_lat)
        lon1 = np.radians(center_lon)
        lat2 = np.radians(lats)
        lon2 = np.radians(lons)
        
        # Haversine formula vectorized
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        
        # Earth radius in meters
        R = 6371000
        distances = R * c
        
        return distances
    
    def _find_optimal_center(self, merchant_data, radius_meters):
        """
        Find optimal center point that maximizes merchant coverage (legacy method)
        """
        # Use the optimized version
        return self._find_optimal_center_fast(merchant_data, radius_meters, 20)
