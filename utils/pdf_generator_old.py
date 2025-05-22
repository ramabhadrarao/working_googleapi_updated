from fpdf import FPDF
import os
import datetime
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import requests
import tempfile

class RoutePDF(FPDF):
    def __init__(self, title=None):
        super().__init__()
        self.title = title or "Route Analytics Report"
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
        # Add logo
        # self.image('static/images/logo.png', 10, 8, 33)
        
        # Set font
        self.set_font('Arial', 'B', 15)
        
        # Title
        self.cell(0, 10, self.title, 0, 1, 'C')
        
        # Line break
        self.ln(10)
        
    def footer(self):
        # Go to 1.5 cm from bottom
        self.set_y(-15)
        
        # Set font
        self.set_font('Arial', 'I', 8)
        
        # Add date and page number
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cell(0, 10, f'Generated on {now} | Page {self.page_no()}/{{nb}}', 0, 0, 'C')
        
    def chapter_title(self, title):
        # Set font
        self.set_font('Arial', 'B', 12)
        
        # Add background color
        self.set_fill_color(200, 220, 255)
        
        # Title
        self.cell(0, 6, title, 0, 1, 'L', 1)
        
        # Line break
        self.ln(4)
        
    def chapter_body(self, body):
        # Set font
        self.set_font('Arial', '', 12)
        
        # Add content - handle encoding issues
        try:
            # Clean the body text of problematic Unicode characters
            clean_body = self.clean_text(body)
            self.multi_cell(0, 5, clean_body)
        except UnicodeEncodeError:
            # Fallback: encode to latin-1 and ignore errors
            clean_body = body.encode('latin-1', 'ignore').decode('latin-1')
            self.multi_cell(0, 5, clean_body)
        
        # Line break
        self.ln()
    
    def clean_text(self, text):
        """Clean text by replacing Unicode characters with ASCII equivalents"""
        if not isinstance(text, str):
            text = str(text)
        
        # Replace common Unicode characters with ASCII equivalents
        replacements = {
            '⚠': '[WARNING]',
            '🚫': '[DANGER]',
            'ℹ': '[INFO]',
            '✅': '[OK]',
            '🚗': '[CAR]',
            '🚛': '[TRUCK]',
            '🚌': '[BUS]',
            '⛽': '[FUEL]',
            '🏥': '[HOSPITAL]',
            '🚔': '[POLICE]',
            '🌡': '[TEMP]',
            '🌧': '[RAIN]',
            '☀': '[SUN]',
            '❄': '[SNOW]',
            '💨': '[WIND]',
            '°': 'deg',
            '•': '*',
            '→': '->',
            '←': '<-',
            '↑': '^',
            '↓': 'v',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            '–': '-',
            '—': '-'
        }
        
        for unicode_char, ascii_replacement in replacements.items():
            text = text.replace(unicode_char, ascii_replacement)
        
        # Remove any remaining problematic characters
        try:
            # Try to encode to latin-1 to catch remaining issues
            text.encode('latin-1')
            return text
        except UnicodeEncodeError:
            # Replace any remaining non-latin-1 characters
            return text.encode('latin-1', 'ignore').decode('latin-1')
        
    def add_section(self, title, content):
        clean_title = self.clean_text(title)
        clean_content = self.clean_text(content)
        self.chapter_title(clean_title)
        self.chapter_body(clean_content)
    
    def add_table(self, headers, data, widths=None):
        # Calculate column widths if not provided
        if widths is None:
            page_width = self.w - 2*self.l_margin
            widths = [page_width / len(headers)] * len(headers)
        
        # Set font for header
        self.set_font('Arial', 'B', 10)
        self.set_fill_color(200, 220, 255)
        
        # Print header
        for i, header in enumerate(headers):
            clean_header = self.clean_text(str(header))
            self.cell(widths[i], 7, clean_header, 1, 0, 'C', 1)
        self.ln()
        
        # Set font for data
        self.set_font('Arial', '', 10)
        self.set_fill_color(255, 255, 255)
        
        # Print rows
        fill = False
        for row in data:
            for i, cell in enumerate(row):
                # Clean and truncate long text
                cell_text = self.clean_text(str(cell))
                if len(cell_text) > 40:
                    cell_text = cell_text[:37] + '...'
                self.cell(widths[i], 6, cell_text, 1, 0, 'L', fill)
            self.ln()
            fill = not fill
    
    def add_risk_chart(self, risk_segments):
        # Count risk levels
        high = len([s for s in risk_segments if s.get('risk_level') == 'HIGH'])
        medium = len([s for s in risk_segments if s.get('risk_level') == 'MEDIUM'])
        low = len([s for s in risk_segments if s.get('risk_level') == 'LOW'])
        
        if high + medium + low == 0:
            # No risk data, skip chart
            self.add_section("Risk Analysis", "No risk data available for this route.")
            return
            
        # Create a bar chart
        plt.figure(figsize=(5, 3))
        
        bars = plt.bar(['High', 'Medium', 'Low'], [high, medium, low], 
                color=['#dc3545', '#fd7e14', '#28a745'])
        
        # Add counts above bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height}', ha='center', va='bottom')
        
        plt.ylim(0, max(high, medium, low) + 1)
        plt.title('Risk Level Distribution')
        
        # Save to a temporary buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        
        # Add the chart to the PDF
        self.chapter_title("Risk Analysis")
        
        # Overall risk assessment
        if high > 0:
            risk_level = "HIGH"
        elif medium > 0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
            
        self.set_font('Arial', 'B', 12)
        self.cell(0, 6, f"Overall Risk Level: {risk_level}", 0, 1)
        self.ln(2)
        
        # Add the chart
        self.image(buf, x=40, w=120)
        self.ln(5)
        
        # Add risk description
        if high > 0:
            self.chapter_body("This route contains high-risk segments that require special attention. Review the detailed risk analysis for specific hazards.")
        elif medium > 0:
            self.chapter_body("This route contains medium-risk segments. Exercise caution and follow recommended safety measures.")
        else:
            self.chapter_body("This route is generally low-risk. Follow standard safety procedures for a safe journey.")
    
    def add_street_view(self, lat, lng, api_key):
        """Add a Google Street View image for a location"""
        try:
            url = f"https://maps.googleapis.com/maps/api/streetview?size=600x300&location={lat},{lng}&fov=80&heading=70&pitch=0&key={api_key}"
            response = requests.get(url)
            
            if response.status_code == 200:
                # Save image to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp:
                    temp.write(response.content)
                    temp_path = temp.name
                
                # Add the image to the PDF
                self.image(temp_path, x=10, w=190)
                
                # Delete the temporary file
                os.unlink(temp_path)
                
                return True
            
            return False
        except Exception as e:
            print(f"Error adding street view: {e}")
            return False

    def add_hazard_icon(self, icon_type="warning"):
        """Add a text-based hazard indicator to the PDF"""
        icons = {
            "warning": "[!]",
            "danger": "[X]",
            "info": "[i]",
            "success": "[OK]"
        }
        
        icon = icons.get(icon_type, icons["warning"])
        
        self.set_font('Arial', 'B', 12)
        self.cell(10, 10, icon, 0, 0, 'L')
        self.set_font('Arial', '', 12)

def generate_pdf(filename, from_addr, to_addr, distance, duration, turns, petrol_bunks,
                hospital_list, schools=None, food_stops=None, police_stations=None, 
                elevation=None, weather=None, risk_segments=None, compliance=None,
                emergency=None, environmental=None, toll_gates=None, bridges=None, 
                vehicle_type="car", type="full", api_key=None):
    """
    Generate a PDF report based on the route analysis
    
    Args:
        type: Type of report to generate ('full', 'summary', 'driver_briefing')
    """
    # Ensure all expected data is present
    if not schools:
        schools = {}
    if not food_stops:
        food_stops = {}
    if not police_stations:
        police_stations = {}
    if not elevation:
        elevation = []
    if not weather:
        weather = []
    if not risk_segments:
        risk_segments = []
    if not toll_gates:
        toll_gates = []
    if not bridges:
        bridges = []
    
    # Create PDF with improved layout
    if type == "full":
        pdf = RoutePDF("Route Analytics Full Report")
    elif type == "summary":
        pdf = RoutePDF("Route Summary Report")
    elif type == "driver_briefing":
        pdf = RoutePDF("Driver Briefing")
    else:
        pdf = RoutePDF()
    
    pdf.alias_nb_pages()
    pdf.add_page()

    # Route Overview
    pdf.add_section("Route Overview", 
        f"From: {from_addr}\n"
        f"To: {to_addr}\n"
        f"Distance: {distance}\n"
        f"Estimated Duration: {duration}\n"
        f"Vehicle Type: {vehicle_type.replace('_', ' ').title()}"
    )
    
    # Add special features summary
    special_features = []
    if turns:
        special_features.append(f"Sharp turns: {len(turns)}")
        blind_spots = len([turn for turn in turns if turn.get('angle', 0) > 70])
        if blind_spots > 0:
            special_features.append(f"Blind spots: {blind_spots}")
    if toll_gates:
        special_features.append(f"Toll gates: {len(toll_gates)}")
    if bridges:
        special_features.append(f"Bridges: {len(bridges)}")
    
    if special_features:
        pdf.chapter_title("Special Features")
        for feature in special_features:
            pdf.add_hazard_icon("info" if "toll" in feature or "bridge" in feature else "warning")
            pdf.cell(0, 6, feature, 0, 1)
        pdf.ln(5)
    
    # Risk Chart
    if risk_segments:
        pdf.add_risk_chart(risk_segments)
    
    # Add details based on report type
    if type == "full":
        # Full report includes all details
        
        # Add weather info
        if weather:
            pdf.chapter_title("Weather Conditions")
            pdf.set_font('Arial', '', 10)
            for w in weather[:5]:  # Limit to first 5
                location = w.get('location', 'Unknown')
                temp = w.get('temp', 'N/A')
                description = w.get('description', 'N/A')
                weather_text = f"{location}: {temp}C, {description}"
                pdf.cell(0, 6, pdf.clean_text(weather_text), 0, 1)
            pdf.ln(5)
        
        # Sharp Turns
        if turns:
            pdf.chapter_title("Sharp Turns")
            headers = ["Location", "Angle (degrees)"]
            data = [(f"{t['lat']:.4f}, {t['lng']:.4f}", f"{t['angle']}") for t in turns[:10]]
            pdf.add_table(headers, data)
            
            if len(turns) > 10:
                pdf.cell(0, 5, f"... and {len(turns) - 10} more turns", ln=True)
            
            # Add street view for first blind spot
            blind_spots = [turn for turn in turns if turn.get('angle', 0) > 70]
            if blind_spots and api_key:
                pdf.chapter_title("Blind Spot Street View")
                pdf.chapter_body("The following is a street view of the most critical blind spot:")
                spot = blind_spots[0]
                if pdf.add_street_view(spot['lat'], spot['lng'], api_key):
                    location_text = f"Location: {spot['lat']:.4f}, {spot['lng']:.4f} - Angle: {spot['angle']}deg"
                    pdf.cell(0, 5, pdf.clean_text(location_text), ln=True)
                else:
                    pdf.cell(0, 5, "Street view not available for this location.", ln=True)
        
        # Elevation Profile
        if elevation:
            pdf.add_page()
            pdf.chapter_title("Elevation Profile")
            headers = ["Location", "Elevation (m)"]
            data = [(f"{e['location']['lat']:.4f}, {e['location']['lng']:.4f}", f"{e['elevation']:.2f}") for e in elevation[:10]]
            pdf.add_table(headers, data)
            
            # Add elevation chart if enough data points
            if len(elevation) >= 5:
                # Extract data
                elev_values = [e['elevation'] for e in elevation]
                elev_indices = range(len(elev_values))
                
                # Create a line chart
                plt.figure(figsize=(6, 3))
                plt.plot(elev_indices, elev_values)
                plt.title('Elevation Profile')
                plt.xlabel('Points along route')
                plt.ylabel('Elevation (m)')
                
                # Save to a temporary buffer
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=100)
                buf.seek(0)
                
                # Add the chart to the PDF
                pdf.ln(5)
                pdf.image(buf, x=30, w=150)
                plt.close()
        
        # Emergency Services
        pdf.add_page()
        pdf.chapter_title("Emergency Services")
        
        # Hospitals
        if hospital_list:
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 6, f"Hospitals ({len(hospital_list)})", ln=True)
            pdf.set_font('Arial', '', 10)
            
            headers = ["Name", "Location"]
            data = []
            
            for name, vicinity in hospital_list.items():
                data.append((pdf.clean_text(name), pdf.clean_text(vicinity)))
            
            widths = [80, 100]
            pdf.add_table(headers, data[:5], widths)
            
            if len(hospital_list) > 5:
                pdf.cell(0, 5, f"... and {len(hospital_list) - 5} more hospitals", ln=True)
        
        # Police Stations
        if police_stations:
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 6, f"Police Stations ({len(police_stations)})", ln=True)
            pdf.set_font('Arial', '', 10)
            
            headers = ["Name", "Location"]
            data = []
            
            for name, vicinity in police_stations.items():
                data.append((pdf.clean_text(name), pdf.clean_text(vicinity)))
            
            widths = [80, 100]
            pdf.add_table(headers, data[:5], widths)
            
            if len(police_stations) > 5:
                pdf.cell(0, 5, f"... and {len(police_stations) - 5} more police stations", ln=True)
        
        # Amenities
        pdf.add_page()
        pdf.chapter_title("Amenities")
        
        # Fuel Stations
        if petrol_bunks:
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 6, f"Fuel Stations ({len(petrol_bunks)})", ln=True)
            pdf.set_font('Arial', '', 10)
            
            headers = ["Name", "Location"]
            data = []
            
            for name, vicinity in petrol_bunks.items():
                data.append((pdf.clean_text(name), pdf.clean_text(vicinity)))
            
            widths = [80, 100]
            pdf.add_table(headers, data[:5], widths)
            
            if len(petrol_bunks) > 5:
                pdf.cell(0, 5, f"... and {len(petrol_bunks) - 5} more fuel stations", ln=True)
        
        # Food Stops
        if food_stops:
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 6, f"Food Stops ({len(food_stops)})", ln=True)
            pdf.set_font('Arial', '', 10)
            
            headers = ["Name", "Location"]
            data = []
            
            for name, vicinity in food_stops.items():
                data.append((pdf.clean_text(name), pdf.clean_text(vicinity)))
            
            widths = [80, 100]
            pdf.add_table(headers, data[:5], widths)
            
            if len(food_stops) > 5:
                pdf.cell(0, 5, f"... and {len(food_stops) - 5} more food stops", ln=True)
        
        # Regulatory Compliance
        if compliance:
            pdf.add_page()
            pdf.chapter_title("Regulatory Compliance")
            
            # Vehicle Compliance
            if 'vehicle' in compliance and compliance['vehicle']:
                pdf.set_font('Arial', 'B', 11)
                pdf.cell(0, 6, "Vehicle Compliance Requirements", ln=True)
                pdf.set_font('Arial', '', 10)
                
                if 'compliant' in compliance['vehicle']:
                    status = "Compliant" if compliance['vehicle']['compliant'] else "Non-Compliant"
                    pdf.cell(0, 6, f"Status: {status}", ln=True)
                
                if 'violations' in compliance['vehicle'] and compliance['vehicle']['violations']:
                    pdf.set_font('Arial', 'B', 10)
                    pdf.cell(0, 6, "Violations:", ln=True)
                    pdf.set_font('Arial', '', 10)
                    
                    for violation in compliance['vehicle']['violations']:
                        violation_text = pdf.clean_text(f"- {violation.get('description', 'Unknown violation')}")
                        pdf.cell(0, 6, violation_text, ln=True)
                
                if 'requirements' in compliance['vehicle'] and compliance['vehicle']['requirements']:
                    pdf.ln(3)
                    pdf.set_font('Arial', 'B', 10)
                    pdf.cell(0, 6, "Requirements:", ln=True)
                    pdf.set_font('Arial', '', 10)
                    
                    headers = ["Requirement", "Mandatory"]
                    data = []
                    
                    for req in compliance['vehicle']['requirements']:
                        mandatory = "Yes" if req.get('mandatory', False) else "No"
                        req_description = pdf.clean_text(req.get('description', 'Unknown'))
                        data.append((req_description, mandatory))
                    
                    widths = [150, 30]
                    pdf.add_table(headers, data, widths)
            
            # RTSP Compliance
            if 'rtsp' in compliance and compliance['rtsp']:
                pdf.ln(5)
                pdf.set_font('Arial', 'B', 11)
                pdf.cell(0, 6, "Driving Hours & Rest Periods (RTSP)", ln=True)
                pdf.set_font('Arial', '', 10)
                
                if 'compliant' in compliance['rtsp']:
                    status = "Compliant" if compliance['rtsp']['compliant'] else "Non-Compliant"
                    pdf.cell(0, 6, f"Status: {status}", ln=True)
                
                if 'warnings' in compliance['rtsp'] and compliance['rtsp']['warnings']:
                    pdf.set_font('Arial', 'B', 10)
                    pdf.cell(0, 6, "Warnings:", ln=True)
                    pdf.set_font('Arial', '', 10)
                    
                    for warning in compliance['rtsp']['warnings']:
                        warning_text = pdf.clean_text(f"- {warning.get('description', 'Unknown warning')}")
                        pdf.cell(0, 6, warning_text, ln=True)
                
                if 'recommendations' in compliance['rtsp'] and compliance['rtsp']['recommendations']:
                    pdf.set_font('Arial', 'B', 10)
                    pdf.cell(0, 6, "Recommendations:", ln=True)
                    pdf.set_font('Arial', '', 10)
                    
                    for rec in compliance['rtsp']['recommendations']:
                        rec_text = pdf.clean_text(f"- {rec.get('description', 'Unknown recommendation')}")
                        pdf.cell(0, 6, rec_text, ln=True)
        
        # Environmental Analysis
        if environmental:
            pdf.add_page()
            pdf.chapter_title("Environmental Analysis")
            
            # Sensitive Areas
            if 'sensitive_areas' in environmental and environmental['sensitive_areas']:
                pdf.set_font('Arial', 'B', 11)
                pdf.cell(0, 6, "Environmentally Sensitive Areas", ln=True)
                pdf.set_font('Arial', '', 10)
                
                headers = ["Area Name", "Type", "Restrictions"]
                data = []
                
                for area in environmental['sensitive_areas']:
                    restrictions = []
                    for key, value in area.get('restrictions', {}).items():
                        if key == 'speed_limit':
                            restrictions.append(f"Speed: {value} km/h")
                        elif key == 'no_honking' and value:
                            restrictions.append("No Honking")
                        elif key == 'hazmat_prohibited' and value:
                            restrictions.append("No Hazmat")
                        elif key == 'night_driving_prohibited' and value:
                            restrictions.append("No Night Driving")
                    
                    area_name = pdf.clean_text(area.get('name', 'Unknown'))
                    area_type = pdf.clean_text(area.get('type', 'Unknown'))
                    restrictions_text = pdf.clean_text(", ".join(restrictions))
                    
                    data.append((area_name, area_type, restrictions_text))
                
                widths = [70, 50, 60]
                pdf.add_table(headers, data, widths)
            
            # Environmental Advisories
            if 'advisories' in environmental and environmental['advisories']:
                pdf.ln(5)
                pdf.set_font('Arial', 'B', 11)
                pdf.cell(0, 6, "Environmental Advisories", ln=True)
                pdf.set_font('Arial', '', 10)
                
                for advisory in environmental['advisories']:
                    pdf.set_font('Arial', 'B', 10)
                    heading = pdf.clean_text(advisory.get('heading', 'Advisory'))
                    pdf.cell(0, 6, heading, ln=True)
                    pdf.set_font('Arial', '', 10)
                    description = pdf.clean_text(advisory.get('description', ''))
                    pdf.multi_cell(0, 5, description)
                    pdf.ln(2)
    
    elif type == "summary":
        # Summary report - focus on key information
        
        # Key metrics
        pdf.chapter_title("Key Metrics")
        
        # Calculate statistics
        blind_spots = len([turn for turn in turns if turn.get('angle', 0) > 70]) if turns else 0
        high_risk_segments = len([s for s in risk_segments if s.get('risk_level') == 'HIGH']) if risk_segments else 0
        total_segments = len(risk_segments) if risk_segments else 0
        
        risk_percent = (high_risk_segments / total_segments * 100) if total_segments > 0 else 0
        
        # Create table
        headers = ["Metric", "Value"]
        data = [
            ("Sharp Turns", str(len(turns)) if turns else "0"),
            ("Blind Spots", str(blind_spots)),
            ("Toll Gates", str(len(toll_gates)) if toll_gates else "0"),
            ("Bridges", str(len(bridges)) if bridges else "0"),
            ("High Risk Segments", f"{high_risk_segments} ({risk_percent:.1f}%)" if total_segments > 0 else "0")
        ]
        
        widths = [100, 80]
        pdf.add_table(headers, data, widths)
        
        # Safety Tips
        pdf.add_page()
        pdf.chapter_title("Safety Recommendations")
        
        recommendations = [
            "Reduce speed at sharp turns and blind spots",
            "Take regular breaks to avoid fatigue",
            "Stay alert for changing weather conditions",
            "Keep a first aid kit and emergency supplies",
            "Follow all speed limits and road signs"
        ]
        
        for i, rec in enumerate(recommendations):
            pdf.add_hazard_icon("info")
            pdf.cell(0, 10, pdf.clean_text(rec), ln=True)
        
        # Add weather summary
        if weather:
            pdf.ln(5)
            pdf.chapter_title("Weather Conditions")
            
            for w in weather[:3]:
                location = w.get('location', 'Unknown')
                temp = w.get('temp', 'N/A')
                description = w.get('description', 'N/A')
                weather_text = f"{location}: {temp}C, {description}"
                pdf.cell(0, 6, pdf.clean_text(weather_text), 0, 1)
            
            if weather and weather[0].get('description', '').lower() in ['rain', 'thunderstorm', 'snow', 'mist', 'fog']:
                pdf.ln(3)
                pdf.add_hazard_icon("warning")
                warning_text = "Caution: Adverse weather conditions may affect road visibility and grip."
                pdf.cell(0, 10, pdf.clean_text(warning_text), ln=True)
    
    elif type == "driver_briefing":
        # Driver briefing - focus on safety and operational instructions
        
        # Important Route Features
        pdf.chapter_title("Important Route Features")
        
        # List key features
        features = []
        
        # Add any toll gates
        if toll_gates and len(toll_gates) > 0:
            features.append(f"This route includes {len(toll_gates)} toll gate(s)")
        
        # Add sharp turns
        if turns and len(turns) > 0:
            blind_spots = len([turn for turn in turns if turn.get('angle', 0) > 70])
            features.append(f"There are {len(turns)} sharp turns on this route, including {blind_spots} blind spots")
        
        # Add any bridges
        if bridges and len(bridges) > 0:
            features.append(f"This route crosses {len(bridges)} bridge(s)")
        
        # Add any high risk segments
        high_risk_segments = len([s for s in risk_segments if s.get('risk_level') == 'HIGH']) if risk_segments else 0
        if high_risk_segments > 0:
            features.append(f"There are {high_risk_segments} high-risk segments on this route")
        
        # Add any environmental considerations
        if environmental and 'sensitive_areas' in environmental and environmental['sensitive_areas']:
            features.append(f"This route passes through {len(environmental['sensitive_areas'])} environmentally sensitive area(s)")
        
        # Print features
        for feature in features:
            pdf.add_hazard_icon("info")
            pdf.cell(0, 10, pdf.clean_text(feature), ln=True)
        
        # Driver Instructions
        pdf.add_page()
        pdf.chapter_title("Driver Instructions")
        
        # Instructions based on vehicle type
        if vehicle_type in ['heavy_truck', 'tanker']:
            instructions = [
                "Maintain speed limits: 60 km/h on highways, 45 km/h in urban areas, 30 km/h in school zones",
                "Avoid sharp braking, especially when fully loaded",
                "Take mandatory rest stops every 4 hours",
                "Keep at least 3 seconds following distance",
                "Check mirrors and blind spots frequently"
            ]
        elif vehicle_type in ['medium_truck', 'bus']:
            instructions = [
                "Maintain speed limits: 70 km/h on highways, 50 km/h in urban areas, 35 km/h in school zones",
                "Take mandatory rest stops every 4 hours",
                "Keep at least 2.5 seconds following distance",
                "Check mirrors and blind spots frequently",
                "Be aware of pedestrians at all stops"
            ]
        else:  # car or default
            instructions = [
                "Maintain speed limits: 80 km/h on highways, 60 km/h in urban areas, 40 km/h in school zones",
                "Take breaks every 2 hours to prevent fatigue",
                "Keep at least 2 seconds following distance",
                "Use caution at sharp turns and blind spots",
                "Drive according to weather and road conditions"
            ]
        
        # Print instructions
        for instruction in instructions:
            pdf.add_hazard_icon("warning")
            pdf.cell(0, 10, pdf.clean_text(instruction), ln=True)
        
        # Emergency Contacts
        if emergency and 'plan' in emergency and 'emergency_contacts' in emergency['plan']:
            pdf.add_page()
            pdf.chapter_title("Emergency Contacts")
            
            headers = ["Name", "Contact", "Type"]
            data = []
            
            for contact in emergency['plan']['emergency_contacts'][:10]:
                contact_info = contact.get('number', contact.get('vicinity', 'Unknown'))
                contact_name = pdf.clean_text(contact.get('name', 'Unknown'))
                contact_info_clean = pdf.clean_text(contact_info)
                contact_type = pdf.clean_text(contact.get('type', 'general'))
                data.append((contact_name, contact_info_clean, contact_type))
            
            widths = [80, 60, 40]
            pdf.add_table(headers, data, widths)
        
        # Emergency Instructions
        if emergency and 'plan' in emergency and 'general_instructions' in emergency['plan']:
            pdf.ln(5)
            pdf.chapter_title("Emergency Instructions")
            
            for instruction in emergency['plan']['general_instructions']:
                clean_instruction = pdf.clean_text(f"* {instruction}")
                pdf.cell(0, 6, clean_instruction, ln=True)
            
            # Add high risk segment instructions
            if 'high_risk_segments' in emergency['plan'] and emergency['plan']['high_risk_segments']:
                pdf.ln(3)
                pdf.set_font('Arial', 'B', 11)
                pdf.cell(0, 6, "Instructions for High Risk Segments:", ln=True)
                pdf.set_font('Arial', '', 10)
                
                for segment in emergency['plan']['high_risk_segments']:
                    for instruction in segment.get('emergency_instructions', []):
                        clean_instruction = pdf.clean_text(f"* {instruction}")
                        pdf.cell(0, 6, clean_instruction, ln=True)
    
    # Safe Driving Recommendations (for all report types)
    pdf.add_page()
    pdf.chapter_title("Safe Driving Recommendations")
    
    recommendations = [
        "Maintain appropriate speed according to road conditions and posted limits",
        "Take regular breaks to avoid fatigue (recommended every 2-3 hours)",
        "Stay alert when navigating sharp turns and areas with elevation changes",
        "Be extra cautious when passing through school zones and residential areas",
        "Monitor weather conditions throughout the journey",
        "Ensure compliance with all regulatory requirements for your vehicle type"
    ]
    
    for i, rec in enumerate(recommendations):
        pdf.add_hazard_icon("success")
        pdf.cell(0, 10, pdf.clean_text(rec), ln=True)
    
    # Footer note
    pdf.ln(10)
    pdf.set_font('Arial', 'I', 10)
    footer_text = "This report was automatically generated by the Route Analytics system. Always use your own judgment and follow official road rules and regulations."
    pdf.multi_cell(0, 5, pdf.clean_text(footer_text))
    
    # Save the PDF
    try:
        pdf.output(filename)
        return filename
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None