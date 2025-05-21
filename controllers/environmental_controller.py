from flask import Blueprint, render_template, abort, current_app, jsonify, request
from flask_login import login_required, current_user
from models import Route
from utils.environmental import EnvironmentalAnalyzer
import json

# Create blueprint
environmental_bp = Blueprint('environmental_bp', __name__)

# Initialize environmental analyzer
environmental_analyzer = EnvironmentalAnalyzer()

@environmental_bp.route('/<int:route_id>')
@login_required
def environmental_analysis(route_id):
    """Display environmental analysis for a specific route."""
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
        
    # Extract environmental data or generate if needed
    environmental_data = {}
    
    if 'environmental' in route_data:
        environmental_data = route_data['environmental']
    else:
        try:
            # Get polyline
            polyline = json.loads(route.polyline) if route.polyline else []
            
            # Check for sensitive zones
            sensitive_areas = environmental_analyzer.check_sensitive_zones(polyline)
            
            # Get environmental restrictions
            environmental_restrictions = environmental_analyzer.get_environmental_restrictions(sensitive_areas)
            
            # Generate environmental advisories
            environmental_advisories = environmental_analyzer.generate_environmental_advisories(
                sensitive_areas, route.vehicle_type
            )
            
            # Calculate carbon footprint
            if route.distance_value:
                carbon_footprint = environmental_analyzer.calculate_carbon_footprint(
                    route.distance_value / 1000,  # Convert meters to km
                    route.vehicle_type
                )
            else:
                carbon_footprint = None
            
            # Combine data
            environmental_data = {
                'sensitive_areas': sensitive_areas,
                'restrictions': environmental_restrictions,
                'advisories': environmental_advisories,
                'carbon_footprint': carbon_footprint
            }
        except Exception as e:
            current_app.logger.error(f"Error processing environmental data: {e}")
            # Initialize with empty data
            environmental_data = {
                'sensitive_areas': [],
                'restrictions': [],
                'advisories': []
            }
    
    # Generate eco-driving tips
    try:
        eco_driving_tips = environmental_analyzer.generate_eco_driving_tips(
            route_data, route.vehicle_type
        )
    except Exception as e:
        current_app.logger.error(f"Error generating eco-driving tips: {e}")
        eco_driving_tips = []
    
    # Calculate environmental impact ranking
    try:
        impact_ranking = environmental_analyzer.rank_route_environmental_impact(
            route.distance_value / 1000 if route.distance_value else 0,
            environmental_data.get('sensitive_areas', []),
            route.vehicle_type
        )
    except Exception as e:
        current_app.logger.error(f"Error calculating environmental impact: {e}")
        impact_ranking = 3  # Default medium impact
    
    return render_template(
        'analysis/environmental.html',
        route=route,
        data=route_data,
        environmental=environmental_data,
        eco_driving_tips=eco_driving_tips,
        impact_ranking=impact_ranking,
        title="Environmental Analysis"
    )

@environmental_bp.route('/map/<int:route_id>')
@login_required
def environmental_map(route_id):
    """Display a map of environmentally sensitive areas."""
    # Get the route from database
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        abort(403)  # Forbidden
    
    # Get route data
    route_data = route.get_route_data()
    polyline = json.loads(route.polyline) if route.polyline else []
    
    # Get environmental data
    environmental_data = {}
    sensitive_areas = []
    
    if 'environmental' in route_data and 'sensitive_areas' in route_data['environmental']:
        sensitive_areas = route_data['environmental']['sensitive_areas']
    else:
        try:
            sensitive_areas = environmental_analyzer.check_sensitive_zones(polyline)
        except Exception as e:
            current_app.logger.error(f"Error checking sensitive zones: {e}")
    
    return render_template(
        'analysis/environmental_map.html',
        route=route,
        polyline=polyline,
        sensitive_areas=sensitive_areas,
        api_key=current_app.config['GOOGLE_MAPS_API_KEY'],
        title="Environmental Zones Map"
    )

@environmental_bp.route('/carbon-footprint/<int:route_id>')
@login_required
def carbon_footprint(route_id):
    """Calculate carbon footprint for a route."""
    # Get the route from database
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    
    if not route.distance_value:
        return jsonify({'error': 'Route distance not available'}), 400
    
    # Calculate carbon footprint
    try:
        carbon_footprint = environmental_analyzer.calculate_carbon_footprint(
            route.distance_value / 1000,  # Convert meters to km
            route.vehicle_type
        )
        
        return jsonify({
            'route_id': route.id,
            'vehicle_type': route.vehicle_type,
            'distance_km': route.distance_value / 1000,
            'carbon_footprint': carbon_footprint
        })
    except Exception as e:
        current_app.logger.error(f"Error calculating carbon footprint: {e}")
        return jsonify({'error': str(e)}), 500

@environmental_bp.route('/eco-driving-tips/<int:route_id>')
@login_required
def eco_driving_tips(route_id):
    """Get eco-driving tips for a route."""
    # Get the route from database
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    
    # Get route data
    route_data = route.get_route_data()
    
    if not route_data:
        return jsonify({'error': 'Route data not found'}), 404
    
    # Generate eco-driving tips
    try:
        tips = environmental_analyzer.generate_eco_driving_tips(
            route_data, route.vehicle_type
        )
        
        return jsonify({
            'route_id': route.id,
            'vehicle_type': route.vehicle_type,
            'eco_driving_tips': tips
        })
    except Exception as e:
        current_app.logger.error(f"Error generating eco-driving tips: {e}")
        return jsonify({'error': str(e)}), 500

@environmental_bp.route('/compare')
@login_required
def compare_environmental_impact():
    """Compare environmental impact of different routes."""
    # Get all routes for the current user
    routes = Route.query.filter_by(user_id=current_user.id).order_by(Route.created_at.desc()).all()
    
    # Prepare comparison data
    comparison = []
    
    for route in routes:
        route_data = route.get_route_data()
        
        # Get environmental data
        environmental_data = route_data.get('environmental', {})
        sensitive_areas = environmental_data.get('sensitive_areas', [])
        
        # Calculate environmental impact ranking
        try:
            impact_ranking = environmental_analyzer.rank_route_environmental_impact(
                route.distance_value / 1000 if route.distance_value else 0,
                sensitive_areas,
                route.vehicle_type
            )
        except Exception as e:
            current_app.logger.error(f"Error calculating environmental impact: {e}")
            impact_ranking = 3  # Default medium impact
        
        # Calculate carbon footprint
        try:
            carbon_footprint = None
            if route.distance_value:
                carbon_footprint = environmental_analyzer.calculate_carbon_footprint(
                    route.distance_value / 1000,  # Convert meters to km
                    route.vehicle_type
                )
        except Exception as e:
            current_app.logger.error(f"Error calculating carbon footprint: {e}")
            carbon_footprint = None
        
        comparison.append({
            'id': route.id,
            'name': route.name,
            'from': route.from_address,
            'to': route.to_address,
            'distance': route.distance,
            'vehicle_type': route.vehicle_type,
            'environmental': {
                'impact_ranking': impact_ranking,
                'impact_level': 'High' if impact_ranking > 3 else ('Medium' if impact_ranking > 2 else 'Low'),
                'sensitive_areas_count': len(sensitive_areas),
                'carbon_footprint': carbon_footprint
            }
        })
    
    return render_template(
        'analysis/environmental_compare.html',
        routes=comparison,
        title="Compare Environmental Impact"
    )