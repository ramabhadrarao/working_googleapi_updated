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
        # Extract all data with proper defaults - this ensures all parameters are available
        major_highways = route_data.get('major_highways', [])
        sharp_turns = route_data.get('sharp_turns', [])
        petrol_bunks = route_data.get('petrol_bunks', {})
        hospitals = route_data.get('hospitals', {})
        schools = route_data.get('schools', {})
        food_stops = route_data.get('food_stops', {})
        police_stations = route_data.get('police_stations', {})
        elevation = route_data.get('elevation', [])
        weather = route_data.get('weather', [])
        toll_gates = route_data.get('toll_gates', [])
        bridges = route_data.get('bridges', [])
        risk_segments = route_data.get('risk_segments', [])
        compliance = route_data.get('compliance', {})
        emergency = route_data.get('emergency', {})
        environmental = route_data.get('environmental', {})
        
        # Get Google Maps API key
        api_key = current_app.config.get('GOOGLE_MAPS_API_KEY')
        
        # Call PDF generation function with unified parameter passing
        # This approach ensures all report types get all available data
        result = generate_pdf(
            filename=filepath,
            from_addr=route.from_address,
            to_addr=route.to_address,
            distance=route.distance,
            duration=route.duration,
            turns=sharp_turns,
            petrol_bunks=petrol_bunks,
            hospital_list=hospitals,
            schools=schools,
            food_stops=food_stops,
            police_stations=police_stations,
            elevation=elevation,
            weather=weather,
            risk_segments=risk_segments,
            compliance=compliance,
            emergency=emergency,
            environmental=environmental,
            toll_gates=toll_gates,
            bridges=bridges,
            vehicle_type=route.vehicle_type,
            type=report_type,  # This determines which sections to include
            api_key=api_key,
            major_highways=major_highways  # New parameter for highway information
        )
        
        # Check if PDF generation was successful
        if result is None:
            flash("Failed to generate PDF report. Please try again.", "danger")
            return redirect(url_for('route_bp.view', route_id=route_id))
        
        # Verify file was created and get file size
        if not os.path.exists(filepath):
            flash("PDF file was not created successfully.", "danger")
            return redirect(url_for('route_bp.view', route_id=route_id))
            
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
        
        # Log successful generation
        current_app.logger.info(f"Successfully generated {report_type} report for route {route_id}")
        
        # Redirect to download
        return redirect(url_for('report_bp.download', report_id=report.id))
        
    except Exception as e:
        current_app.logger.error(f"Error generating PDF for route {route_id}: {str(e)}")
        
        # Clean up any partially created file
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass
        
        flash(f"Error generating PDF report: {str(e)}", "danger")
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
        current_app.logger.error(f"Report file not found: {filepath}")
        flash("Report file not found. It may have been deleted.", "danger")
        return redirect(url_for('report_bp.list_reports'))
    
    # Determine report type name for download filename
    report_type_names = {
        'full': 'Full_Report',
        'summary': 'Summary_Report',
        'driver_briefing': 'Driver_Briefing'
    }
    report_type_name = report_type_names.get(report.report_type, report.report_type)
    
    # Format the filename for download with timestamp
    timestamp = report.created_at.strftime("%Y%m%d_%H%M%S")
    download_name = f"Route_{report.route_id}_{report_type_name}_{timestamp}.pdf"
    
    try:
        # Send file for download
        return send_file(
            filepath,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/pdf'
        )
    except Exception as e:
        current_app.logger.error(f"Error downloading report {report_id}: {str(e)}")
        flash("Error downloading report file.", "danger")
        return redirect(url_for('report_bp.list_reports'))

@report_bp.route('/list')
@login_required
def list_reports():
    """List all reports for the current user."""
    try:
        reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
        
        # Check if report files still exist and update status
        for report in reports:
            filepath = report.get_file_path()
            if not os.path.exists(filepath):
                current_app.logger.warning(f"Report file missing: {filepath}")
        
        return render_template('reports/report_list.html', reports=reports, title="My Reports")
    except Exception as e:
        current_app.logger.error(f"Error listing reports: {str(e)}")
        flash("Error loading reports list.", "danger")
        return redirect(url_for('main.dashboard'))

@report_bp.route('/delete/<int:report_id>', methods=['POST'])
@login_required
def delete(report_id):
    """Delete a report."""
    try:
        # Get report from database
        report = Report.query.get_or_404(report_id)
        
        # Ensure the report belongs to the current user
        if report.user_id != current_user.id and not current_user.is_admin():
            abort(403)  # Forbidden
        
        # Get file path
        filepath = report.get_file_path()
        
        # Delete file if it exists
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                current_app.logger.info(f"Deleted report file: {filepath}")
            except Exception as e:
                current_app.logger.error(f"Error deleting report file {filepath}: {str(e)}")
                # Continue with database deletion even if file deletion fails
        
        # Delete report from database
        db.session.delete(report)
        db.session.commit()
        
        flash("Report deleted successfully.", "success")
        
    except Exception as e:
        current_app.logger.error(f"Error deleting report {report_id}: {str(e)}")
        flash("Error deleting report.", "danger")
    
    return redirect(url_for('report_bp.list_reports'))

@report_bp.route('/preview/<int:route_id>/<report_type>')
@login_required
def preview(route_id, report_type):
    """Preview report content before generating PDF."""
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
    
    # Prepare preview data
    preview_data = {
        'route': route,
        'route_data': route_data,
        'report_type': report_type,
        'major_highways': route_data.get('major_highways', []),
        'sharp_turns': route_data.get('sharp_turns', []),
        'blind_spots': [t for t in route_data.get('sharp_turns', []) if t.get('angle', 0) > 70],
        'risk_segments': route_data.get('risk_segments', []),
        'weather': route_data.get('weather', []),
        'schools': route_data.get('schools', {}),
        'hospitals': route_data.get('hospitals', {}),
        'emergency': route_data.get('emergency', {}),
        'compliance': route_data.get('compliance', {}),
        'environmental': route_data.get('environmental', {}),
        'toll_gates': route_data.get('toll_gates', []),
        'bridges': route_data.get('bridges', [])
    }
    
    return render_template('reports/preview.html', **preview_data, title=f"Report Preview - {report_type.title()}")

@report_bp.route('/bulk-generate/<int:route_id>')
@login_required 
def bulk_generate(route_id):
    """Generate all three report types for a route."""
    # Get the route from database
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        abort(403)  # Forbidden
    
    generated_reports = []
    failed_reports = []
    
    # Generate all three report types
    report_types = ['full', 'summary', 'driver_briefing']
    
    for report_type in report_types:
        try:
            # Use the existing generate function logic
            route_data = route.get_route_data()
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{report_type}_{timestamp}_{unique_id}.pdf"
            filepath = os.path.join(current_app.config['REPORTS_FOLDER'], filename)
            
            # Extract all data
            major_highways = route_data.get('major_highways', [])
            sharp_turns = route_data.get('sharp_turns', [])
            petrol_bunks = route_data.get('petrol_bunks', {})
            hospitals = route_data.get('hospitals', {})
            schools = route_data.get('schools', {})
            food_stops = route_data.get('food_stops', {})
            police_stations = route_data.get('police_stations', {})
            elevation = route_data.get('elevation', [])
            weather = route_data.get('weather', [])
            toll_gates = route_data.get('toll_gates', [])
            bridges = route_data.get('bridges', [])
            risk_segments = route_data.get('risk_segments', [])
            compliance = route_data.get('compliance', {})
            emergency = route_data.get('emergency', {})
            environmental = route_data.get('environmental', {})
            
            # Generate PDF
            result = generate_pdf(
                filename=filepath,
                from_addr=route.from_address,
                to_addr=route.to_address,
                distance=route.distance,
                duration=route.duration,
                turns=sharp_turns,
                petrol_bunks=petrol_bunks,
                hospital_list=hospitals,
                schools=schools,
                food_stops=food_stops,
                police_stations=police_stations,
                elevation=elevation,
                weather=weather,
                risk_segments=risk_segments,
                compliance=compliance,
                emergency=emergency,
                environmental=environmental,
                toll_gates=toll_gates,
                bridges=bridges,
                vehicle_type=route.vehicle_type,
                type=report_type,
                api_key=current_app.config.get('GOOGLE_MAPS_API_KEY'),
                major_highways=major_highways
            )
            
            if result and os.path.exists(filepath):
                # Save report in database
                file_size = os.path.getsize(filepath)
                report = Report(
                    user_id=current_user.id,
                    route_id=route.id,
                    filename=filename,
                    report_type=report_type,
                    file_size=file_size
                )
                
                db.session.add(report)
                generated_reports.append(report_type)
            else:
                failed_reports.append(report_type)
                
        except Exception as e:
            current_app.logger.error(f"Error generating {report_type} report: {str(e)}")
            failed_reports.append(report_type)
    
    # Commit all successful reports
    if generated_reports:
        db.session.commit()
        flash(f"Successfully generated {len(generated_reports)} report(s): {', '.join(generated_reports)}", "success")
    
    if failed_reports:
        flash(f"Failed to generate {len(failed_reports)} report(s): {', '.join(failed_reports)}", "warning")
    
    return redirect(url_for('report_bp.list_reports'))