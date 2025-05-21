import json
from datetime import datetime
from . import db

class Route(db.Model):
    """Route model to store route information and analysis results."""
    __tablename__ = 'routes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(128))
    from_address = db.Column(db.String(256), nullable=False)
    to_address = db.Column(db.String(256), nullable=False)
    from_lat = db.Column(db.Float)
    from_lng = db.Column(db.Float)
    to_lat = db.Column(db.Float)
    to_lng = db.Column(db.Float)
    distance = db.Column(db.String(64))
    distance_value = db.Column(db.Integer)  # Distance in meters
    duration = db.Column(db.String(64))
    duration_value = db.Column(db.Integer)  # Duration in seconds
    vehicle_type = db.Column(db.String(32), default='car')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Serialized route data (JSON)
    polyline = db.Column(db.Text)  # Encoded polyline of the route
    route_data = db.Column(db.Text)  # Serialized route data in JSON
    risk_analysis = db.Column(db.Text)  # Risk analysis results in JSON
    
    # Overall route metrics
    risk_score = db.Column(db.Float)
    sharp_turns_count = db.Column(db.Integer)
    high_risk_segments = db.Column(db.Integer)
    medium_risk_segments = db.Column(db.Integer)
    low_risk_segments = db.Column(db.Integer)
    blind_spots_count = db.Column(db.Integer)
    
    # Relationships
    reports = db.relationship('Report', backref='route', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(Route, self).__init__(**kwargs)
    
    def save_route_data(self, data):
        """Save route data as JSON."""
        self.route_data = json.dumps(data)
    
    def get_route_data(self):
        """Get route data from JSON."""
        if self.route_data:
            return json.loads(self.route_data)
        return {}
    
    def save_risk_analysis(self, data):
        """Save risk analysis as JSON."""
        self.risk_analysis = json.dumps(data)
        
        # Update summary metrics
        if isinstance(data, list):
            self.high_risk_segments = sum(1 for segment in data if segment.get('risk_level') == 'HIGH')
            self.medium_risk_segments = sum(1 for segment in data if segment.get('risk_level') == 'MEDIUM')
            self.low_risk_segments = sum(1 for segment in data if segment.get('risk_level') == 'LOW')
            
            # Calculate average risk score
            if data:
                self.risk_score = sum(segment.get('risk_score', 0) for segment in data) / len(data)
            else:
                self.risk_score = 0
    
    def get_risk_analysis(self):
        """Get risk analysis from JSON."""
        if self.risk_analysis:
            return json.loads(self.risk_analysis)
        return []
        
    def get_toll_gates(self):
        """Get toll gates from route data."""
        route_data = self.get_route_data()
        return route_data.get('toll_gates', [])
    
    def get_bridges(self):
        """Get bridges from route data."""
        route_data = self.get_route_data()
        return route_data.get('bridges', [])
    
    def get_obstacles(self):
        """Get obstacles from route data."""
        route_data = self.get_route_data()
        return route_data.get('obstacles', [])
    
    def get_blind_spots(self):
        """Get blind spots (sharp turns with high angles)."""
        route_data = self.get_route_data()
        turns = route_data.get('sharp_turns', [])
        return [turn for turn in turns if turn.get('angle', 0) > 70]  # Turns with angles > 70° are blind spots
    
    def __repr__(self):
        return f'<Route {self.id}: {self.from_address} to {self.to_address}>'