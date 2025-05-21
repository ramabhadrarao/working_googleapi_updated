from flask import Blueprint, render_template, abort, current_app
from flask_login import login_required, current_user
from models import Route

# Create blueprint
summary_bp = Blueprint('summary_bp', __name__)

@summary_bp.route('/<int:route_id>')
@login_required
def route_summary(route_id):
    """Display route summary for a specific route."""
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
        
    # Extract data for summary view
    summary_data = {
        'from': route_data.get('from', route.from_address),
        'to': route_data.get('to', route.to_address),
        'distance': route_data.get('distance', route.distance),
        'duration': route_data.get('duration', route.duration),
        'adjusted_duration': route_data.get('adjusted_duration'),
        'vehicle_type': route_data.get('vehicle_type', route.vehicle_type),
        'major_highways': route_data.get('major_highways', []),
        'toll_gates': route_data.get('toll_gates', []),
        'bridges': route_data.get('bridges', []),
        'risk_segments': route_data.get('risk_segments', []),
        'weather': route_data.get('weather', [])
    }
    
    # Extract risk analysis summary
    high_risk_count = len([s for s in summary_data['risk_segments'] if s.get('risk_level') == 'HIGH'])
    medium_risk_count = len([s for s in summary_data['risk_segments'] if s.get('risk_level') == 'MEDIUM'])
    low_risk_count = len([s for s in summary_data['risk_segments'] if s.get('risk_level') == 'LOW'])
    
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
    
    # Add risk summary to the data
    summary_data['risk_summary'] = {
        'high_count': high_risk_count,
        'medium_count': medium_risk_count,
        'low_count': low_risk_count,
        'overall_risk': overall_risk,
        'risk_color': risk_color,
        'total_segments': len(summary_data['risk_segments'])
    }
    
    # Summary of special features
    summary_data['special_features'] = {
        'toll_gates_count': len(summary_data['toll_gates']),
        'bridges_count': len(summary_data['bridges']),
        'sharp_turns_count': route.sharp_turns_count,
        'blind_spots_count': route.blind_spots_count
    }
    
    return render_template(
        'analysis/summary.html',
        route=route,
        data=summary_data,
        title="Route Summary"
    )

@summary_bp.route('/ajax/<int:route_id>')
@login_required
def ajax_summary(route_id):
    """Get route summary data in JSON format for AJAX requests."""
    from flask import jsonify
    
    # Get the route from database
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    
    # Get route data
    route_data = route.get_route_data()
    
    # Check if route data exists
    if not route_data:
        return jsonify({'error': 'Route data not found'}), 404
    
    # Extract summary data
    summary_data = {
        'from': route_data.get('from', route.from_address),
        'to': route_data.get('to', route.to_address),
        'distance': route_data.get('distance', route.distance),
        'duration': route_data.get('duration', route.duration),
        'adjusted_duration': route_data.get('adjusted_duration'),
        'vehicle_type': route_data.get('vehicle_type', route.vehicle_type),
        'major_highways': route_data.get('major_highways', []),
        'risk_level': route.get_risk_analysis()[0].get('risk_level', 'UNKNOWN') if route.get_risk_analysis() else 'UNKNOWN',
        'sharp_turns_count': route.sharp_turns_count,
        'blind_spots_count': route.blind_spots_count,
        'toll_gates_count': len(route_data.get('toll_gates', [])),
        'bridges_count': len(route_data.get('bridges', []))
    }
    
    return jsonify(summary_data)