import math
from geopy.distance import geodesic
import numpy as np
import logging

logger = logging.getLogger(__name__)

def split_route_into_segments(polyline, segment_length_meters=5000):
    """Split a route into roughly equal segments of specified length"""
    segments = []
    current_segment = []
    current_length = 0
    
    for i in range(len(polyline) - 1):
        point1 = (polyline[i][0], polyline[i][1])
        point2 = (polyline[i+1][0], polyline[i+1][1])
        
        # Calculate distance between consecutive points
        try:
            distance = geodesic(point1, point2).meters
        except:
            distance = 100  # Default value if calculation fails
        
        if current_length + distance > segment_length_meters and len(current_segment) > 0:
            # End of segment reached
            current_segment.append(polyline[i])
            segments.append({
                'points': current_segment.copy(),  # Make sure to copy the list
                'start_point': current_segment[0],
                'end_point': current_segment[-1],
                'distance': current_length
            })
            current_segment = [polyline[i]]
            current_length = 0
        else:
            current_segment.append(polyline[i])
            current_length += distance
    
    # Add the last segment if it has points
    if current_segment:
        # Make sure to add the last point from the polyline to close the segment
        if polyline and i+1 < len(polyline):
            current_segment.append(polyline[-1])
        
        segments.append({
            'points': current_segment,
            'start_point': current_segment[0],
            'end_point': current_segment[-1],
            'distance': current_length
        })
    
    return segments

def point_in_segment(point, segment):
    """Check if a point is within a route segment"""
    point_coords = (point['lat'], point['lng'])
    
    for seg_point in segment['points']:
        seg_coords = (seg_point[0], seg_point[1])
        if geodesic(point_coords, seg_coords).meters < 100:  # Within 100m
            return True
    return False

def calculate_elevation_change(elevation_data, segment):
    """Calculate elevation change within a segment"""
    if not elevation_data:
        return 0
        
    segment_elevations = []
    
    # Find elevation points within the segment
    for elev in elevation_data:
        elev_point = (elev['location']['lat'], elev['location']['lng'])
        for seg_point in segment['points']:
            seg_coords = (seg_point[0], seg_point[1])
            if geodesic(elev_point, seg_coords).meters < 100:  # Within 100m
                segment_elevations.append(elev['elevation'])
                break
    
    if not segment_elevations:
        return 0
        
    # Calculate max elevation change
    return max(segment_elevations) - min(segment_elevations)

def is_adverse_weather(weather):
    """Determine if weather conditions are adverse"""
    adverse_conditions = [
        'rain', 'snow', 'storm', 'fog', 'mist', 'haze', 'dust', 
        'thunderstorm', 'drizzle', 'tornado', 'hurricane'
    ]
    
    if not weather or 'description' not in weather:
        return False
        
    description = weather['description'].lower()
    
    # Check for adverse conditions
    for condition in adverse_conditions:
        if condition in description:
            return True
            
    # Check for extreme temperatures
    if 'temp' in weather:
        if weather['temp'] > 40 or weather['temp'] < 5:
            return True
            
    return False

def get_segment_weather(weather_data, segment):
    """Get weather data for a segment"""
    if not weather_data:
        return None
        
    # Find weather points within the segment
    for weather in weather_data:
        weather_point = (weather['lat'], weather['lng'])
        for seg_point in segment['points']:
            seg_coords = (seg_point[0], seg_point[1])
            if geodesic(weather_point, seg_coords).meters < 5000:  # Within 5km
                return weather
                
    return None

def get_road_quality(gmaps, segment, api_key):
    """Attempt to estimate road quality using Google Maps data"""
    try:
        # Get elevation data for segment to identify changes (possible indicator of road quality)
        elevation_samples = 5
        waypoints = []
        
        # Sample points along the segment
        step = max(1, len(segment['points']) // elevation_samples)
        for i in range(0, len(segment['points']), step):
            if i < len(segment['points']):
                waypoints.append((segment['points'][i][0], segment['points'][i][1]))
        
        # Use a simple heuristic based on road type and elevation changes
        # This is a simplified approach - in reality, you'd need actual road quality data
        road_quality = {
            'poor_sections': [],
            'quality_score': 10  # Start with perfect score
        }
        
        return road_quality
    except Exception as e:
        logger.error(f"Error assessing road quality: {e}")
        return None

def calculate_terrain_type(segment, gmaps):
    """Determine if segment is urban, semi-urban, or rural"""
    try:
        # Sample a point from the middle of the segment
        mid_index = len(segment['points']) // 2
        lat, lng = segment['points'][mid_index]
        
        # Use reverse geocoding to get location details
        result = gmaps.reverse_geocode((lat, lng))
        
        # Analyze address components to determine terrain type
        if result and len(result) > 0:
            address_components = result[0].get('address_components', [])
            types = []
            for component in address_components:
                types.extend(component.get('types', []))
            
            # Simple classification heuristics
            if any(t in types for t in ['locality', 'sublocality', 'neighborhood']):
                if 'political' in types and 'postal_code' in types:
                    return 'urban'
                else:
                    return 'semi-urban'
            else:
                return 'rural'
        
        return 'unknown'
    except Exception as e:
        logger.error(f"Error determining terrain type: {e}")
        return 'unknown'

def calculate_route_risk(route_data, turns, elevation_data, weather_data, gmaps, api_key):
    """Calculate risk score for route segments based on multiple factors"""
    risk_segments = []
    
    # Process route into segments (e.g., every 5km)
    if not route_data or len(route_data) < 2:
        # Return a default segment if the route is too short
        default_segment = {
            'start_point': route_data[0] if route_data else [0, 0],
            'end_point': route_data[-1] if len(route_data) > 1 else [0, 0],
            'points': route_data[:] if route_data else [],
            'distance': 0,
            'risk_factors': [],
            'risk_score': 0,
            'risk_level': 'LOW',
            'color': '#28a745',
            'terrain_type': 'unknown'
        }
        return [default_segment]
    
    # Try to split the route into segments
    try:
        route_segments = split_route_into_segments(route_data, 5000)  # 5km segments
    except Exception as e:
        logger.error(f"Error splitting route: {e}")
        # Return a default segment if splitting fails
        default_segment = {
            'start_point': route_data[0],
            'end_point': route_data[-1],
            'points': route_data[:],
            'distance': 0,
            'risk_factors': [],
            'risk_score': 0,
            'risk_level': 'LOW',
            'color': '#28a745',
            'terrain_type': 'unknown'
        }
        return [default_segment]
    
    # Process each segment
    for segment in route_segments:
        segment_risk = {
            'start_point': segment['start_point'],
            'end_point': segment['end_point'],
            'points': segment.get('points', [segment['start_point'], segment['end_point']]),
            'distance': segment['distance'],
            'risk_factors': [],
            'risk_score': 0
        }
        
        # Check for sharp turns in segment
        try:
            segment_turns = [t for t in turns if point_in_segment(t, segment)]
            if len(segment_turns) > 0:
                segment_risk['risk_factors'].append({
                    'type': 'sharp_turns',
                    'count': len(segment_turns),
                    'details': segment_turns,
                    'weight': 2.0
                })
                segment_risk['risk_score'] += len(segment_turns) * 2.0
        except Exception as e:
            logger.error(f"Error checking turns: {e}")
        
        # Check for elevation changes
        try:
            elevation_change = calculate_elevation_change(elevation_data, segment)
            if elevation_change > 100:  # More than 100m change
                segment_risk['risk_factors'].append({
                    'type': 'elevation',
                    'change': elevation_change,
                    'weight': 1.5
                })
                segment_risk['risk_score'] += min(elevation_change / 100, 5) * 1.5
        except Exception as e:
            logger.error(f"Error checking elevation: {e}")
            
        # Check for adverse weather
        try:
            segment_weather = get_segment_weather(weather_data, segment)
            if segment_weather and is_adverse_weather(segment_weather):
                segment_risk['risk_factors'].append({
                    'type': 'weather',
                    'condition': segment_weather['description'],
                    'details': segment_weather,
                    'weight': 2.0
                })
                segment_risk['risk_score'] += 2.0
        except Exception as e:
            logger.error(f"Error checking weather: {e}")
        
        # Try to determine terrain type
        try:
            terrain_type = calculate_terrain_type(segment, gmaps)
            segment_risk['terrain_type'] = terrain_type
        except Exception as e:
            logger.error(f"Error determining terrain type: {e}")
            segment_risk['terrain_type'] = 'unknown'
        
        # Check road quality (if possible)
        try:
            road_quality = get_road_quality(gmaps, segment, api_key)
            if road_quality and 'quality_score' in road_quality:
                if road_quality['quality_score'] < 7:
                    segment_risk['risk_factors'].append({
                        'type': 'road_quality',
                        'score': road_quality['quality_score'],
                        'details': road_quality.get('poor_sections', []),
                        'weight': 2.0
                    })
                    segment_risk['risk_score'] += (10 - road_quality['quality_score']) * 0.5
        except Exception as e:
            logger.error(f"Error checking road quality: {e}")
            
        # Classify risk level
        if segment_risk['risk_score'] > 8:
            segment_risk['risk_level'] = 'HIGH'
            segment_risk['color'] = '#dc3545'  # Bootstrap danger color
        elif segment_risk['risk_score'] > 4:
            segment_risk['risk_level'] = 'MEDIUM'
            segment_risk['color'] = '#fd7e14'  # Bootstrap warning color
        else:
            segment_risk['risk_level'] = 'LOW'
            segment_risk['color'] = '#28a745'  # Bootstrap success color
            
        risk_segments.append(segment_risk)
    
    return risk_segments

def get_risk_map_data(risk_segments):
    """Generate data for rendering risk information on maps"""
    map_data = []
    
    for segment in risk_segments:
        # Check if 'points' key exists, otherwise use start and end points to create a simple path
        if 'points' in segment:
            points = segment['points']
        else:
            # Use start_point and end_point to create a simple path
            # We need to ensure start_point and end_point are available
            if 'start_point' in segment and 'end_point' in segment:
                points = [segment['start_point'], segment['end_point']]
            else:
                # Skip this segment if we don't have any points
                continue
        
        map_segment = {
            'path': [{'lat': p[0], 'lng': p[1]} for p in points],
            'risk_level': segment.get('risk_level', 'LOW'),
            'color': segment.get('color', '#28a745'),  # Default to green if no color
            'risk_score': segment.get('risk_score', 0)
        }
        map_data.append(map_segment)
    
    return map_data

def get_vehicle_adjusted_time(route_duration, vehicle_type):
    """Adjust travel time based on vehicle type"""
    multipliers = {
        'car': 1.0,
        'motorcycle': 0.9,
        'medium_truck': 1.3,
        'heavy_truck': 1.5,
        'bus': 1.4,
        'tanker': 1.6
    }
    
    multiplier = multipliers.get(vehicle_type, 1.0)
    
    # Apply multiplier to duration
    if isinstance(route_duration, dict) and 'value' in route_duration:
        adjusted_value = route_duration['value'] * multiplier
    else:
        # Handle case where route_duration is not a dictionary
        try:
            adjusted_value = int(route_duration) * multiplier
        except (TypeError, ValueError):
            return {
                'adjusted_value': None,
                'adjusted_text': None,
                'multiplier': multiplier
            }
    
    # Format duration text
    hours = int(adjusted_value // 3600)
    minutes = int((adjusted_value % 3600) // 60)
    
    if hours > 0:
        adjusted_text = f"{hours} hour{'s' if hours != 1 else ''}"
        if minutes > 0:
            adjusted_text += f" {minutes} min{'s' if minutes != 1 else ''}"
    else:
        adjusted_text = f"{minutes} min{'s' if minutes != 1 else ''}"
    
    return {
        'adjusted_value': adjusted_value,
        'adjusted_text': adjusted_text,
        'multiplier': multiplier
    }

def analyze_blind_spots(turns, threshold=70):
    """Identify blind spots (turns with angles above threshold)"""
    if not turns:
        return []
    
    blind_spots = [turn for turn in turns if turn.get('angle', 0) >= threshold]
    
    # Sort by angle (most severe first)
    blind_spots.sort(key=lambda x: x.get('angle', 0), reverse=True)
    
    return blind_spots

def calculate_overall_risk_score(risk_segments):
    """Calculate overall risk score for a route based on its segments"""
    if not risk_segments:
        return 0
    
    # Weight segments by their length
    total_length = sum(segment.get('distance', 0) for segment in risk_segments)
    weighted_score = 0
    
    if total_length > 0:
        for segment in risk_segments:
            distance = segment.get('distance', 0)
            weight = distance / total_length if total_length > 0 else 0
            weighted_score += segment.get('risk_score', 0) * weight
    else:
        # Simple average if distances are not available
        weighted_score = sum(segment.get('risk_score', 0) for segment in risk_segments) / len(risk_segments)
    
    return round(weighted_score, 2)

def detect_bridges_from_elevation(elevation_data, min_elevation_change=20, min_distance=100):
    """Attempt to detect bridges based on sudden elevation changes"""
    if not elevation_data or len(elevation_data) < 3:
        return []
    
    bridges = []
    last_bridge_index = -9999  # To avoid detecting bridges too close to each other
    
    for i in range(1, len(elevation_data) - 1):
        # Check for a significant dip in elevation (bridge over valley)
        dip = (elevation_data[i-1]['elevation'] - elevation_data[i]['elevation'] > min_elevation_change and
               elevation_data[i+1]['elevation'] - elevation_data[i]['elevation'] > min_elevation_change)
        
        # Check for a significant rise in elevation (bridge over water)
        rise = (elevation_data[i]['elevation'] - elevation_data[i-1]['elevation'] > min_elevation_change and
                elevation_data[i]['elevation'] - elevation_data[i+1]['elevation'] > min_elevation_change)
        
        if (dip or rise) and i > last_bridge_index + min_distance:
            bridges.append({
                'lat': elevation_data[i]['location']['lat'],
                'lng': elevation_data[i]['location']['lng'],
                'name': 'Potential Bridge',
                'elevation_change': abs(elevation_data[i]['elevation'] - elevation_data[i-1]['elevation']),
                'source': 'elevation'
            })
            last_bridge_index = i
    
    return bridges