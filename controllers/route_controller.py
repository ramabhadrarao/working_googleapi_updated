import os
import json
import googlemaps
import polyline
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, RadioField, FloatField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange
from models import db, Route
import math  # Add this import to fix the error

# Import utility modules
from utils.risk_analysis import calculate_route_risk, get_risk_map_data, get_vehicle_adjusted_time
from utils.compliance import ComplianceChecker
from utils.emergency import categorize_emergency_services, find_critical_emergency_points, create_emergency_response_plan
from utils.environmental import EnvironmentalAnalyzer
from utils.elevation import get_elevation_data

# Create blueprint
route_bp = Blueprint('route_bp', __name__)

# Initialize services
compliance_checker = ComplianceChecker()
environmental_analyzer = EnvironmentalAnalyzer()

# Define forms
class RouteForm(FlaskForm):
    """Form for route input."""
    input_type = RadioField('Input Type', choices=[
        ('address', 'Use Address'),
        ('coordinates', 'Use Coordinates')
    ], default='address')
    
    # Address fields
    from_address = StringField('From Address')
    to_address = StringField('To Address')
    
    # Coordinate fields
    from_lat = FloatField('From Latitude', validators=[Optional(), NumberRange(-90, 90)])
    from_lng = FloatField('From Longitude', validators=[Optional(), NumberRange(-180, 180)])
    to_lat = FloatField('To Latitude', validators=[Optional(), NumberRange(-90, 90)])
    to_lng = FloatField('To Longitude', validators=[Optional(), NumberRange(-180, 180)])
    
    # Common fields
    vehicle_type = SelectField('Vehicle Type', choices=[
        ('car', 'Car'),
        ('medium_truck', 'Medium Truck'),
        ('heavy_truck', 'Heavy Truck'),
        ('tanker', 'Tanker'),
        ('bus', 'Bus')
    ], default='car')
    
    submit = SubmitField('Analyze Route')
    
    def validate(self, *args, **kwargs):
        """Custom validation to ensure either address or coordinates are provided."""
        # First, run the parent class's validate method with all arguments
        if not super().validate(*args, **kwargs):
            return False
            
        if self.input_type.data == 'address':
            if not self.from_address.data or not self.to_address.data:
                flash('From and To addresses are required when using address input.', 'danger')
                return False
        else:  # coordinates
            if not all([self.from_lat.data, self.from_lng.data, self.to_lat.data, self.to_lng.data]):
                flash('All coordinate fields are required when using coordinate input.', 'danger')
                return False
                
        return True
    
# Helper functions
def get_gmaps_client():
    """Get a Google Maps client instance."""
    api_key = current_app.config['GOOGLE_MAPS_API_KEY']
    return googlemaps.Client(key=api_key)

def format_places_data(places_dict):
    """Format places data for storage in database."""
    formatted = {}
    for category, places in places_dict.items():
        formatted[category] = {place['name']: place['vicinity'] for place in places}
    return formatted

def get_weather_for_route_points(gmaps_polyline, api_key):
    """Get weather data for points along the route."""
    import requests
    sampled = gmaps_polyline[::30]  # Sample every 30th point
    weather_info = []
    
    for lat, lng in sampled:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={api_key}&units=metric"
        try:
            r = requests.get(url)
            if r.status_code == 200:
                data = r.json()
                weather_info.append({
                    "icon": data['weather'][0]['icon'],
                    "lat": lat,
                    "lng": lng,
                    "location": data.get("name", f"{lat},{lng}"),
                    "temp": data['main']['temp'],
                    "description": data['weather'][0]['description']
                })
        except Exception as e:
            current_app.logger.error(f"Weather fetch error: {e}")
    
    return weather_info

def angle_between(p1, p2, p3):
    """Calculate angle between three points."""
    import math
    def bearing(p, q):
        return math.atan2(q[1] - p[1], q[0] - p[0])
    return abs(bearing(p1, p2) - bearing(p2, p3))

def find_sharp_turns(poly):
    """Find sharp turns in the route polyline."""
    sharp_turns = []
    for i in range(1, len(poly) - 1):
        angle = angle_between(poly[i - 1], poly[i], poly[i + 1])
        if angle > 0.5:  # ~30 degrees
            sharp_turns.append({
                'lat': poly[i][0], 
                'lng': poly[i][1], 
                'angle': round(math.degrees(angle), 2)
            })
    return sharp_turns

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula."""
    from math import radians, cos, sin, asin, sqrt
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return 6371 * c  # km

def get_major_highways(route_legs):
    """Extract major highways from route steps."""
    highways = []
    
    for step in route_legs.get('steps', []):
        html_instructions = step.get('html_instructions', '')
        
        # Look for highway mentions in directions
        highway_keywords = ['NH', 'National Highway', 'SH', 'State Highway', 'Expressway']
        
        for keyword in highway_keywords:
            if keyword in html_instructions:
                # Extract the highway name/number if possible
                parts = html_instructions.split(keyword)
                if len(parts) > 1:
                    # Try to extract the highway number
                    try:
                        highway_name = parts[1].split('<')[0].strip()
                        if highway_name:
                            highways.append(f"{keyword} {highway_name}")
                        else:
                            highways.append(keyword)
                    except:
                        highways.append(keyword)
                else:
                    highways.append(keyword)
    
    # Remove duplicates while preserving order
    unique_highways = []
    for highway in highways:
        if highway not in unique_highways:
            unique_highways.append(highway)
    
    return unique_highways

def detect_toll_gates(route_data, gmaps):
    """Detect toll gates along the route."""
    toll_gates = []
    
    # Check for toll information from Google Directions API
    if 'routes' in route_data and len(route_data['routes']) > 0:
        for route in route_data['routes']:
            if 'legs' in route:
                for leg in route['legs']:
                    if 'steps' in leg:
                        for step in leg['steps']:
                            html_instructions = step.get('html_instructions', '')
                            if 'toll' in html_instructions.lower():
                                start_loc = step.get('start_location', {})
                                toll_gates.append({
                                    'lat': start_loc.get('lat'),
                                    'lng': start_loc.get('lng'),
                                    'name': 'Toll Gate',
                                    'source': 'directions'
                                })
    
    return toll_gates

def detect_bridges(route_data, gmaps):
    """Detect bridges along the route."""
    bridges = []
    
    # Check for bridge information from Google Directions API
    if 'routes' in route_data and len(route_data['routes']) > 0:
        for route in route_data['routes']:
            if 'legs' in route:
                for leg in route['legs']:
                    if 'steps' in leg:
                        for step in leg['steps']:
                            html_instructions = step.get('html_instructions', '')
                            if 'bridge' in html_instructions.lower():
                                start_loc = step.get('start_location', {})
                                bridges.append({
                                    'lat': start_loc.get('lat'),
                                    'lng': start_loc.get('lng'),
                                    'name': 'Bridge',
                                    'source': 'directions'
                                })
    
    return bridges

def get_alternative_routes(gmaps, origin, destination, vehicle_type):
    """Get alternative routes for the journey."""
    try:
        # Request alternative routes from Google Directions API
        alternatives = gmaps.directions(
            origin=origin,
            destination=destination,
            mode="driving",
            alternatives=True  # Request alternative routes
        )
        
        processed_routes = []
        
        for i, route in enumerate(alternatives):
            route_info = {
                'id': i,
                'summary': route.get('summary', f'Route {i+1}'),
                'distance': route['legs'][0]['distance']['text'],
                'distance_value': route['legs'][0]['distance']['value'],
                'duration': route['legs'][0]['duration']['text'],
                'duration_value': route['legs'][0]['duration']['value'],
                'polyline': polyline.decode(route['overview_polyline']['points']),
                'waypoints': [],  # Key points along the route
                'is_toll': any('toll' in leg.get('html_instructions', '').lower() for step in route['legs'] for leg in step.get('steps', [])),
                'highways': []  # Major highways
            }
            
            # Get adjusted time for vehicle
            if vehicle_type != 'car':
                adjusted_time = get_vehicle_adjusted_time(route['legs'][0]['duration'], vehicle_type)
                route_info['adjusted_duration'] = adjusted_time.get('adjusted_text')
                route_info['adjusted_duration_value'] = adjusted_time.get('adjusted_value')
            
            # Extract waypoints (major turning points)
            if 'legs' in route and len(route['legs']) > 0:
                for leg in route['legs']:
                    if 'steps' in leg:
                        steps = leg['steps']
                        major_steps = []
                        
                        # Get significant turning points
                        for step in steps:
                            if 'maneuver' in step:
                                major_steps.append({
                                    'lat': step['start_location']['lat'],
                                    'lng': step['start_location']['lng'],
                                    'instruction': step.get('html_instructions', '')
                                })
                        
                        route_info['waypoints'] = major_steps
            
            # Extract major highways
            if 'legs' in route and len(route['legs']) > 0:
                for leg in route['legs']:
                    route_info['highways'] = get_major_highways(leg)
            
            processed_routes.append(route_info)
        
        # Sort routes by duration (fastest first)
        processed_routes.sort(key=lambda x: x['duration_value'])
        
        return processed_routes
    
    except Exception as e:
        current_app.logger.error(f"Error getting alternative routes: {e}")
        return []

# Routes
@route_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """Main route input page."""
    form = RouteForm()
    data = {}
    map_data = {}
    
    if form.validate_on_submit():
        # Determine if using address or coordinates
        if form.input_type.data == 'address':
            from_address = form.from_address.data
            to_address = form.to_address.data
            origin = from_address
            destination = to_address
        else:  # coordinates
            from_lat = form.from_lat.data
            from_lng = form.from_lng.data
            to_lat = form.to_lat.data
            to_lng = form.to_lng.data
            from_address = f"{from_lat},{from_lng}"
            to_address = f"{to_lat},{to_lng}"
            origin = {'lat': from_lat, 'lng': from_lng}
            destination = {'lat': to_lat, 'lng': to_lng}
        
        vehicle_type = form.vehicle_type.data
        
        # Initialize Google Maps client
        try:
            gmaps = get_gmaps_client()
            
            # Get directions
            directions = gmaps.directions(origin, destination, mode="driving")
            
            if directions:
                # Get basic route information
                route = directions[0]['legs'][0]
                distance = route['distance']['text']
                distance_value = route['distance']['value']
                duration = route['duration']['text']
                duration_value = route['duration']['value']
                
                # Decode the polyline
                poly = polyline.decode(directions[0]['overview_polyline']['points'])
                
                # Calculate sharp turns
                sharp_turns = find_sharp_turns(poly)
                
                # Sample points for POI search
                sample_points = poly[::30]  # reduced sampling
                
                # Define POI categories
                categories = {
                    'petrol': 'gas_station',
                    'hospital': 'hospital',
                    'school': 'school',
                    'food': 'restaurant',
                    'police': 'police'
                }
                
                # Initialize places data
                places_data = {key: [] for key in categories}
                seen_places = {key: set() for key in categories}
                
                # Filter function for places
                def filter_places(results, key):
                    filtered = []
                    for r in results.get('results', []):
                        if 'geometry' not in r or 'name' not in r:
                            continue
                        name = r['name']
                        loc = r['geometry']['location']
                        place_id = r.get('place_id') or name
                        if place_id not in seen_places[key]:
                            if any(haversine(lat, lng, loc['lat'], loc['lng']) < 5 for lat, lng in poly):
                                r['latlng'] = loc
                                filtered.append(r)
                                seen_places[key].add(place_id)
                    return filtered
                
                # Fetch POIs for each category
                for lat, lng in sample_points:
                    for key, gtype in categories.items():
                        try:
                            res = gmaps.places_nearby(location=(lat, lng), radius=1000, type=gtype)
                            places_data[key] += filter_places(res, key)
                        except Exception as e:
                            current_app.logger.error(f"Failed fetching {key} at ({lat}, {lng}): {e}")
                
                # Get elevation data
                elevation_data = get_elevation_data(gmaps, poly)
                
                # Get weather data
                api_key = current_app.config['OPENWEATHER_API_KEY']
                weather_data = get_weather_for_route_points(poly, api_key)
                
                # Risk analysis
                try:
                    risk_segments = calculate_route_risk(
                        poly, sharp_turns, elevation_data, weather_data, gmaps, current_app.config['GOOGLE_MAPS_API_KEY']
                    )
                    risk_map_data = get_risk_map_data(risk_segments)
                except Exception as e:
                    current_app.logger.error(f"Error in risk analysis: {e}")
                    risk_segments = []
                    risk_map_data = []
                
                # Get adjusted travel time for heavy vehicles
                try:
                    adjusted_time = get_vehicle_adjusted_time(route['duration'], vehicle_type)
                except Exception as e:
                    current_app.logger.error(f"Error calculating adjusted time: {e}")
                    adjusted_time = {"adjusted_text": None, "adjusted_value": None}
                
                # Extract major highways
                try:
                    major_highways = get_major_highways(route)
                except Exception as e:
                    current_app.logger.error(f"Error extracting highways: {e}")
                    major_highways = []
                
                # Check regulatory compliance
                try:
                    compliance_status = compliance_checker.check_vehicle_compliance(vehicle_type)
                    speed_limits = compliance_checker.check_speed_limits(vehicle_type, poly)
                    restricted_zones = compliance_checker.check_restricted_zones(poly)
                    rtsp_compliance = compliance_checker.check_rtsp_compliance(route['duration']['value'])
                except Exception as e:
                    current_app.logger.error(f"Error checking compliance: {e}")
                    compliance_status = {}
                    speed_limits = {}
                    restricted_zones = []
                    rtsp_compliance = {}
                
                # Format places data for POI
                poi_data = {
                    'petrol_bunks': {p['name']: p['vicinity'] for p in places_data['petrol']},
                    'hospitals': {p['name']: p['vicinity'] for p in places_data['hospital']},
                    'schools': {p['name']: p['vicinity'] for p in places_data['school']},
                    'food_stops': {p['name']: p['vicinity'] for p in places_data['food']},
                    'police_stations': {p['name']: p['vicinity'] for p in places_data['police']}
                }
                
                # Emergency services and planning
                try:
                    emergency_services = categorize_emergency_services(
                        poi_data['hospitals'], 
                        poi_data['police_stations'], 
                        poi_data['petrol_bunks']
                    )
                    
                    critical_emergency_points = find_critical_emergency_points(poly, emergency_services)
                    emergency_plan = create_emergency_response_plan(poly, emergency_services, risk_segments)
                except Exception as e:
                    current_app.logger.error(f"Error processing emergency data: {e}")
                    emergency_services = {}
                    critical_emergency_points = []
                    emergency_plan = {}
                
                # Rest stop planning
                try:
                    rest_stop_recommendations = compliance_checker.generate_rest_stop_recommendations(
                        poly, route['duration']['value'], poi_data
                    )
                except Exception as e:
                    current_app.logger.error(f"Error generating rest stops: {e}")
                    rest_stop_recommendations = []
                
                # Environmental analysis
                try:
                    sensitive_areas = environmental_analyzer.check_sensitive_zones(poly)
                    environmental_restrictions = environmental_analyzer.get_environmental_restrictions(sensitive_areas)
                    environmental_advisories = environmental_analyzer.generate_environmental_advisories(
                        sensitive_areas, vehicle_type
                    )
                except Exception as e:
                    current_app.logger.error(f"Error in environmental analysis: {e}")
                    sensitive_areas = []
                    environmental_restrictions = []
                    environmental_advisories = []
                
                # Detect toll gates and bridges
                toll_gates = detect_toll_gates(directions[0], gmaps)
                bridges = detect_bridges(directions[0], gmaps)
                
                # Get alternative routes
                alternative_routes = get_alternative_routes(gmaps, origin, destination, vehicle_type)
                
                # Build data to pass to template
                data = {
                    'from': from_address,
                    'to': to_address,
                    'distance': distance,
                    'distance_value': distance_value,
                    'duration': duration,
                    'duration_value': duration_value,
                    'adjusted_duration': adjusted_time.get('adjusted_text') if vehicle_type != 'car' else None,
                    'vehicle_type': vehicle_type,
                    'major_highways': major_highways,
                    'sharp_turns': sharp_turns,
                    'petrol_bunks': poi_data['petrol_bunks'],
                    'hospitals': poi_data['hospitals'],
                    'schools': poi_data['schools'],
                    'food_stops': poi_data['food_stops'],
                    'police_stations': poi_data['police_stations'],
                    'elevation': elevation_data,
                    'weather': weather_data,
                    
                    # Special features
                    'toll_gates': toll_gates,
                    'bridges': bridges,
                    
                    # Analysis data
                    'risk_segments': risk_segments,
                    'compliance': {
                        'vehicle': compliance_status,
                        'speed_limits': speed_limits,
                        'restricted_zones': restricted_zones,
                        'rtsp': rtsp_compliance
                    },
                    'emergency': {
                        'services': emergency_services,
                        'critical_points': critical_emergency_points,
                        'plan': emergency_plan
                    },
                    'rest_stops': rest_stop_recommendations,
                    'environmental': {
                        'sensitive_areas': sensitive_areas,
                        'restrictions': environmental_restrictions,
                        'advisories': environmental_advisories
                    },
                    'alternative_routes': alternative_routes
                }
                
                map_data = {
                    'polyline': poly, 
                    'sharp_turns': sharp_turns,
                    'risk_segments': risk_map_data,
                    'toll_gates': toll_gates,
                    'bridges': bridges
                }
                
                # Save the route to database
                route_obj = Route(
                    user_id=current_user.id,
                    name=f"Route from {from_address} to {to_address}",
                    from_address=from_address,
                    to_address=to_address,
                    from_lat=poly[0][0] if poly else None,
                    from_lng=poly[0][1] if poly else None,
                    to_lat=poly[-1][0] if poly else None,
                    to_lng=poly[-1][1] if poly else None,
                    distance=distance,
                    distance_value=distance_value,
                    duration=duration,
                    duration_value=duration_value,
                    vehicle_type=vehicle_type,
                    polyline=json.dumps(poly)
                )
                
                # Save all route data
                route_obj.save_route_data(data)
                route_obj.save_risk_analysis(risk_segments)
                
                # Update summary metrics
                route_obj.sharp_turns_count = len(sharp_turns)
                route_obj.blind_spots_count = len([t for t in sharp_turns if t['angle'] > 70])
                
                db.session.add(route_obj)
                db.session.commit()
                
                # Redirect to dashboard view
                return redirect(url_for('route_bp.view', route_id=route_obj.id))
                
        except Exception as e:
            current_app.logger.error(f"Error processing route: {e}")
            # Include an error message to display to the user
            flash(f"Error processing your route: {str(e)}", 'danger')
    
    return render_template(
        "routes/index.html", 
        form=form, 
        data=data, 
        map_data=map_data, 
        api_key=current_app.config['GOOGLE_MAPS_API_KEY'],
        title="Route Analysis"
    )

@route_bp.route('/view/<int:route_id>')
@login_required
def view(route_id):
    """View a saved route."""
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to view this route.', 'danger')
        return redirect(url_for('route_bp.index'))
    
    # Get route data from database
    data = route.get_route_data()
    
    # Prepare map data
    map_data = {
        'polyline': json.loads(route.polyline) if route.polyline else [], 
        'sharp_turns': data.get('sharp_turns', []),
        'risk_segments': get_risk_map_data(route.get_risk_analysis()),
        'toll_gates': data.get('toll_gates', []),
        'bridges': data.get('bridges', [])
    }
    
    return render_template(
        "routes/dashboard.html", 
        route=route,
        data=data, 
        map_data=map_data, 
        api_key=current_app.config['GOOGLE_MAPS_API_KEY'],
        title=f"Route: {route.from_address} to {route.to_address}"
    )

@route_bp.route('/alternative/<int:route_id>')
@login_required
def alternative_routes(route_id):
    """View alternative routes for a saved route."""
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to view this route.', 'danger')
        return redirect(url_for('route_bp.index'))
    
    # Get route data from database
    data = route.get_route_data()
    alternative_routes = data.get('alternative_routes', [])
    
    # Get Google Maps API key
    api_key = current_app.config['GOOGLE_MAPS_API_KEY']
    
    return render_template(
        "routes/alternative_routes.html", 
        route=route,
        alternative_routes=alternative_routes,
        api_key=api_key,
        title=f"Alternative Routes: {route.from_address} to {route.to_address}"
    )

@route_bp.route('/list')
@login_required
def list_routes():
    """List all routes for the current user."""
    routes = Route.query.filter_by(user_id=current_user.id).order_by(Route.created_at.desc()).all()
    return render_template('routes/list.html', routes=routes, title="My Routes")

@route_bp.route('/delete/<int:route_id>', methods=['POST'])
@login_required
def delete(route_id):
    """Delete a route."""
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to delete this route.', 'danger')
        return redirect(url_for('route_bp.list_routes'))
    
    db.session.delete(route)
    db.session.commit()
    
    flash('Route deleted successfully.', 'success')
    return redirect(url_for('route_bp.list_routes'))

@route_bp.route('/blind-spots/<int:route_id>')
@login_required
def blind_spots(route_id):
    """View blind spots (high-angle sharp turns) for a route."""
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to view this route.', 'danger')
        return redirect(url_for('route_bp.index'))
    
    # Get blind spots
    blind_spots = route.get_blind_spots()
    
    # Get polyline for map
    polyline_data = json.loads(route.polyline) if route.polyline else []
    
    return render_template(
        'routes/blind_spots.html',
        route=route,
        blind_spots=blind_spots,
        polyline=polyline_data,
        api_key=current_app.config['GOOGLE_MAPS_API_KEY'],
        title=f"Blind Spots: {route.from_address} to {route.to_address}"
    )