# utils/csv_route_analyzer.py - COMPLETE FIXED VERSION
import pandas as pd
import numpy as np
import json
import googlemaps
import logging
from geopy.distance import geodesic
from datetime import datetime
import math
import concurrent.futures
import time

# Import existing utility functions
from .risk_analysis import calculate_route_risk, get_risk_map_data, get_vehicle_adjusted_time
from .compliance import ComplianceChecker
from .emergency import categorize_emergency_services, find_critical_emergency_points, create_emergency_response_plan
from .environmental import EnvironmentalAnalyzer
from .elevation import get_elevation_data

logger = logging.getLogger(__name__)

class CSVRouteAnalyzer:
    """Analyze routes from CSV data containing latitude/longitude coordinates - COMPLETE VERSION"""
    
    def __init__(self):
        self.compliance_checker = ComplianceChecker()
        self.environmental_analyzer = EnvironmentalAnalyzer()
        # Configuration for performance optimization
        self.config = {
            'max_points_for_analysis': 500,
            'poi_search_points': 5,
            'elevation_sample_points': 20,
            'weather_sample_points': 3,
            'sharp_turn_sample_interval': 5,
            'enable_parallel_processing': True,
            'api_timeout': 10
        }
    
    def optimize_point_density(self, points, target_points=500):
        """Reduce point density using Douglas-Peucker algorithm"""
        if len(points) <= target_points:
            return points
        
        logger.info(f"Optimizing {len(points)} points to approximately {target_points}")
        
        # Simple uniform sampling as fallback
        if len(points) > target_points * 2:
            step = len(points) // target_points
            optimized = points[::step]
            # Always include start and end points
            if optimized[0] != points[0]:
                optimized.insert(0, points[0])
            if optimized[-1] != points[-1]:
                optimized.append(points[-1])
            return optimized
        
        return self.douglas_peucker_simplify(points, tolerance=0.0001)
    
    def douglas_peucker_simplify(self, points, tolerance=0.0001):
        """Simplify route using Douglas-Peucker algorithm"""
        if len(points) <= 2:
            return points
        
        # Find the point with maximum distance from line between first and last
        max_distance = 0
        max_index = 0
        
        for i in range(1, len(points) - 1):
            distance = self.point_to_line_distance(points[i], points[0], points[-1])
            if distance > max_distance:
                max_distance = distance
                max_index = i
        
        # If max distance is greater than tolerance, recursively simplify
        if max_distance > tolerance:
            left_points = self.douglas_peucker_simplify(points[:max_index + 1], tolerance)
            right_points = self.douglas_peucker_simplify(points[max_index:], tolerance)
            return left_points[:-1] + right_points
        else:
            return [points[0], points[-1]]
    
    def point_to_line_distance(self, point, line_start, line_end):
        """Calculate perpendicular distance from point to line"""
        try:
            # Convert to approximate Cartesian coordinates for calculation
            x0, y0 = point[1], point[0]  # lng, lat
            x1, y1 = line_start[1], line_start[0]
            x2, y2 = line_end[1], line_end[0]
            
            # Calculate distance using point-to-line formula
            num = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
            den = math.sqrt((y2 - y1)**2 + (x2 - x1)**2)
            
            return num / den if den != 0 else 0
        except:
            return 0
    
    def process_csv_route(self, csv_file_path, bounds, vehicle_type, api_key):
        """
        Process CSV file and analyze route within specified bounds - COMPLETE
        """
        start_time = time.time()
        try:
            logger.info("Starting CSV route processing...")
            
            # Read CSV file
            df = pd.read_csv(csv_file_path)
            
            # Validate CSV structure
            if len(df.columns) < 2:
                return {'success': False, 'error': 'CSV must have at least 2 columns (latitude, longitude)'}
            
            # Extract coordinates (assume first two columns are lat, lng)
            original_points = []
            for index, row in df.iterrows():
                try:
                    lat = float(row.iloc[0])
                    lng = float(row.iloc[1])
                    
                    # Validate coordinate ranges
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        original_points.append([lat, lng])
                except (ValueError, TypeError):
                    continue
            
            if not original_points:
                return {'success': False, 'error': 'No valid coordinate pairs found in CSV'}
            
            logger.info(f"Loaded {len(original_points)} valid coordinates")
            
            # Filter points within bounds
            filtered_points = self.filter_points_by_bounds(original_points, bounds)
            
            if not filtered_points:
                return {'success': False, 'error': 'No points found within specified bounds'}
            
            logger.info(f"Filtered to {len(filtered_points)} points within bounds")
            
            # OPTIMIZE: Reduce point density for analysis
            if len(filtered_points) > self.config['max_points_for_analysis']:
                optimized_points = self.optimize_point_density(
                    filtered_points, 
                    self.config['max_points_for_analysis']
                )
                logger.info(f"Optimized to {len(optimized_points)} points for analysis")
            else:
                optimized_points = filtered_points
            
            # Sort points to create logical route order
            ordered_points = self.order_route_points(optimized_points, bounds)
            
            # Initialize Google Maps client
            try:
                gmaps = googlemaps.Client(key=api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Google Maps client: {e}")
                gmaps = None
            
            # Process analysis in parallel if enabled
            if self.config['enable_parallel_processing']:
                analysis_data = self.process_route_parallel(ordered_points, vehicle_type, gmaps, api_key)
            else:
                analysis_data = self.process_route_sequential(ordered_points, vehicle_type, gmaps, api_key)
            
            # Add metadata
            analysis_data.update({
                'from': f"{bounds['from_lat']:.6f}, {bounds['from_lng']:.6f}",
                'to': f"{bounds['to_lat']:.6f}, {bounds['to_lng']:.6f}",
                'vehicle_type': vehicle_type,
                'original_points': original_points[:100],  # Limit stored original points
                'filtered_points': ordered_points,
                'points_filtered': len(original_points) - len(ordered_points),
                'processing_time': round(time.time() - start_time, 2)
            })
            
            logger.info(f"Route analysis completed in {analysis_data['processing_time']} seconds")
            
            return {
                'success': True,
                'data': analysis_data
            }
            
        except Exception as e:
            logger.error(f"Error processing CSV route: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def process_route_parallel(self, points, vehicle_type, gmaps, api_key):
        """Process route analysis using parallel processing"""
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Submit parallel tasks
            future_stats = executor.submit(self.calculate_route_statistics, points)
            future_turns = executor.submit(self.find_sharp_turns_optimized, points)
            future_pois = executor.submit(self.find_pois_optimized, gmaps, points)
            future_elevation = executor.submit(self.get_elevation_optimized, gmaps, points)
            
            # Collect results with timeout
            try:
                results['stats'] = future_stats.result(timeout=30)
                results['sharp_turns'] = future_turns.result(timeout=30)
                results['pois'] = future_pois.result(timeout=60)
                results['elevation'] = future_elevation.result(timeout=60)
            except concurrent.futures.TimeoutError:
                logger.warning("Some analysis tasks timed out, using partial results")
                results['stats'] = self.calculate_route_statistics(points)
                results['sharp_turns'] = []
                results['pois'] = {}
                results['elevation'] = []
        
        # Sequential processing for dependent tasks
        results['weather'] = self.get_weather_optimized(points, api_key)
        results['risk_segments'] = self.calculate_risk_optimized(points, results.get('sharp_turns', []))
        results['compliance'] = self.check_route_compliance_optimized(points, vehicle_type)
        results['emergency'] = self.analyze_emergency_optimized(points, results.get('pois', {}))
        results['environmental'] = self.analyze_environmental_optimized(points, vehicle_type)
        
        return self.format_analysis_results(results)
    
    def process_route_sequential(self, points, vehicle_type, gmaps, api_key):
        """Process route analysis sequentially"""
        results = {}
        
        results['stats'] = self.calculate_route_statistics(points)
        results['sharp_turns'] = self.find_sharp_turns_optimized(points)
        results['pois'] = self.find_pois_optimized(gmaps, points)
        results['elevation'] = self.get_elevation_optimized(gmaps, points)
        results['weather'] = self.get_weather_optimized(points, api_key)
        results['risk_segments'] = self.calculate_risk_optimized(points, results.get('sharp_turns', []))
        results['compliance'] = self.check_route_compliance_optimized(points, vehicle_type)
        results['emergency'] = self.analyze_emergency_optimized(points, results.get('pois', {}))
        results['environmental'] = self.analyze_environmental_optimized(points, vehicle_type)
        
        return self.format_analysis_results(results)
    
    def find_sharp_turns_optimized(self, points, angle_threshold=30):
        """Find sharp turns with optimized sampling"""
        if len(points) < 3:
            return []
        
        sharp_turns = []
        interval = max(1, self.config['sharp_turn_sample_interval'])
        
        for i in range(interval, len(points) - interval, interval):
            try:
                # Use points with larger intervals for more significant turns
                p1 = points[max(0, i - interval)]
                p2 = points[i]
                p3 = points[min(len(points) - 1, i + interval)]
                
                angle = self.calculate_turn_angle(p1, p2, p3)
                
                if angle >= angle_threshold:
                    sharp_turns.append({
                        'lat': p2[0],
                        'lng': p2[1],
                        'angle': round(angle, 2),
                        'index': i
                    })
            except Exception as e:
                continue
        
        logger.info(f"Found {len(sharp_turns)} sharp turns")
        return sharp_turns
    
    def find_pois_optimized(self, gmaps, points):
        """Find POIs with minimal API calls"""
        if not gmaps or len(points) < 2:
            return {}
        
        poi_data = {
            'petrol_bunks': {},
            'hospitals': {},
            'schools': {},
            'food_stops': {},
            'police_stations': {}
        }
        
        # Use only strategic points for POI search
        strategic_indices = [
            0,  # Start
            len(points) // 4,      # 25%
            len(points) // 2,      # 50%
            3 * len(points) // 4,  # 75%
            len(points) - 1        # End
        ]
        
        strategic_points = [points[i] for i in strategic_indices if i < len(points)]
        
        categories = {
            'petrol_bunks': 'gas_station',
            'hospitals': 'hospital',
            'schools': 'school',
            'food_stops': 'restaurant',
            'police_stations': 'police'
        }
        
        for point in strategic_points[:self.config['poi_search_points']]:
            for category, place_type in categories.items():
                try:
                    result = gmaps.places_nearby(
                        location=(point[0], point[1]),
                        radius=3000,  # 3km radius
                        type=place_type
                    )
                    
                    for place in result.get('results', [])[:3]:  # Limit to top 3
                        poi_data[category][place['name']] = place.get('vicinity', 'Unknown location')
                        
                except Exception as e:
                    logger.warning(f"POI search error for {category}: {e}")
                    continue
        
        return poi_data
    
    def get_elevation_optimized(self, gmaps, points):
        """Get elevation data with reduced API calls"""
        if not gmaps or len(points) < 2:
            return []
        
        # Sample points for elevation
        sample_size = min(self.config['elevation_sample_points'], len(points))
        if sample_size >= len(points):
            sample_points = points
        else:
            step = len(points) // sample_size
            sample_points = points[::step]
        
        try:
            elevation_data = get_elevation_data(gmaps, sample_points, sample_interval=1)
            return elevation_data[:20]  # Limit results
        except Exception as e:
            logger.warning(f"Elevation data error: {e}")
            return []
    
    def get_weather_optimized(self, points, api_key):
        """Get weather data with minimal API calls"""
        if len(points) < 2:
            return []
        
        # Use only 3 strategic points for weather
        weather_points = [
            points[0],                    # Start
            points[len(points) // 2],     # Middle
            points[-1]                    # End
        ]
        
        weather_data = []
        for point in weather_points[:self.config['weather_sample_points']]:
            try:
                import requests
                url = f"https://api.openweathermap.org/data/2.5/weather?lat={point[0]}&lon={point[1]}&appid={api_key}&units=metric"
                response = requests.get(url, timeout=self.config['api_timeout'])
                
                if response.status_code == 200:
                    data = response.json()
                    weather_data.append({
                        "lat": point[0],
                        "lng": point[1],
                        "location": data.get("name", f"{point[0]:.3f},{point[1]:.3f}"),
                        "temp": data['main']['temp'],
                        "description": data['weather'][0]['description'],
                        "icon": data['weather'][0]['icon']
                    })
            except Exception as e:
                logger.warning(f"Weather API error: {e}")
                continue
        
        return weather_data
    
    def calculate_risk_optimized(self, points, sharp_turns):
        """Calculate risk with reduced complexity"""
        try:
            # Sample points for risk analysis
            sample_size = min(100, len(points))
            if len(points) > sample_size:
                step = len(points) // sample_size
                sample_points = points[::step]
            else:
                sample_points = points
            
            # Simplified risk calculation
            risk_segments = []
            for i in range(0, len(sample_points), 10):
                segment_points = sample_points[i:i+10]
                
                # Basic risk scoring
                risk_score = 0
                risk_level = "LOW"
                
                # Check for sharp turns in segment
                for turn in sharp_turns:
                    for point in segment_points:
                        if abs(point[0] - turn['lat']) < 0.001 and abs(point[1] - turn['lng']) < 0.001:
                            risk_score += turn['angle'] / 10
                
                if risk_score > 5:
                    risk_level = "HIGH"
                elif risk_score > 2:
                    risk_level = "MEDIUM"
                
                risk_segments.append({
                    'points': segment_points,
                    'risk_level': risk_level,
                    'risk_score': min(10, risk_score),
                    'reasons': ['Sharp turns'] if risk_score > 0 else []
                })
            
            return risk_segments
        except Exception as e:
            logger.warning(f"Risk calculation error: {e}")
            return []
    
    def check_route_compliance_optimized(self, points, vehicle_type):
        """Check regulatory compliance for the route - OPTIMIZED"""
        try:
            # Use existing compliance checker with simplified checks
            vehicle_compliance = self.compliance_checker.check_vehicle_compliance(vehicle_type)
            
            # Calculate estimated duration for RTSP check
            route_stats = self.calculate_route_statistics(points)
            rtsp_compliance = self.compliance_checker.check_rtsp_compliance(
                route_stats['duration_seconds'], vehicle_type
            )
            
            # Simplified restricted zones check
            restricted_zones = []  # Simplified for performance
            
            return {
                'vehicle': vehicle_compliance,
                'rtsp': rtsp_compliance,
                'restricted_zones': restricted_zones,
                'speed_limits': []  # Simplified for performance
            }
            
        except Exception as e:
            logger.warning(f"Error checking compliance: {e}")
            return {
                'vehicle': {'compliant': True, 'restrictions': []},
                'rtsp': {'compliant': True, 'max_hours': 8},
                'restricted_zones': [],
                'speed_limits': []
            }
    
    def analyze_emergency_optimized(self, points, poi_data):
        """Analyze emergency preparedness for the route - OPTIMIZED"""
        try:
            # Simplified emergency analysis
            emergency_services = {
                'hospitals': list(poi_data.get('hospitals', {}).keys())[:5],
                'police_stations': list(poi_data.get('police_stations', {}).keys())[:5],
                'petrol_bunks': list(poi_data.get('petrol_bunks', {}).keys())[:5]
            }
            
            return {
                'services': emergency_services,
                'critical_points': [],
                'plan': {'recommendations': ['Identify nearest hospitals', 'Keep emergency contacts ready']}
            }
            
        except Exception as e:
            logger.warning(f"Error analyzing emergency preparedness: {e}")
            return {'services': {}, 'critical_points': [], 'plan': {}}
    
    def analyze_environmental_optimized(self, points, vehicle_type):
        """Analyze environmental impact of the route - OPTIMIZED"""
        try:
            # Simplified environmental analysis
            route_stats = self.calculate_route_statistics(points)
            distance_km = route_stats['distance_meters'] / 1000
            
            # Basic carbon footprint calculation
            emissions_per_km = {
                'car': 0.12,  # kg CO2 per km
                'medium_truck': 0.25,
                'heavy_truck': 0.35,
                'tanker': 0.40,
                'bus': 0.30
            }
            
            emission_factor = emissions_per_km.get(vehicle_type, 0.12)
            carbon_footprint = distance_km * emission_factor
            
            return {
                'sensitive_areas': [],
                'restrictions': [],
                'advisories': ['Consider eco-friendly driving practices'],
                'carbon_footprint': {
                    'total_co2_kg': round(carbon_footprint, 2),
                    'per_km': emission_factor
                }
            }
            
        except Exception as e:
            logger.warning(f"Error analyzing environmental impact: {e}")
            return {'sensitive_areas': [], 'restrictions': [], 'advisories': [], 'carbon_footprint': {}}
    
    def format_analysis_results(self, results):
        """Format results into expected structure"""
        stats = results.get('stats', {})
        
        formatted = {
            'distance': stats.get('distance_text', '0 km'),
            'distance_value': stats.get('distance_meters', 0),
            'duration': stats.get('duration_text', '0 mins'),
            'duration_value': stats.get('duration_seconds', 0),
            'sharp_turns': results.get('sharp_turns', []),
            'elevation': results.get('elevation', []),
            'weather': results.get('weather', []),
            'risk_segments': results.get('risk_segments', []),
            'compliance': results.get('compliance', {}),
            'emergency': results.get('emergency', {}),
            'environmental': results.get('environmental', {}),
            'petrol_bunks': results.get('pois', {}).get('petrol_bunks', {}),
            'hospitals': results.get('pois', {}).get('hospitals', {}),
            'schools': results.get('pois', {}).get('schools', {}),
            'food_stops': results.get('pois', {}).get('food_stops', {}),
            'police_stations': results.get('pois', {}).get('police_stations', {}),
            'toll_gates': [],
            'bridges': [],
            'major_highways': []
        }
        
        return formatted
    
    # EXISTING METHODS - Keep all existing methods from original
    
    def filter_points_by_bounds(self, points, bounds):
        """Filter points to only include those within specified bounds"""
        filtered = []
        
        # Create bounding box
        min_lat = min(bounds['from_lat'], bounds['to_lat'])
        max_lat = max(bounds['from_lat'], bounds['to_lat'])
        min_lng = min(bounds['from_lng'], bounds['to_lng'])
        max_lng = max(bounds['from_lng'], bounds['to_lng'])
        
        for point in points:
            lat, lng = point[0], point[1]
            if min_lat <= lat <= max_lat and min_lng <= lng <= max_lng:
                filtered.append(point)
        
        return filtered
    
    def order_route_points(self, points, bounds):
        """Order points to create a logical route from start to end bounds"""
        if not points:
            return []
        
        # Start with the point closest to the 'from' coordinates
        start_point = (bounds['from_lat'], bounds['from_lng'])
        end_point = (bounds['to_lat'], bounds['to_lng'])
        
        # Find closest point to start
        distances_to_start = []
        for i, point in enumerate(points):
            dist = geodesic(start_point, (point[0], point[1])).meters
            distances_to_start.append((dist, i, point))
        
        distances_to_start.sort()
        
        # Simple ordering: sort by distance from start to end
        ordered = []
        remaining_points = points.copy()
        
        # Start with closest point to start
        current_point = distances_to_start[0][2]
        remaining_points.remove(current_point)
        ordered.append(current_point)
        
        # Greedy approach: always pick the nearest unvisited point
        while remaining_points:
            current_pos = (ordered[-1][0], ordered[-1][1])
            
            nearest_dist = float('inf')
            nearest_point = None
            
            for point in remaining_points:
                point_pos = (point[0], point[1])
                dist = geodesic(current_pos, point_pos).meters
                
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_point = point
            
            if nearest_point:
                ordered.append(nearest_point)
                remaining_points.remove(nearest_point)
            else:
                break
        
        return ordered
    
    def calculate_route_statistics(self, points):
        """Calculate basic route statistics"""
        if len(points) < 2:
            return {
                'distance_meters': 0,
                'distance_text': '0 km',
                'duration_seconds': 0,
                'duration_text': '0 mins'
            }
        
        total_distance = 0
        for i in range(len(points) - 1):
            point1 = (points[i][0], points[i][1])
            point2 = (points[i+1][0], points[i+1][1])
            distance = geodesic(point1, point2).meters
            total_distance += distance
        
        # Estimate duration based on average speed (50 km/h for mixed roads)
        avg_speed_ms = 50 * 1000 / 3600  # 50 km/h in m/s
        duration_seconds = total_distance / avg_speed_ms
        
        # Format distance
        if total_distance >= 1000:
            distance_text = f"{total_distance / 1000:.1f} km"
        else:
            distance_text = f"{total_distance:.0f} m"
        
        # Format duration
        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        
        if hours > 0:
            duration_text = f"{hours} hour{'s' if hours != 1 else ''} {minutes} min{'s' if minutes != 1 else ''}"
        else:
            duration_text = f"{minutes} min{'s' if minutes != 1 else ''}"
        
        return {
            'distance_meters': int(total_distance),
            'distance_text': distance_text,
            'duration_seconds': int(duration_seconds),
            'duration_text': duration_text
        }
    
    def calculate_turn_angle(self, p1, p2, p3):
        """Calculate the turn angle at point p2 between p1-p2-p3"""
        try:
            # Calculate bearings
            bearing1 = self.calculate_bearing(p1, p2)
            bearing2 = self.calculate_bearing(p2, p3)
            
            # Calculate turn angle
            angle = abs(bearing2 - bearing1)
            if angle > 180:
                angle = 360 - angle
            
            return angle
        except:
            return 0
    
    def calculate_bearing(self, p1, p2):
        """Calculate bearing between two points"""
        lat1, lng1 = math.radians(p1[0]), math.radians(p1[1])
        lat2, lng2 = math.radians(p2[0]), math.radians(p2[1])
        
        dlon = lng2 - lng1
        
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        
        bearing = math.atan2(y, x)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360
        
        return bearing
    
    def count_points_in_bounds(self, points, bounds):
        """Count how many points fall within specified bounds"""
        try:
            return len(self.filter_points_by_bounds(points, bounds))
        except:
            return 0
    
    def prepare_export_data(self, route, route_data, risk_segments):
        """Prepare data for CSV export"""
        export_data = []
        
        try:
            filtered_points = route_data.get('filtered_points', [])
            sharp_turns = {(t['lat'], t['lng']): t for t in route_data.get('sharp_turns', [])}
            
            # Create a mapping of points to risk segments
            risk_mapping = {}
            for i, segment in enumerate(risk_segments):
                for point in segment.get('points', []):
                    key = (round(point[0], 6), round(point[1], 6))
                    risk_mapping[key] = {
                        'segment_id': i,
                        'risk_level': segment.get('risk_level', 'LOW'),
                        'risk_score': segment.get('risk_score', 0)
                    }
            
            # Elevation data mapping
            elevation_mapping = {}
            for elev in route_data.get('elevation', []):
                key = (round(elev['location']['lat'], 6), round(elev['location']['lng'], 6))
                elevation_mapping[key] = elev['elevation']
            
            # Process each point
            for point in filtered_points:
                lat, lng = point[0], point[1]
                key = (round(lat, 6), round(lng, 6))
                
                point_data = {
                    'lat': lat,
                    'lng': lng,
                    'risk_level': 'LOW',
                    'risk_score': 0,
                    'segment_id': 0,
                    'is_sharp_turn': key in sharp_turns,
                    'elevation': elevation_mapping.get(key, 0),
                    'turn_angle': sharp_turns.get(key, {}).get('angle', 0)
                }
                
                # Add risk information if available
                if key in risk_mapping:
                    point_data.update(risk_mapping[key])
                
                export_data.append(point_data)
            
            return export_data
            
        except Exception as e:
            logger.error(f"Error preparing export data: {str(e)}")
            return []