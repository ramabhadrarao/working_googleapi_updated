# controllers/csv_upload_controller.py - COMPLETE OPTIMIZED VERSION
import os
import pandas as pd
import numpy as np
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, make_response
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import FloatField, StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from werkzeug.utils import secure_filename
from models import db, Route
import json
import googlemaps
from datetime import datetime
import uuid
import time
import io
import csv
import logging

# Import existing utility functions
from utils.risk_analysis import calculate_route_risk, get_risk_map_data, get_vehicle_adjusted_time
from utils.compliance import ComplianceChecker
from utils.emergency import categorize_emergency_services, find_critical_emergency_points, create_emergency_response_plan
from utils.environmental import EnvironmentalAnalyzer
from utils.elevation import get_elevation_data
from utils.csv_route_analyzer import CSVRouteAnalyzer  # Optimized analyzer

# Create blueprint
csv_upload_bp = Blueprint('csv_upload_bp', __name__)

# Initialize services
compliance_checker = ComplianceChecker()
environmental_analyzer = EnvironmentalAnalyzer()
csv_analyzer = CSVRouteAnalyzer()

# Configure logging
logger = logging.getLogger(__name__)

class CSVUploadForm(FlaskForm):
    """Form for CSV route upload and analysis - with optimization options"""
    csv_file = FileField('Route CSV File', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV files only!')
    ])
    
    # Bounding box coordinates
    from_lat = FloatField('From Latitude', validators=[
        DataRequired(), 
        NumberRange(-90, 90, message="Latitude must be between -90 and 90")
    ])
    from_lng = FloatField('From Longitude', validators=[
        DataRequired(), 
        NumberRange(-180, 180, message="Longitude must be between -180 and 180")
    ])
    to_lat = FloatField('To Latitude', validators=[
        DataRequired(), 
        NumberRange(-90, 90, message="Latitude must be between -90 and 90")
    ])
    to_lng = FloatField('To Longitude', validators=[
        DataRequired(), 
        NumberRange(-180, 180, message="Longitude must be between -180 and 180")
    ])
    
    route_name = StringField('Route Name (Optional)')
    vehicle_type = SelectField('Vehicle Type', choices=[
        ('car', 'Car'),
        ('medium_truck', 'Medium Truck'),
        ('heavy_truck', 'Heavy Truck'),
        ('tanker', 'Tanker'),
        ('bus', 'Bus')
    ], default='car')
    
    # Processing optimization options
    processing_mode = SelectField('Processing Mode', choices=[
        ('fast', 'Fast (Basic Analysis)'),
        ('standard', 'Standard (Full Analysis)'),
        ('detailed', 'Detailed (Comprehensive)')
    ], default='standard')
    
    max_points = SelectField('Maximum Points for Analysis', choices=[
        ('250', '250 points'),
        ('500', '500 points'),
        ('1000', '1000 points'),
        ('all', 'All points')
    ], default='500')
    
    submit = SubmitField('Upload and Analyze Route')

@csv_upload_bp.route('/', methods=['GET', 'POST'])
@login_required
def upload_csv():
    """Handle CSV route upload and analysis - OPTIMIZED"""
    form = CSVUploadForm()
    
    if form.validate_on_submit():
        start_time = time.time()
        file_path = None
        
        try:
            # Save uploaded file
            csv_file = form.csv_file.data
            filename = secure_filename(csv_file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            csv_file.save(file_path)
            
            # Quick file size and validation check
            try:
                file_size = os.path.getsize(file_path)
                if file_size > 50 * 1024 * 1024:  # 50MB limit
                    flash('File too large. Please use a file smaller than 50MB.', 'danger')
                    os.remove(file_path)
                    return redirect(url_for('csv_upload_bp.upload_csv'))
                
                # Quick row count check
                with open(file_path, 'r') as f:
                    total_rows = sum(1 for line in f) - 1  # Subtract header
                
                if total_rows > 20000:
                    flash(f'File too large ({total_rows:,} points). Please use a file with fewer than 20,000 points.', 'danger')
                    os.remove(file_path)
                    return redirect(url_for('csv_upload_bp.upload_csv'))
                    
                logger.info(f"Processing CSV with {total_rows:,} points")
                    
            except Exception as e:
                flash(f'Error reading CSV file: {str(e)}', 'danger')
                os.remove(file_path)
                return redirect(url_for('csv_upload_bp.upload_csv'))
            
            # Extract form data
            bounds = {
                'from_lat': form.from_lat.data,
                'from_lng': form.from_lng.data,
                'to_lat': form.to_lat.data,
                'to_lng': form.to_lng.data
            }
            
            vehicle_type = form.vehicle_type.data
            route_name = form.route_name.data or f"CSV Route {timestamp}"
            processing_mode = form.processing_mode.data
            max_points = form.max_points.data
            
            # Configure CSV analyzer based on form selections
            configure_analyzer(processing_mode, max_points)
            
            # Log processing configuration
            logger.info(f"Processing configuration: mode={processing_mode}, max_points={max_points}")
            
            # Show processing start message
            if total_rows > 1000:
                flash(f'Processing large file ({total_rows:,} points). This may take several minutes...', 'info')
            
            # Process CSV and analyze route
            try:
                analysis_result = csv_analyzer.process_csv_route(
                    file_path, bounds, vehicle_type, current_app.config['GOOGLE_MAPS_API_KEY']
                )
                
                processing_time = time.time() - start_time
                logger.info(f"CSV processing completed in {processing_time:.2f} seconds")
                
            except Exception as e:
                logger.error(f"CSV processing error: {str(e)}")
                flash(f"Processing error: {str(e)}. Try using a smaller file or different bounds.", 'danger')
                os.remove(file_path)
                return redirect(url_for('csv_upload_bp.upload_csv'))
            
            if not analysis_result['success']:
                flash(f"Error processing CSV: {analysis_result['error']}", 'danger')
                os.remove(file_path)
                return redirect(url_for('csv_upload_bp.upload_csv'))
            
            # Prepare data for database storage (limit data size)
            route_data = analysis_result['data']
            essential_data = prepare_essential_data(route_data)
            
            # Create and save route
            route = create_route_record(
                bounds, route_name, vehicle_type, essential_data, processing_mode, max_points
            )
            
            # Save to database
            try:
                db.session.add(route)
                db.session.commit()
                logger.info(f"Route saved to database with ID: {route.id}")
            except Exception as e:
                logger.error(f"Database error: {str(e)}")
                flash('Error saving route to database. Please try again.', 'danger')
                os.remove(file_path)
                return redirect(url_for('csv_upload_bp.upload_csv'))
            
            # Clean up uploaded file
            os.remove(file_path)
            
            # Success message with detailed stats
            success_message = create_success_message(essential_data, processing_time)
            flash(success_message, 'success')
            
            return redirect(url_for('csv_upload_bp.view_csv_route', route_id=route.id))
            
        except Exception as e:
            logger.error(f"Unexpected error processing CSV route: {str(e)}")
            flash(f'Unexpected error: {str(e)}. Please try again or contact support.', 'danger')
            
            # Clean up file if it exists
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
    
    return render_template('csv_upload/upload.html', form=form, title="Upload CSV Route")

def configure_analyzer(processing_mode, max_points):
    """Configure the CSV analyzer based on user selections"""
    
    # Processing mode configurations
    mode_configs = {
        'fast': {
            'max_points_for_analysis': 250,
            'poi_search_points': 3,
            'elevation_sample_points': 10,
            'weather_sample_points': 2,
            'sharp_turn_sample_interval': 10,
            'enable_parallel_processing': True,
            'api_timeout': 5
        },
        'standard': {
            'max_points_for_analysis': 500,
            'poi_search_points': 5,
            'elevation_sample_points': 20,
            'weather_sample_points': 3,
            'sharp_turn_sample_interval': 5,
            'enable_parallel_processing': True,
            'api_timeout': 10
        },
        'detailed': {
            'max_points_for_analysis': 1000,
            'poi_search_points': 8,
            'elevation_sample_points': 50,
            'weather_sample_points': 5,
            'sharp_turn_sample_interval': 3,
            'enable_parallel_processing': True,
            'api_timeout': 15
        }
    }
    
    # Apply mode configuration
    config = mode_configs.get(processing_mode, mode_configs['standard'])
    csv_analyzer.config.update(config)
    
    # Override max_points if specifically set
    if max_points != 'all':
        csv_analyzer.config['max_points_for_analysis'] = int(max_points)
    else:
        csv_analyzer.config['max_points_for_analysis'] = None  # No limit

def prepare_essential_data(route_data):
    """Prepare essential data for database storage, limiting size"""
    
    return {
        'distance': route_data.get('distance', '0 km'),
        'distance_value': route_data.get('distance_value', 0),
        'duration': route_data.get('duration', '0 mins'),
        'duration_value': route_data.get('duration_value', 0),
        'sharp_turns': route_data.get('sharp_turns', [])[:50],  # Limit to 50 turns
        'risk_segments': route_data.get('risk_segments', [])[:20],  # Limit to 20 segments
        'filtered_points': route_data.get('filtered_points', [])[:1000],  # Limit to 1000 points
        'elevation': route_data.get('elevation', [])[:30],  # Limit elevation data
        'weather': route_data.get('weather', [])[:5],  # Limit weather data
        'petrol_bunks': dict(list(route_data.get('petrol_bunks', {}).items())[:10]),  # Limit POIs
        'hospitals': dict(list(route_data.get('hospitals', {}).items())[:10]),
        'schools': dict(list(route_data.get('schools', {}).items())[:10]),
        'food_stops': dict(list(route_data.get('food_stops', {}).items())[:10]),
        'police_stations': dict(list(route_data.get('police_stations', {}).items())[:10]),
        'processing_stats': {
            'original_points': len(route_data.get('original_points', [])),
            'filtered_points': len(route_data.get('filtered_points', [])),
            'processing_time': route_data.get('processing_time', 0),
            'optimization_applied': True
        }
    }

def create_route_record(bounds, route_name, vehicle_type, essential_data, processing_mode, max_points):
    """Create a Route record for database storage"""
    
    route = Route(
        user_id=current_user.id,
        name=route_name,
        from_address=f"CSV Route Start: {bounds['from_lat']:.6f}, {bounds['from_lng']:.6f}",
        to_address=f"CSV Route End: {bounds['to_lat']:.6f}, {bounds['to_lng']:.6f}",
        from_lat=bounds['from_lat'],
        from_lng=bounds['from_lng'],
        to_lat=bounds['to_lat'],
        to_lng=bounds['to_lng'],
        distance=essential_data['distance'],
        distance_value=essential_data['distance_value'],
        duration=essential_data['duration'],
        duration_value=essential_data['duration_value'],
        vehicle_type=vehicle_type,
        polyline=json.dumps(essential_data['filtered_points'])
    )
    
    # Save route data and risk analysis
    route.save_route_data(essential_data)
    route.save_risk_analysis(essential_data['risk_segments'])
    
    # Update summary metrics
    route.sharp_turns_count = len(essential_data.get('sharp_turns', []))
    route.blind_spots_count = len([t for t in essential_data.get('sharp_turns', []) if t.get('angle', 0) > 70])
    
    # Add processing metadata
    route.processing_mode = processing_mode
    route.max_points_configured = max_points
    
    return route

def create_success_message(essential_data, processing_time):
    """Create a detailed success message"""
    
    stats = essential_data.get('processing_stats', {})
    original_points = stats.get('original_points', 0)
    filtered_points = stats.get('filtered_points', 0)
    
    message = f"""
    CSV route analyzed successfully!<br>
    • Processed {filtered_points:,} points from {original_points:,} total points<br>
    • Found {len(essential_data.get('sharp_turns', []))} sharp turns<br>
    • Identified {len(essential_data.get('risk_segments', []))} risk segments<br>
    • Processing time: {processing_time:.1f} seconds
    """
    
    return message

@csv_upload_bp.route('/view/<int:route_id>')
@login_required
def view_csv_route(route_id):
    """View CSV-based route analysis"""
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to view this route.', 'danger')
        return redirect(url_for('csv_upload_bp.upload_csv'))
    
    # Get route data from database
    data = route.get_route_data()
    
    # Ensure data structure is compatible with CSV dashboard template
    if not data:
        data = {}
    
    # Fix missing fields that might cause template errors
    data.setdefault('distance', route.distance or '0 km')
    data.setdefault('duration', route.duration or '0 mins')
    data.setdefault('vehicle_type', route.vehicle_type or 'car')
    data.setdefault('sharp_turns', [])
    data.setdefault('elevation', [])
    data.setdefault('weather', [])
    data.setdefault('risk_segments', [])
    data.setdefault('compliance', {})
    data.setdefault('emergency', {})
    data.setdefault('environmental', {})
    data.setdefault('petrol_bunks', {})
    data.setdefault('hospitals', {})
    data.setdefault('schools', {})
    data.setdefault('food_stops', {})
    data.setdefault('police_stations', {})
    data.setdefault('original_points', [])
    data.setdefault('filtered_points', [])
    data.setdefault('points_filtered', 0)
    
    # Fix risk segments to include distance field
    risk_segments = route.get_risk_analysis() or []
    for segment in risk_segments:
        if 'distance' not in segment:
            # Calculate approximate distance for the segment
            points = segment.get('points', [])
            if len(points) >= 2:
                from geopy.distance import geodesic
                total_distance = 0
                for i in range(len(points) - 1):
                    try:
                        p1 = (points[i][0], points[i][1])
                        p2 = (points[i+1][0], points[i+1][1])
                        total_distance += geodesic(p1, p2).meters
                    except:
                        continue
                segment['distance'] = total_distance
            else:
                segment['distance'] = 0
    
    # Update risk segments in data
    data['risk_segments'] = risk_segments
    
    # Prepare map data
    map_data = {
        'polyline': json.loads(route.polyline) if route.polyline else [], 
        'sharp_turns': data.get('sharp_turns', []),
        'risk_segments': get_risk_map_data(risk_segments),
        'toll_gates': data.get('toll_gates', []),
        'bridges': data.get('bridges', []),
        'original_points': data.get('original_points', []),
        'filtered_points': data.get('filtered_points', [])
    }
    
    # Use the CSV-specific dashboard template
    return render_template(
        "csv_upload/dashboard.html",  # This should be the CSV-specific template
        route=route,
        data=data, 
        map_data=map_data, 
        api_key=current_app.config['GOOGLE_MAPS_API_KEY'],
        title=f"CSV Route Analysis: {route.name}"
    )

@csv_upload_bp.route('/list')
@login_required
def list_csv_routes():
    """List all CSV-based routes for the current user"""
    # Filter routes that were created from CSV uploads
    csv_routes = Route.query.filter(
        Route.user_id == current_user.id,
        Route.name.like('%CSV Route%')
    ).order_by(Route.created_at.desc()).all()
    
    return render_template('csv_upload/list.html', routes=csv_routes, title="My CSV Routes")

@csv_upload_bp.route('/api/validate-csv', methods=['POST'])
@login_required
def validate_csv():
    """API endpoint to validate CSV file before upload"""
    try:
        if 'file' not in request.files:
            return jsonify({'valid': False, 'error': 'No file provided'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'valid': False, 'error': 'No file selected'})
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            return jsonify({'valid': False, 'error': 'File too large. Maximum size is 50MB.'})
        
        # Read and validate CSV
        try:
            df = pd.read_csv(file.stream, nrows=1000)  # Read first 1000 rows for validation
            file.stream.seek(0)  # Reset stream
            
            # Count total rows
            total_rows = sum(1 for line in file.stream) - 1  # Subtract header
            file.stream.seek(0)
            
        except Exception as e:
            return jsonify({'valid': False, 'error': f'Invalid CSV format: {str(e)}'})
        
        # Check if CSV has at least 2 columns (lat, lng)
        if len(df.columns) < 2:
            return jsonify({'valid': False, 'error': 'CSV must have at least 2 columns (latitude, longitude)'})
        
        # Check if we have numeric data in first two columns
        try:
            lat_col = pd.to_numeric(df.iloc[:, 0], errors='coerce')
            lng_col = pd.to_numeric(df.iloc[:, 1], errors='coerce')
            
            # Remove NaN values
            valid_coords = ~(lat_col.isna() | lng_col.isna())
            lat_col = lat_col[valid_coords]
            lng_col = lng_col[valid_coords]
            
            if len(lat_col) == 0:
                return jsonify({'valid': False, 'error': 'No valid coordinate pairs found'})
            
        except Exception as e:
            return jsonify({'valid': False, 'error': 'First two columns must contain numeric latitude and longitude values'})
        
        # Validate coordinate ranges
        if not (lat_col.between(-90, 90).all()):
            return jsonify({'valid': False, 'error': 'Latitude values must be between -90 and 90'})
        
        if not (lng_col.between(-180, 180).all()):
            return jsonify({'valid': False, 'error': 'Longitude values must be between -180 and 180'})
        
        # Check for reasonable point density
        if total_rows > 20000:
            return jsonify({
                'valid': False, 
                'error': f'Too many points ({total_rows:,}). Please use a file with fewer than 20,000 points.'
            })
        
        # Return validation success with basic stats
        return jsonify({
            'valid': True,
            'stats': {
                'total_points': total_rows,
                'valid_coordinates': len(lat_col),
                'lat_range': [float(lat_col.min()), float(lat_col.max())],
                'lng_range': [float(lng_col.min()), float(lng_col.max())],
                'columns': list(df.columns[:5]),  # Show first 5 columns
                'file_size_mb': round(file_size / (1024 * 1024), 2)
            }
        })
        
    except Exception as e:
        logger.error(f"CSV validation error: {str(e)}")
        return jsonify({'valid': False, 'error': f'Validation error: {str(e)}'})

@csv_upload_bp.route('/api/preview-bounds', methods=['POST'])
@login_required
def preview_bounds():
    """API endpoint to preview how many points fall within specified bounds"""
    try:
        data = request.get_json()
        
        # Get bounds from request
        bounds = {
            'from_lat': float(data['from_lat']),
            'from_lng': float(data['from_lng']),
            'to_lat': float(data['to_lat']),
            'to_lng': float(data['to_lng'])
        }
        
        # If CSV data is provided, filter and count points
        if 'csv_data' in data:
            csv_points = data['csv_data']
            filtered_count = csv_analyzer.count_points_in_bounds(csv_points, bounds)
            
            return jsonify({
                'success': True,
                'total_points': len(csv_points),
                'filtered_points': filtered_count,
                'percentage': round((filtered_count / len(csv_points)) * 100, 2) if csv_points else 0
            })
        
        return jsonify({'success': True, 'bounds': bounds})
        
    except Exception as e:
        logger.error(f"Bounds preview error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@csv_upload_bp.route('/export/<int:route_id>')
@login_required
def export_csv_route(route_id):
    """Export analyzed CSV route data"""
    route = Route.query.get_or_404(route_id)
    
    # Ensure the route belongs to the current user
    if route.user_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to export this route.', 'danger')
        return redirect(url_for('csv_upload_bp.list_csv_routes'))
    
    try:
        # Get route data
        data = route.get_route_data()
        risk_segments = route.get_risk_analysis()
        
        # Prepare export data
        export_data = csv_analyzer.prepare_export_data(route, data, risk_segments)
        
        # Generate CSV export
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Latitude', 'Longitude', 'Risk_Level', 'Risk_Score', 
            'Segment_ID', 'Sharp_Turn', 'Elevation', 'Turn_Angle'
        ])
        
        # Write data rows
        for point in export_data:
            writer.writerow([
                point['lat'],
                point['lng'],
                point.get('risk_level', 'LOW'),
                point.get('risk_score', 0),
                point.get('segment_id', 0),
                point.get('is_sharp_turn', False),
                point.get('elevation', 0),
                point.get('turn_angle', 0)
            ])
        
        output.seek(0)
        
        # Create response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=route_analysis_{route.id}_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting CSV route: {str(e)}")
        flash(f'Error exporting route: {str(e)}', 'danger')
        return redirect(url_for('csv_upload_bp.view_csv_route', route_id=route_id))

@csv_upload_bp.route('/api/processing-status/<task_id>')
@login_required
def processing_status(task_id):
    """Check processing status for long-running CSV analysis"""
    # This is a placeholder for future implementation with Celery or similar
    return jsonify({
        'status': 'processing',
        'progress': 50,
        'message': 'Analyzing route data...',
        'estimated_time_remaining': 30
    })

@csv_upload_bp.route('/api/processing-config', methods=['GET', 'POST'])
@login_required
def processing_config():
    """Configure processing parameters"""
    if request.method == 'POST':
        config = request.get_json()
        
        # Update CSV analyzer configuration
        csv_analyzer.config.update({
            'max_points_for_analysis': config.get('max_points', 500),
            'poi_search_points': config.get('poi_points', 5),
            'elevation_sample_points': config.get('elevation_points', 20),
            'enable_parallel_processing': config.get('parallel_processing', True)
        })
        
        return jsonify({'success': True, 'message': 'Configuration updated'})
    
    return jsonify(csv_analyzer.config)

# Error handlers
@csv_upload_bp.errorhandler(413)
def too_large(e):
    flash('File too large. Please use a file smaller than 50MB.', 'danger')
    return redirect(url_for('csv_upload_bp.upload_csv'))

@csv_upload_bp.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception in CSV upload: {str(e)}")
    flash('An unexpected error occurred. Please try again.', 'danger')
    return redirect(url_for('csv_upload_bp.upload_csv'))