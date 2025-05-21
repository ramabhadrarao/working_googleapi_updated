from flask import Blueprint, render_template, abort, current_app, jsonify, request
from flask_login import login_required, current_user
from models import Route
import json

# Create blueprint
risk_bp = Blueprint('risk_bp', __name__)

@risk_bp.route('/<int:route_id>')
@login_required
def risk_analysis(route_id):
    """Display risk analysis for a specific route."""
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
        
    # Get risk analysis data
    risk_segments = route.get_risk_analysis()
    
    # Calculate risk statistics
    high_risk_count = len([s for s in risk_segments if s.get('risk_level') == 'HIGH'])
    medium_risk_count = len([s for s in risk_segments if s.get('risk_level') == 'MEDIUM'])
    low_risk_count = len([s for s in risk_segments if s.get('risk_level') == 'LOW'])
    
    # Calculate overall risk level
    if high_risk_count > 0:
        overall_risk = 'HIGH'
        risk_color = 'danger'
    elif medium_risk_count > 0:
        overall_risk = 'MEDIUM'
        risk_color = 'warning'
    else:
        overall_risk = 'LOW'
        risk_color = 'success'
    
    # Prepare data for the view
    risk_data = {
        'segments': risk_segments,
        'summary': {
            'high_count': high_risk_count,
            'medium_count': medium_risk_count,
            'low_count': low_risk_count,
            'overall_risk': overall_risk,
            'risk_color': risk_color,
            'total_segments': len(risk_segments)
        }
    }
    
    return render_template(
        'analysis/risk.html',
        route=route,
        data=route_data,
        risk_data=risk_data,
        title="Risk Analysis"
    )

@risk_bp.route('/ajax/<int:route_id>')
@login_required
def ajax_risk_data(route_id):
    """Get risk analysis data in JSON format for AJAX requests."""
    # Get the route from database
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    
    # Get risk analysis data
    risk_segments = route.get_risk_analysis()
    
    # Calculate risk statistics
    high_risk_count = len([s for s in risk_segments if s.get('risk_level') == 'HIGH'])
    medium_risk_count = len([s for s in risk_segments if s.get('risk_level') == 'MEDIUM'])
    low_risk_count = len([s for s in risk_segments if s.get('risk_level') == 'LOW'])
    
    # Calculate overall risk level
    if high_risk_count > 0:
        overall_risk = 'HIGH'
    elif medium_risk_count > 0:
        overall_risk = 'MEDIUM'
    else:
        overall_risk = 'LOW'
    
    # Prepare data for response
    risk_data = {
        'segments': risk_segments,
        'summary': {
            'high_count': high_risk_count,
            'medium_count': medium_risk_count,
            'low_count': low_risk_count,
            'overall_risk': overall_risk,
            'total_segments': len(risk_segments)
        }
    }
    
    return jsonify(risk_data)

@risk_bp.route('/map/<int:route_id>')
@login_required
def risk_map(route_id):
    """Display a map visualization of route risks."""
    # Get the route from database
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        abort(403)  # Forbidden
    
    # Get route data
    route_data = route.get_route_data()
    polyline = json.loads(route.polyline) if route.polyline else []
    
    # Get risk analysis data
    risk_segments = route.get_risk_analysis()
    
    # Import helper function to format risk data for maps
    from utils.risk_analysis import get_risk_map_data
    map_data = get_risk_map_data(risk_segments)
    
    return render_template(
        'analysis/risk_map.html',
        route=route,
        polyline=polyline,
        map_data=map_data,
        api_key=current_app.config['GOOGLE_MAPS_API_KEY'],
        title="Risk Map"
    )

@risk_bp.route('/compare')
@login_required
def compare_routes():
    """Compare risk levels between different routes."""
    # Get all routes for the current user
    routes = Route.query.filter_by(user_id=current_user.id).order_by(Route.created_at.desc()).all()
    
    # Prepare comparison data
    comparison = []
    
    for route in routes:
        risk_segments = route.get_risk_analysis()
        
        # Calculate risk statistics
        high_risk_count = len([s for s in risk_segments if s.get('risk_level') == 'HIGH'])
        medium_risk_count = len([s for s in risk_segments if s.get('risk_level') == 'MEDIUM'])
        low_risk_count = len([s for s in risk_segments if s.get('risk_level') == 'LOW'])
        
        # Calculate overall risk level
        if high_risk_count > 0:
            overall_risk = 'HIGH'
            risk_color = 'danger'
        elif medium_risk_count > 0:
            overall_risk = 'MEDIUM'
            risk_color = 'warning'
        else:
            overall_risk = 'LOW'
            risk_color = 'success'
        
        # Calculate risk percentage
        total_segments = len(risk_segments)
        high_percent = (high_risk_count / total_segments * 100) if total_segments > 0 else 0
        medium_percent = (medium_risk_count / total_segments * 100) if total_segments > 0 else 0
        low_percent = (low_risk_count / total_segments * 100) if total_segments > 0 else 0
        
        comparison.append({
            'id': route.id,
            'name': route.name,
            'from': route.from_address,
            'to': route.to_address,
            'distance': route.distance,
            'risk': {
                'level': overall_risk,
                'color': risk_color,
                'high_count': high_risk_count,
                'medium_count': medium_risk_count,
                'low_count': low_risk_count,
                'high_percent': high_percent,
                'medium_percent': medium_percent,
                'low_percent': low_percent
            }
        })
    
    return render_template(
        'analysis/risk_compare.html',
        routes=comparison,
        title="Compare Route Risks"
    )