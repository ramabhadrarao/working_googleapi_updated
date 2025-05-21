from flask import Blueprint, render_template, abort, current_app, jsonify, request
from flask_login import login_required, current_user
import json
from models import Route
from utils.compliance import ComplianceChecker

# Create blueprint
compliance_bp = Blueprint('compliance_bp', __name__)

# Initialize compliance checker
compliance_checker = ComplianceChecker()

@compliance_bp.route('/<int:route_id>')
@login_required
def compliance_analysis(route_id):
    """Display compliance analysis for a specific route."""
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
        
    # Get or generate compliance data
    compliance_data = {}
    polyline = []
    
    if 'compliance' in route_data:
        compliance_data = route_data['compliance']
    else:
        # If compliance data not in route_data, generate it now
        try:
            # Get route polyline
            if route.polyline:
                polyline = json.loads(route.polyline)
            
            # Check vehicle compliance
            vehicle_compliance = compliance_checker.check_vehicle_compliance(route.vehicle_type)
            
            # Check speed limits
            speed_limits = compliance_checker.check_speed_limits(route.vehicle_type, polyline)
            
            # Check restricted zones
            restricted_zones = compliance_checker.check_restricted_zones(polyline)
            
            # Check RTSP compliance
            rtsp_compliance = compliance_checker.check_rtsp_compliance(route.duration_value, route.vehicle_type)
            
            # Combine compliance data
            compliance_data = {
                'vehicle': vehicle_compliance,
                'speed_limits': speed_limits,
                'restricted_zones': restricted_zones,
                'rtsp': rtsp_compliance
            }
        except Exception as e:
            current_app.logger.error(f"Error calculating compliance data: {e}")
            # Initialize empty compliance data
            compliance_data = {
                'vehicle': {},
                'speed_limits': {},
                'restricted_zones': [],
                'rtsp': {}
            }
    
    # Generate rest stop recommendations
    rest_stops = []
    
    if 'rest_stops' in route_data:
        rest_stops = route_data['rest_stops']
    else:
        try:
            # Get POI data for rest stops
            poi_data = {
                'petrol_bunks': route_data.get('petrol_bunks', {}),
                'food_stops': route_data.get('food_stops', {})
            }
            
            # Generate rest stop recommendations
            rest_stops = compliance_checker.generate_rest_stop_recommendations(
                polyline, route.duration_value, poi_data, route.vehicle_type
            )
        except Exception as e:
            current_app.logger.error(f"Error generating rest stops: {e}")
    
    return render_template(
        'analysis/compliance.html',
        route=route,
        data=route_data,
        compliance=compliance_data,
        rest_stops=rest_stops,
        title="Regulatory Compliance"
    )

@compliance_bp.route('/vehicle/<vehicle_type>')
@login_required
def vehicle_compliance(vehicle_type):
    """Get compliance requirements for a specific vehicle type."""
    # Validate vehicle type
    valid_vehicle_types = ['car', 'medium_truck', 'heavy_truck', 'tanker', 'bus']
    if vehicle_type not in valid_vehicle_types:
        return jsonify({'error': 'Invalid vehicle type'}), 400
    
    # Get compliance data
    compliance_data = compliance_checker.check_vehicle_compliance(vehicle_type)
    
    return jsonify(compliance_data)

@compliance_bp.route('/rest-stops/<int:route_id>')
@login_required
def rest_stop_recommendations(route_id):
    """Generate rest stop recommendations for a route."""
    # Get the route from database
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    
    # Get route data
    route_data = route.get_route_data()
    
    if not route_data:
        return jsonify({'error': 'Route data not found'}), 404
    
    # Get POI data for rest stops
    poi_data = {
        'petrol_bunks': route_data.get('petrol_bunks', {}),
        'food_stops': route_data.get('food_stops', {})
    }
    
    # Get polyline
    polyline = json.loads(route.polyline) if route.polyline else []
    
    # Generate rest stop recommendations
    try:
        rest_stops = compliance_checker.generate_rest_stop_recommendations(
            polyline, route.duration_value, poi_data, route.vehicle_type
        )
        
        return jsonify({
            'route_id': route.id,
            'vehicle_type': route.vehicle_type,
            'duration': route.duration,
            'rest_stops': rest_stops
        })
    except Exception as e:
        current_app.logger.error(f"Error generating rest stops: {e}")
        return jsonify({'error': str(e)}), 500

@compliance_bp.route('/zones-map/<int:route_id>')
@login_required
def restricted_zones_map(route_id):
    """Display a map of restricted zones along the route."""
    # Get the route from database
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        abort(403)  # Forbidden
    
    # Get route data
    route_data = route.get_route_data()
    polyline = json.loads(route.polyline) if route.polyline else []
    
    # Get restricted zones
    restricted_zones = []
    
    if 'compliance' in route_data and 'restricted_zones' in route_data['compliance']:
        restricted_zones = route_data['compliance']['restricted_zones']
    else:
        try:
            restricted_zones = compliance_checker.check_restricted_zones(polyline)
        except Exception as e:
            current_app.logger.error(f"Error checking restricted zones: {e}")
    
    return render_template(
        'analysis/restricted_zones_map.html',
        route=route,
        polyline=polyline,
        restricted_zones=restricted_zones,
        api_key=current_app.config['GOOGLE_MAPS_API_KEY'],
        title="Restricted Zones Map"
    )