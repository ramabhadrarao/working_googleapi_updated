from flask import Blueprint, render_template, abort, current_app, jsonify, request
from flask_login import login_required, current_user
from models import Route
from utils.emergency import (
    categorize_emergency_services, 
    find_critical_emergency_points, 
    create_emergency_response_plan,
    generate_emergency_action_cards,
    generate_emergency_map_data
)
import json

# Create blueprint
emergency_bp = Blueprint('emergency_bp', __name__)

@emergency_bp.route('/<int:route_id>')
@login_required
def emergency_analysis(route_id):
    """Display emergency response analysis for a specific route."""
    # Get the route from database
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        abort(403)  # Forbidden
    
    # Get route data
    route_data = route.get_route_data()
    
    # Check if route data exists
    if not route_data:
        abort(404)  # Not Found
        
    # Extract emergency data or generate if needed
    emergency_data = {}
    
    if 'emergency' in route_data:
        emergency_data = route_data['emergency']
    else:
        try:
            # Get emergency services data
            hospitals = route_data.get('hospitals', {})
            police_stations = route_data.get('police_stations', {})
            petrol_bunks = route_data.get('petrol_bunks', {})
            
            # Categorize services
            emergency_services = categorize_emergency_services(
                hospitals, police_stations, petrol_bunks
            )
            
            # Get polyline
            polyline = json.loads(route.polyline) if route.polyline else []
            
            # Find critical emergency points
            critical_points = find_critical_emergency_points(
                polyline, emergency_services
            )
            
            # Get risk segments for emergency plan
            risk_segments = route.get_risk_analysis()
            
            # Create emergency response plan
            emergency_plan = create_emergency_response_plan(
                polyline, emergency_services, risk_segments
            )
            
            # Combine data
            emergency_data = {
                'services': emergency_services,
                'critical_points': critical_points,
                'plan': emergency_plan
            }
        except Exception as e:
            current_app.logger.error(f"Error processing emergency data: {e}")
            # Initialize with empty data
            emergency_data = {
                'services': {},
                'critical_points': [],
                'plan': {}
            }
    
    # Generate action cards based on vehicle type and risk level
    try:
        vehicle_type = route.vehicle_type
        risk_level = "LOW"
        risk_segments = route.get_risk_analysis()
        
        if risk_segments:
            high_risk_count = len([s for s in risk_segments if s.get('risk_level') == 'HIGH'])
            medium_risk_count = len([s for s in risk_segments if s.get('risk_level') == 'MEDIUM'])
            
            if high_risk_count > 0:
                risk_level = "HIGH"
            elif medium_risk_count > 0:
                risk_level = "MEDIUM"
        
        action_cards = generate_emergency_action_cards(
            emergency_data.get('services', {}), vehicle_type, risk_level
        )
    except Exception as e:
        current_app.logger.error(f"Error generating action cards: {e}")
        action_cards = []
    
    return render_template(
        'analysis/emergency.html',
        route=route,
        data=route_data,
        emergency=emergency_data,
        action_cards=action_cards,
        title="Emergency Preparedness"
    )

@emergency_bp.route('/map/<int:route_id>')
@login_required
def emergency_map(route_id):
    """Display a map of emergency services and critical points."""
    # Get the route from database
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        abort(403)  # Forbidden
    
    # Get route data
    route_data = route.get_route_data()
    polyline = json.loads(route.polyline) if route.polyline else []
    
    # Get emergency data
    emergency_data = {}
    
    if 'emergency' in route_data:
        emergency_data = route_data['emergency']
    else:
        try:
            # Get emergency services data
            hospitals = route_data.get('hospitals', {})
            police_stations = route_data.get('police_stations', {})
            petrol_bunks = route_data.get('petrol_bunks', {})
            
            # Categorize services
            emergency_services = categorize_emergency_services(
                hospitals, police_stations, petrol_bunks
            )
            
            # Find critical emergency points
            critical_points = find_critical_emergency_points(
                polyline, emergency_services
            )
            
            emergency_data = {
                'services': emergency_services,
                'critical_points': critical_points
            }
        except Exception as e:
            current_app.logger.error(f"Error processing emergency data: {e}")
            emergency_data = {
                'services': {},
                'critical_points': []
            }
    
    # Generate map data
    try:
        map_data = generate_emergency_map_data(
            polyline, 
            emergency_data.get('services', {}),
            emergency_data.get('critical_points', [])
        )
    except Exception as e:
        current_app.logger.error(f"Error generating map data: {e}")
        map_data = {
            'hospitals': [],
            'police_stations': [],
            'fuel_stations': [],
            'critical_points': []
        }
    
    return render_template(
        'analysis/emergency_map.html',
        route=route,
        polyline=polyline,
        emergency=emergency_data,
        map_data=map_data,
        api_key=current_app.config['GOOGLE_MAPS_API_KEY'],
        title="Emergency Services Map"
    )

@emergency_bp.route('/action-cards/<int:route_id>')
@login_required
def action_cards(route_id):
    """Generate emergency action cards for a route."""
    # Get the route from database
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    
    # Get route data
    route_data = route.get_route_data()
    
    if not route_data:
        return jsonify({'error': 'Route data not found'}), 404
    
    # Get emergency services data
    emergency_data = route_data.get('emergency', {})
    emergency_services = emergency_data.get('services', {})
    
    if not emergency_services:
        # Try to generate emergency services data
        hospitals = route_data.get('hospitals', {})
        police_stations = route_data.get('police_stations', {})
        petrol_bunks = route_data.get('petrol_bunks', {})
        
        emergency_services = categorize_emergency_services(
            hospitals, police_stations, petrol_bunks
        )
    
    # Determine route risk level
    risk_level = "LOW"
    risk_segments = route.get_risk_analysis()
    
    if risk_segments:
        high_risk_count = len([s for s in risk_segments if s.get('risk_level') == 'HIGH'])
        medium_risk_count = len([s for s in risk_segments if s.get('risk_level') == 'MEDIUM'])
        
        if high_risk_count > 0:
            risk_level = "HIGH"
        elif medium_risk_count > 0:
            risk_level = "MEDIUM"
    
    # Generate action cards
    try:
        action_cards = generate_emergency_action_cards(
            emergency_services, route.vehicle_type, risk_level
        )
        
        return jsonify({
            'route_id': route.id,
            'vehicle_type': route.vehicle_type,
            'risk_level': risk_level,
            'action_cards': action_cards
        })
    except Exception as e:
        current_app.logger.error(f"Error generating action cards: {e}")
        return jsonify({'error': str(e)}), 500

@emergency_bp.route('/contacts/<int:route_id>')
@login_required
def emergency_contacts(route_id):
    """View emergency contacts for a route."""
    # Get the route from database
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        abort(403)  # Forbidden
    
    # Get route data
    route_data = route.get_route_data()
    
    # Check if route data exists
    if not route_data:
        abort(404)  # Not Found
    
    # Get emergency data
    emergency_data = route_data.get('emergency', {})
    emergency_plan = emergency_data.get('plan', {})
    
    # Get contacts
    contacts = emergency_plan.get('emergency_contacts', [])
    
    # Sort contacts by priority
    contacts.sort(key=lambda x: x.get('priority', 999))
    
    return render_template(
        'analysis/emergency_contacts.html',
        route=route,
        contacts=contacts,
        title="Emergency Contacts"
    )