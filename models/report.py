from datetime import datetime
from . import db

class Report(db.Model):
    """Report model to store generated PDF reports."""
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    route_id = db.Column(db.Integer, db.ForeignKey('routes.id'), nullable=False)
    filename = db.Column(db.String(256), nullable=False)
    report_type = db.Column(db.String(64), default='full')  # 'full', 'summary', 'driver_briefing'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)  # File size in bytes
    
    def __init__(self, **kwargs):
        super(Report, self).__init__(**kwargs)
    
    def get_download_url(self):
        """Get the download URL for the report."""
        return f'/reports/download/{self.id}'
    
    def get_file_path(self):
        """Get the file path for the report."""
        import os
        from flask import current_app
        return os.path.join(current_app.config['REPORTS_FOLDER'], self.filename)
    
    def __repr__(self):
        return f'<Report {self.id}: {self.report_type} for Route {self.route_id}>'