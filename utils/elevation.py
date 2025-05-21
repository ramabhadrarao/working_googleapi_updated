import logging
import googlemaps
from geopy.distance import geodesic

# Set up logger
logger = logging.getLogger(__name__)

def get_elevation_data(gmaps, route_points, sample_interval=20):
    """
    Get elevation data for points along a route
    
    Args:
        gmaps: Google Maps client instance
        route_points: List of route coordinates [lat, lng]
        sample_interval: Sample every Nth point to reduce API calls
    
    Returns:
        List of dicts with elevation data
    """
    if not route_points:
        return []
        
    elevation_data = []
    
    try:
        # Sample route points to reduce API calls
        sampled_points = route_points[::sample_interval]
        
        # Cap the number of points to avoid exceeding API limits
        max_points = 100
        if len(sampled_points) > max_points:
            step = len(sampled_points) // max_points
            sampled_points = sampled_points[::step]
        
        # Prepare locations for API call
        locations = [{'lat': point[0], 'lng': point[1]} for point in sampled_points]
        
        # Make API call
        if not locations:
            return []
            
        results = gmaps.elevation(locations)
        
        # Process results
        for i, result in enumerate(results):
            if 'elevation' in result:
                elevation_data.append({
                    'location': {
                        'lat': result['location']['lat'],
                        'lng': result['location']['lng']
                    },
                    'elevation': result['elevation'],
                    'resolution': result.get('resolution', 0)
                })
                
        return elevation_data
    
    except Exception as e:
        logger.error(f"Error getting elevation data: {e}")
        return []

def calculate_slope(point1, point2):
    """Calculate slope between two elevation points as percentage"""
    if not point1 or not point2:
        return 0
        
    try:
        # Get coordinates
        lat1, lng1 = point1['location']['lat'], point1['location']['lng']
        lat2, lng2 = point2['location']['lat'], point2['location']['lng']
        
        # Calculate horizontal distance in meters
        horizontal_distance = geodesic((lat1, lng1), (lat2, lng2)).meters
        
        if horizontal_distance == 0:
            return 0
        
        # Calculate vertical change
        elevation_change = point2['elevation'] - point1['elevation']
        
        # Calculate slope as percentage
        slope_percent = (elevation_change / horizontal_distance) * 100
        
        return slope_percent
    
    except Exception as e:
        logger.error(f"Error calculating slope: {e}")
        return 0

def identify_steep_segments(elevation_data, threshold_percent=8):
    """Identify segments with steep slopes"""
    if not elevation_data or len(elevation_data) < 2:
        return []
        
    steep_segments = []
    
    for i in range(len(elevation_data) - 1):
        slope = calculate_slope(elevation_data[i], elevation_data[i+1])
        
        if abs(slope) >= threshold_percent:
            steep_segments.append({
                'start_point': elevation_data[i],
                'end_point': elevation_data[i+1],
                'slope_percent': slope,
                'direction': 'uphill' if slope > 0 else 'downhill'
            })
    
    return steep_segments

def get_elevation_stats(elevation_data):
    """Calculate elevation statistics for a route"""
    if not elevation_data:
        return {
            'min_elevation': 0,
            'max_elevation': 0,
            'total_ascent': 0,
            'total_descent': 0,
            'elevation_range': 0
        }
    
    # Extract elevation values
    elevations = [point['elevation'] for point in elevation_data]
    
    # Calculate min and max
    min_elevation = min(elevations)
    max_elevation = max(elevations)
    
    # Calculate total ascent and descent
    total_ascent = 0
    total_descent = 0
    
    for i in range(1, len(elevations)):
        diff = elevations[i] - elevations[i-1]
        if diff > 0:
            total_ascent += diff
        else:
            total_descent += abs(diff)
    
    return {
        'min_elevation': min_elevation,
        'max_elevation': max_elevation,
        'total_ascent': total_ascent,
        'total_descent': total_descent,
        'elevation_range': max_elevation - min_elevation
    }