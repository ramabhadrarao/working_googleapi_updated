# config/processing_config.py
"""
Configuration settings for CSV route processing optimization
"""

# Processing modes configuration
PROCESSING_MODES = {
    'fast': {
        'max_points_for_analysis': 250,
        'poi_search_points': 3,
        'elevation_sample_points': 10,
        'weather_sample_points': 2,
        'sharp_turn_sample_interval': 10,
        'enable_parallel_processing': True,
        'skip_environmental_analysis': True,
        'skip_detailed_compliance': True,
        'api_timeout': 5
    },
    'standard': {
        'max_points_for_analysis': 500,
        'poi_search_points': 5,
        'elevation_sample_points': 20,
        'weather_sample_points': 3,
        'sharp_turn_sample_interval': 5,
        'enable_parallel_processing': True,
        'skip_environmental_analysis': False,
        'skip_detailed_compliance': False,
        'api_timeout': 10
    },
    'detailed': {
        'max_points_for_analysis': 1000,
        'poi_search_points': 8,
        'elevation_sample_points': 50,
        'weather_sample_points': 5,
        'sharp_turn_sample_interval': 3,
        'enable_parallel_processing': True,
        'skip_environmental_analysis': False,
        'skip_detailed_compliance': False,
        'api_timeout': 15
    }
}

# File size limits
MAX_FILE_SIZE_MB = 50
MAX_POINTS_WARNING = 5000
MAX_POINTS_ERROR = 10000

# Database storage limits
MAX_POINTS_STORED = 1000
MAX_SHARP_TURNS_STORED = 50
MAX_RISK_SEGMENTS_STORED = 20

# API rate limiting
MAX_API_CALLS_PER_MINUTE = 100
API_RETRY_ATTEMPTS = 3
API_RETRY_DELAY = 1  # seconds

# Processing timeouts
PROCESSING_TIMEOUT_SECONDS = 300  # 5 minutes
ANALYSIS_STEP_TIMEOUT = 60  # 1 minute per analysis step

def get_processing_config(mode='standard', max_points=None):
    """
    Get processing configuration based on mode and optional max_points override
    
    Args:
        mode (str): Processing mode ('fast', 'standard', 'detailed')
        max_points (int): Override for max_points_for_analysis
    
    Returns:
        dict: Configuration settings
    """
    config = PROCESSING_MODES.get(mode, PROCESSING_MODES['standard']).copy()
    
    if max_points and max_points != 'all':
        config['max_points_for_analysis'] = int(max_points)
    elif max_points == 'all':
        config['max_points_for_analysis'] = None  # No limit
    
    return config

def estimate_processing_time(total_points, mode='standard'):
    """
    Estimate processing time based on number of points and mode
    
    Args:
        total_points (int): Total number of GPS points
        mode (str): Processing mode
    
    Returns:
        dict: Estimated time and complexity
    """
    config = PROCESSING_MODES[mode]
    effective_points = min(total_points, config['max_points_for_analysis'])
    
    # Base time estimates (in seconds)
    base_times = {
        'fast': 2,      # 2 seconds per 100 points
        'standard': 5,  # 5 seconds per 100 points
        'detailed': 10  # 10 seconds per 100 points
    }
    
    estimated_seconds = (effective_points / 100) * base_times.get(mode, 5)
    
    # Add API call overhead
    api_calls = (config['poi_search_points'] * 5 +  # POI searches
                config['elevation_sample_points'] +   # Elevation calls
                config['weather_sample_points'])      # Weather calls
    
    api_overhead = api_calls * 0.5  # 0.5 seconds per API call
    total_time = estimated_seconds + api_overhead
    
    return {
        'estimated_seconds': int(total_time),
        'estimated_text': format_duration(total_time),
        'complexity': 'Low' if total_time < 30 else 'Medium' if total_time < 120 else 'High',
        'effective_points': effective_points,
        'api_calls': api_calls
    }

def format_duration(seconds):
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"

# Progress tracking messages
PROGRESS_MESSAGES = {
    0: "Initializing...",
    10: "Reading CSV file...",
    20: "Filtering points by bounds...",
    30: "Optimizing route points...",
    40: "Calculating route statistics...",
    50: "Finding sharp turns...",
    60: "Getting elevation data...",
    70: "Searching for points of interest...",
    80: "Analyzing risks and compliance...",
    90: "Finalizing analysis...",
    100: "Complete!"
}