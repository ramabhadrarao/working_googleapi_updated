import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, send_file, redirect, url_for, flash, current_app, abort
from flask_login import login_required, current_user
from models import Route, Report, db
from utils.pdf_generator import generate_pdf

# Create blueprint
report_bp = Blueprint('report_bp', __name__)

@report_bp.route('/generate/<int:route_id>/<report_type>')
@login_required
def generate(route_id, report_type):
    """Generate a PDF report for a route."""
    # Ensure report_type is valid
    valid_types = ['full', 'summary', 'driver_briefing']
    if report_type not in valid_types:
        flash(f"Invalid report type: {report_type}", "danger")
        return redirect(url_for('route_bp.view', route_id=route_id))
    
    # Get the route from database
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        abort(403)  # Forbidden
    
    # Get route data
    route_data = route.get_route_data()
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{report_type}_{timestamp}_{unique_id}.pdf"
    filepath = os.path.join(current_app.config['REPORTS_FOLDER'], filename)
    
    try:
        # Call PDF generation function
        if report_type == 'full':
            generate_pdf(
                filepath,
                route.from_address,
                route.to_address,
                route.distance,
                route.duration,
                route_data.get('sharp_turns', []),
                route_data.get('petrol_bunks', {}),
                route_data.get('hospitals', {}),
                route_data.get('schools', {}),
                route_data.get('food_stops', {}),
                route_data.get('police_stations', {}),
                route_data.get('elevation', []),
                route_data.get('weather', []),
                toll_gates=route_data.get('toll_gates', []),
                bridges=route_data.get('bridges', []),
                risk_segments=route_data.get('risk_segments', []),
                compliance=route_data.get('compliance', {}),
                emergency=route_data.get('emergency', {}),
                environmental=route_data.get('environmental', {}),
                vehicle_type=route.vehicle_type,
                api_key=current_app.config['GOOGLE_MAPS_API_KEY']
            )
        elif report_type == 'summary':
            generate_pdf(
                filepath,
                route.from_address,
                route.to_address,
                route.distance,
                route.duration,
                route_data.get('sharp_turns', []),
                route_data.get('petrol_bunks', {}),
                route_data.get('hospitals', {}),
                type='summary',
                vehicle_type=route.vehicle_type
            )
        elif report_type == 'driver_briefing':
            generate_pdf(
                filepath,
                route.from_address,
                route.to_address,
                route.distance,
                route.duration,
                route_data.get('sharp_turns', []),
                route_data.get('petrol_bunks', {}),
                route_data.get('hospitals', {}),
                route_data.get('schools', {}),
                route_data.get('food_stops', {}),
                route_data.get('police_stations', {}),
                type='driver_briefing',
                risk_segments=route_data.get('risk_segments', []),
                compliance=route_data.get('compliance', {}),
                emergency=route_data.get('emergency', {}),
                toll_gates=route_data.get('toll_gates', []),
                bridges=route_data.get('bridges', []),
                vehicle_type=route.vehicle_type
            )
        
        # Get file size
        file_size = os.path.getsize(filepath)
        
        # Save report in database
        report = Report(
            user_id=current_user.id,
            route_id=route.id,
            filename=filename,
            report_type=report_type,
            file_size=file_size
        )
        
        db.session.add(report)
        db.session.commit()
        
        # Redirect to download
        return redirect(url_for('report_bp.download', report_id=report.id))
        
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {e}")
        flash(f"Error generating PDF: {str(e)}", "danger")
        return redirect(url_for('route_bp.view', route_id=route_id))

@report_bp.route('/download/<int:report_id>')
@login_required
def download(report_id):
    """Download a generated report."""
    # Get report from database
    report = Report.query.get_or_404(report_id)
    
    # Ensure the report belongs to the current user
    if report.user_id != current_user.id and not current_user.is_admin():
        abort(403)  # Forbidden
    
    # Get file path
    filepath = report.get_file_path()
    
    # Check if file exists
    if not os.path.exists(filepath):
        flash("Report file not found.", "danger")
        return redirect(url_for('report_bp.list_reports'))
    
    # Determine report type name
    report_type_names = {
        'full': 'Full Report',
        'summary': 'Summary Report',
        'driver_briefing': 'Driver Briefing'
    }
    report_type_name = report_type_names.get(report.report_type, report.report_type)
    
    # Format the filename for download
    download_name = f"Route_{report.route_id}_{report_type_name.replace(' ', '_')}.pdf"
    
    # Send file for download
    return send_file(
        filepath,
        as_attachment=True,
        download_name=download_name,
        mimetype='application/pdf'
    )

@report_bp.route('/list')
@login_required
def list_reports():
    """List all reports for the current user."""
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template('reports/report_list.html', reports=reports, title="My Reports")

@report_bp.route('/delete/<int:report_id>', methods=['POST'])
@login_required
def delete(report_id):
    """Delete a report."""
    # Get report from database
    report = Report.query.get_or_404(report_id)
    
    # Ensure the report belongs to the current user
    if report.user_id != current_user.id and not current_user.is_admin():
        abort(403)  # Forbidden
    
    # Get file path
    filepath = report.get_file_path()
    
    # Delete file if it exists
    if os.path.exists(filepath):
        os.remove(filepath)
    
    # Delete report from database
    db.session.delete(report)
    db.session.commit()
    
    flash("Report deleted successfully.", "success")
    return redirect(url_for('report_bp.list_reports'))