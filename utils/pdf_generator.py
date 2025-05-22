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
            
        # Create a bar chart with CORRECT colors
        plt.figure(figsize=(6, 4))
        
        # Fixed color mapping: High=Red, Medium=Orange, Low=Green
        bars = plt.bar(['High Risk', 'Medium Risk', 'Low Risk'], [high, medium, low], 
                color=['#dc3545', '#fd7e14', '#28a745'])  # Red, Orange, Green
        
        # Add counts above bars
        for bar in bars:
            height = bar.get_height()
            if height > 0:  # Only show label if there's a value
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{int(height)}', ha='center', va='bottom', fontweight='bold')
        
        plt.ylim(0, max(max(high, medium, low) + 1, 1))
        plt.title('Risk Level Distribution Along Route', fontsize=14, fontweight='bold')
        plt.ylabel('Number of Segments')
        plt.grid(axis='y', alpha=0.3)
        
        # Add legend
        plt.legend(['High Risk (Extreme Caution)', 'Medium Risk (Caution)', 'Low Risk (Normal)'], 
                  loc='upper right', fontsize=8)
        
        # Save to a temporary buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        
        # Add the chart to the PDF
        self.chapter_title("Risk Analysis")
        
        # Overall risk assessment
        if high > 0:
            risk_level = "HIGH"
            risk_color = "RED"
        elif medium > 0:
            risk_level = "MEDIUM" 
            risk_color = "ORANGE"
        else:
            risk_level = "LOW"
            risk_color = "GREEN"
            
        self.set_font('Arial', 'B', 12)
        self.cell(0, 6, f"Overall Route Risk Level: {risk_level} ({risk_color})", 0, 1)
        self.ln(2)
        
        # Add the chart
        self.image(buf, x=25, w=160)
        self.ln(10)
        plt.close()
        
        # Add risk description
        if high > 0:
            self.chapter_body("This route contains HIGH-RISK segments that require EXTREME CAUTION. Reduce speed, increase following distance, and be prepared for hazardous conditions.")
        elif medium > 0:
            self.chapter_body("This route contains MEDIUM-RISK segments. Exercise increased caution and follow recommended safety measures.")
        else:
            self.chapter_body("This route is generally LOW-RISK. Follow standard safety procedures for a safe journey.")
    
    def add_weather_chart(self, weather_data):
        """Add a weather conditions chart"""
        if not weather_data or len(weather_data) < 2:
            return
        
        # Extract data for chart
        locations = []
        temperatures = []
        descriptions = []
        
        for w in weather_data:
            locations.append(w.get('location', 'Unknown')[:10])  # Truncate long names
            temperatures.append(w.get('temp', 0))
            descriptions.append(w.get('description', 'Unknown'))
        
        # Create temperature chart
        plt.figure(figsize=(8, 5))
        
        # Create bar chart for temperatures
        bars = plt.bar(range(len(locations)), temperatures, 
                      color=['#ff6b6b' if t > 35 else '#4ecdc4' if t < 10 else '#45b7d1' 
                            for t in temperatures])
        
        # Add temperature values on bars
        for i, (bar, temp, desc) in enumerate(zip(bars, temperatures, descriptions)):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{temp}°C', ha='center', va='bottom', fontweight='bold')
            
            # Add weather description below x-axis
            plt.text(bar.get_x() + bar.get_width()/2., -5,
                    desc[:8], ha='center', va='top', fontsize=8, rotation=45)
        
        plt.xlabel('Locations Along Route')
        plt.ylabel('Temperature (°C)')
        plt.title('Weather Conditions Along Route', fontsize=14, fontweight='bold')
        plt.xticks(range(len(locations)), locations, rotation=45)
        plt.grid(axis='y', alpha=0.3)
        
        # Adjust layout to prevent label cutoff
        plt.tight_layout()
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        
        # Add to PDF
        self.chapter_title("Weather Conditions Along Route")
        self.image(buf, x=15, w=180)
        self.ln(10)
        plt.close()
        
        # Add weather warnings if any
        adverse_conditions = []
        for w in weather_data:
            temp = w.get('temp', 20)
            desc = w.get('description', '').lower()
            location = w.get('location', 'Unknown')
            
            if temp > 40:
                adverse_conditions.append(f"EXTREME HEAT at {location}: {temp}°C")
            elif temp < 5:
                adverse_conditions.append(f"COLD CONDITIONS at {location}: {temp}°C")
            
            if any(condition in desc for condition in ['rain', 'storm', 'fog', 'snow']):
                adverse_conditions.append(f"ADVERSE WEATHER at {location}: {desc.title()}")
        
        if adverse_conditions:
            self.set_font('Arial', 'B', 11)
            self.set_text_color(220, 20, 20)  # Red text
            self.cell(0, 6, "WEATHER WARNINGS:", ln=True)
            self.set_text_color(0, 0, 0)  # Reset to black
            self.set_font('Arial', '', 10)
            
            for warning in adverse_conditions:
                self.cell(0, 6, f"* {self.clean_text(warning)}", ln=True)
            self.ln(3)
    
    def add_major_highways_section(self, major_highways):
        """Add major highways section"""
        if not major_highways:
            return
            
        self.chapter_title("Major Highways on Route")
        
        # Create a formatted list of highways
        highway_text = "This route uses the following major highways:\n\n"
        
        for i, highway in enumerate(major_highways, 1):
            highway_text += f"{i}. {highway}\n"
        
        highway_text += f"\nTotal Major Highways: {len(major_highways)}"
        
        # Add important notes
        highway_text += "\n\nIMPORTANT HIGHWAY NOTES:"
        highway_text += "\n* Follow posted speed limits on highways"
        highway_text += "\n* Maintain safe following distances"
        highway_text += "\n* Use designated lanes for your vehicle type"
        highway_text += "\n* Be aware of toll collection points"
        highway_text += "\n* Watch for highway patrol and enforcement"
        
        self.chapter_body(highway_text)
    
    def add_all_sharp_turns(self, turns, api_key=None):
        """Add detailed section for ALL sharp turns"""
        if not turns:
            return
            
        self.add_page()
        self.chapter_title("All Sharp Turns Analysis")
        
        # Separate high-risk turns (>70°) and regular sharp turns
        high_risk_turns = [t for t in turns if t.get('angle', 0) > 70]
        regular_turns = [t for t in turns if t.get('angle', 0) <= 70]
        
        # Summary statistics
        summary_text = f"SHARP TURNS SUMMARY:\n"
        summary_text += f"* Total Sharp Turns: {len(turns)}\n"
        summary_text += f"* High-Risk Turns (>70°): {len(high_risk_turns)}\n"
        summary_text += f"* Regular Sharp Turns (<=70°): {len(regular_turns)}\n"
        
        if turns:
            max_angle = max(t.get('angle', 0) for t in turns)
            avg_angle = sum(t.get('angle', 0) for t in turns) / len(turns)
            summary_text += f"* Most Severe Turn: {max_angle:.1f}°\n"
            summary_text += f"* Average Turn Angle: {avg_angle:.1f}°\n"
        
        self.chapter_body(summary_text)
        
        # HIGH-RISK TURNS TABLE
        if high_risk_turns:
            self.chapter_title("HIGH-RISK TURNS (>70° - EXTREME CAUTION REQUIRED)")
            
            headers = ["#", "Location (Lat, Lng)", "Angle", "Risk Level", "Action Required"]
            data = []
            
            for i, turn in enumerate(high_risk_turns, 1):
                lat = turn.get('lat', 0)
                lng = turn.get('lng', 0)
                angle = turn.get('angle', 0)
                
                # Determine risk level based on angle
                if angle > 90:
                    risk_level = "EXTREME"
                    action = "REDUCE SPEED TO 20-30 KM/H"
                elif angle > 80:
                    risk_level = "VERY HIGH"
                    action = "REDUCE SPEED TO 30-40 KM/H"
                else:
                    risk_level = "HIGH"
                    action = "REDUCE SPEED TO 40-50 KM/H"
                
                data.append([
                    str(i),
                    f"{lat:.4f}, {lng:.4f}",
                    f"{angle:.1f}°",
                    risk_level,
                    action
                ])
            
            widths = [15, 50, 25, 30, 70]
            self.add_table(headers, data, widths)
            
            # Add street view for most critical turn
            if api_key and high_risk_turns:
                most_critical = max(high_risk_turns, key=lambda x: x.get('angle', 0))
                self.ln(5)
                self.set_font('Arial', 'B', 11)
                self.cell(0, 6, f"Street View - Most Critical Turn ({most_critical['angle']:.1f}°):", ln=True)
                
                if self.add_street_view(most_critical['lat'], most_critical['lng'], api_key):
                    self.ln(3)
                    self.set_font('Arial', '', 10)
                    location_text = f"Location: {most_critical['lat']:.4f}, {most_critical['lng']:.4f}"
                    self.cell(0, 5, self.clean_text(location_text), ln=True)
        
        # REGULAR SHARP TURNS TABLE  
        if regular_turns:
            self.chapter_title("Regular Sharp Turns (<=70° - Caution Required)")
            
            headers = ["#", "Location (Lat, Lng)", "Angle", "Recommended Speed"]
            data = []
            
            for i, turn in enumerate(regular_turns, 1):
                lat = turn.get('lat', 0)
                lng = turn.get('lng', 0)
                angle = turn.get('angle', 0)
                
                # Recommended speed based on angle
                if angle > 60:
                    rec_speed = "50-60 KM/H"
                elif angle > 45:
                    rec_speed = "60-70 KM/H"
                else:
                    rec_speed = "NORMAL SPEED"
                
                data.append([
                    str(i),
                    f"{lat:.4f}, {lng:.4f}",
                    f"{angle:.1f}°",
                    rec_speed
                ])
            
            widths = [15, 70, 30, 50]
            self.add_table(headers, data[:15], widths)  # Limit to first 15 to save space
            
            if len(regular_turns) > 15:
                self.cell(0, 5, f"... and {len(regular_turns) - 15} more regular sharp turns", ln=True)
    
    def add_all_blind_spots_with_maps(self, turns, api_key=None):
        """Add detailed blind spots section with maps"""
        blind_spots = [t for t in turns if t.get('angle', 0) > 70] if turns else []
        
        if not blind_spots:
            self.chapter_title("Blind Spots Analysis")
            self.chapter_body("No blind spots (turns >70°) detected on this route.")
            return
        
        self.add_page()
        self.chapter_title("BLIND SPOTS - CRITICAL SAFETY INFORMATION")
        
        # Warning message
        warning_text = "CRITICAL WARNING: This section contains all blind spots (turns >70°) on your route.\n"
        warning_text += "These locations require EXTREME CAUTION and REDUCED SPEED.\n\n"
        warning_text += f"Total Blind Spots Identified: {len(blind_spots)}\n"
        warning_text += f"Most Severe Blind Spot: {max(blind_spots, key=lambda x: x.get('angle', 0))['angle']:.1f}°"
        
        self.set_font('Arial', 'B', 11)
        self.set_text_color(220, 20, 20)  # Red text for warning
        self.multi_cell(0, 6, self.clean_text(warning_text))
        self.set_text_color(0, 0, 0)  # Reset to black
        self.ln(5)
        
        # Detailed table of all blind spots
        headers = ["#", "Coordinates", "Angle", "Severity", "Speed Limit", "Special Instructions"]
        data = []
        
        for i, spot in enumerate(blind_spots, 1):
            lat = spot.get('lat', 0)
            lng = spot.get('lng', 0)
            angle = spot.get('angle', 0)
            
            # Determine severity and instructions
            if angle > 90:
                severity = "EXTREME"
                speed_limit = "20-25 KM/H"
                instructions = "CRAWL SPEED, HORN, HEADLIGHTS"
            elif angle > 85:
                severity = "VERY HIGH"
                speed_limit = "25-30 KM/H" 
                instructions = "VERY SLOW, USE HORN"
            elif angle > 80:
                severity = "HIGH"
                speed_limit = "30-35 KM/H"
                instructions = "SLOW DOWN, BE READY TO STOP"
            else:
                severity = "MODERATE"
                speed_limit = "35-40 KM/H"
                instructions = "REDUCE SPEED, STAY ALERT"
            
            data.append([
                str(i),
                f"{lat:.4f}\n{lng:.4f}",
                f"{angle:.1f}°",
                severity,
                speed_limit,
                instructions
            ])
        
        widths = [15, 35, 25, 25, 30, 60]
        self.add_table(headers, data, widths)
        
        # Add street views for top 3 most critical blind spots
        if api_key and blind_spots:
            self.add_page()
            self.chapter_title("Street Views - Most Critical Blind Spots")
            
            # Sort by angle (most critical first)
            critical_spots = sorted(blind_spots, key=lambda x: x.get('angle', 0), reverse=True)[:3]
            
            for i, spot in enumerate(critical_spots, 1):
                self.set_font('Arial', 'B', 12)
                header_text = f"Blind Spot #{i} - {spot['angle']:.1f}° (EXTREME CAUTION)"
                self.cell(0, 8, self.clean_text(header_text), ln=True)
                
                if self.add_street_view(spot['lat'], spot['lng'], api_key):
                    self.ln(2)
                    self.set_font('Arial', '', 10)
                    info_text = f"Location: {spot['lat']:.4f}, {spot['lng']:.4f} | "
                    info_text += f"Recommended Speed: 20-30 km/h | Use Horn & Headlights"
                    self.cell(0, 5, self.clean_text(info_text), ln=True)
                else:
                    self.set_font('Arial', '', 10)
                    self.cell(0, 5, "Street view not available for this location.", ln=True)
                
                self.ln(5)
    
    def add_street_view(self, lat, lng, api_key):
        """Add a Google Street View image for a location"""
        try:
            url = f"https://maps.googleapis.com/maps/api/streetview?size=600x300&location={lat},{lng}&fov=80&heading=70&pitch=0&key={api_key}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200 and len(response.content) > 1000:  # Valid image
                # Save image to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp:
                    temp.write(response.content)
                    temp_path = temp.name
                
                # Add the image to the PDF
                self.image(temp_path, x=15, w=180)
                
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
                vehicle_type="car", type="full", api_key=None, major_highways=None):
    """
    Generate a PDF report based on the route analysis
    
    Args:
        type: Type of report to generate ('full', 'summary', 'driver_briefing')
        major_highways: List of major highways on the route
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
    if not major_highways:
        major_highways = []
    
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
    
    # Add Major Highways Section
    pdf.add_major_highways_section(major_highways)
    
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
    
    # Risk Chart (with corrected colors)
    if risk_segments:
        pdf.add_risk_chart(risk_segments)
    
    # Weather Chart
    if weather:
        pdf.add_weather_chart(weather)
    
    # Add details based on report type
    if type == "full":
        # Full report includes all details
        
        # Add ALL sharp turns analysis
        pdf.add_all_sharp_turns(turns, api_key)
        
        # Add ALL blind spots with maps
        pdf.add_all_blind_spots_with_maps(turns, api_key)
        
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
                plt.figure(figsize=(8, 4))
                plt.plot(elev_indices, elev_values, linewidth=2, color='#2E86AB')
                plt.fill_between(elev_indices, elev_values, alpha=0.3, color='#A23B72')
                plt.title('Elevation Profile Along Route', fontsize=14, fontweight='bold')
                plt.xlabel('Points along route')
                plt.ylabel('Elevation (m)')
                plt.grid(True, alpha=0.3)
                
                # Save to a temporary buffer
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                buf.seek(0)
                
                # Add the chart to the PDF
                pdf.ln(5)
                pdf.image(buf, x=15, w=180)
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
            pdf.add_table(headers, data[:10], widths)
            
            if len(hospital_list) > 10:
                pdf.cell(0, 5, f"... and {len(hospital_list) - 10} more hospitals", ln=True)
        
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
            pdf.add_table(headers, data[:10], widths)
            
            if len(police_stations) > 10:
                pdf.cell(0, 5, f"... and {len(police_stations) - 10} more police stations", ln=True)
        
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
            pdf.add_table(headers, data[:10], widths)
            
            if len(petrol_bunks) > 10:
                pdf.cell(0, 5, f"... and {len(petrol_bunks) - 10} more fuel stations", ln=True)
        
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
            pdf.add_table(headers, data[:10], widths)
            
            if len(food_stops) > 10:
                pdf.cell(0, 5, f"... and {len(food_stops) - 10} more food stops", ln=True)
        
        # Schools Section
        if schools:
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 11)
            pdf.set_text_color(220, 20, 20)  # Red text for schools (safety critical)
            pdf.cell(0, 6, f"SCHOOLS - SPEED LIMIT ZONES ({len(schools)})", ln=True)
            pdf.set_text_color(0, 0, 0)  # Reset to black
            pdf.set_font('Arial', '', 10)
            
            # Add warning
            school_warning = "CRITICAL: Reduce speed to 30-40 km/h when passing schools during school hours (8-9:30 AM, 2:30-4 PM)"
            pdf.multi_cell(0, 5, pdf.clean_text(school_warning))
            pdf.ln(3)
            
            headers = ["School Name", "Location", "Speed Limit"]
            data = []
            
            for name, vicinity in schools.items():
                # Determine speed limit based on vehicle type
                if vehicle_type in ['heavy_truck', 'tanker']:
                    speed_limit = "30 KM/H"
                elif vehicle_type in ['medium_truck', 'bus']:
                    speed_limit = "35 KM/H"
                else:
                    speed_limit = "40 KM/H"
                
                data.append((pdf.clean_text(name), pdf.clean_text(vicinity), speed_limit))
            
            widths = [60, 90, 30]
            pdf.add_table(headers, data[:10], widths)
            
            if len(schools) > 10:
                pdf.cell(0, 5, f"... and {len(schools) - 10} more schools", ln=True)
        
        # Environmental Analysis (if exists)
        if environmental and 'sensitive_areas' in environmental and environmental['sensitive_areas']:
            pdf.add_page()
            pdf.chapter_title("Environmental Analysis")
            
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
            ("Schools", str(len(schools)) if schools else "0"),
            ("High Risk Segments", f"{high_risk_segments} ({risk_percent:.1f}%)" if total_segments > 0 else "0")
        ]
        
        widths = [100, 80]
        pdf.add_table(headers, data, widths)
        
        # Safety Tips
        pdf.add_page()
        pdf.chapter_title("Safety Recommendations")
        
        recommendations = [
            "Reduce speed at sharp turns and blind spots",
            "Exercise extreme caution near schools during school hours",
            "Take regular breaks to avoid fatigue",
            "Stay alert for changing weather conditions",
            "Keep a first aid kit and emergency supplies",
            "Follow all speed limits and road signs"
        ]
        
        for i, rec in enumerate(recommendations):
            pdf.add_hazard_icon("info")
            pdf.cell(0, 10, pdf.clean_text(rec), ln=True)
    
    elif type == "driver_briefing":
        # Driver briefing - focus on safety and operational instructions
        
        # Important Route Features
        pdf.chapter_title("Important Route Features")
        
        # List key features
        features = []
        
        # Add major highways
        if major_highways:
            features.append(f"Major Highways: {', '.join(major_highways[:3])}")
            if len(major_highways) > 3:
                features.append(f"Plus {len(major_highways) - 3} more highways")
        
        # Add any toll gates
        if toll_gates and len(toll_gates) > 0:
            features.append(f"This route includes {len(toll_gates)} toll gate(s)")
        
        # Add sharp turns
        if turns and len(turns) > 0:
            blind_spots = len([turn for turn in turns if turn.get('angle', 0) > 70])
            features.append(f"There are {len(turns)} sharp turns on this route, including {blind_spots} blind spots")
        
        # Add schools
        if schools and len(schools) > 0:
            features.append(f"CAUTION: {len(schools)} school(s) along route - reduce speed during school hours")
        
        # Add any bridges
        if bridges and len(bridges) > 0:
            features.append(f"This route crosses {len(bridges)} bridge(s)")
        
        # Add any high risk segments
        high_risk_segments = len([s for s in risk_segments if s.get('risk_level') == 'HIGH']) if risk_segments else 0
        if high_risk_segments > 0:
            features.append(f"ALERT: {high_risk_segments} high-risk segments on this route")
        
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
                "Speed limits: 60 km/h highways, 45 km/h urban, 30 km/h school zones",
                "Avoid sharp braking, especially when fully loaded",
                "Take mandatory rest stops every 4 hours",
                "Keep at least 3 seconds following distance",
                "Check mirrors and blind spots frequently"
            ]
        elif vehicle_type in ['medium_truck', 'bus']:
            instructions = [
                "Speed limits: 70 km/h highways, 50 km/h urban, 35 km/h school zones", 
                "Take mandatory rest stops every 4 hours",
                "Keep at least 2.5 seconds following distance",
                "Check mirrors and blind spots frequently",
                "Be aware of pedestrians at all stops"
            ]
        else:  # car or default
            instructions = [
                "Speed limits: 80 km/h highways, 60 km/h urban, 40 km/h school zones",
                "Take breaks every 2 hours to prevent fatigue",
                "Keep at least 2 seconds following distance",
                "Use caution at sharp turns and blind spots",
                "Drive according to weather and road conditions"
            ]
        
        # Print instructions
        for instruction in instructions:
            pdf.add_hazard_icon("warning")
            pdf.cell(0, 10, pdf.clean_text(instruction), ln=True)
        
         # Add top blind spots for driver briefing
        if turns:
            blind_spots = [t for t in turns if t.get('angle', 0) > 70]
            if blind_spots:
                pdf.add_page()
                pdf.chapter_title("CRITICAL BLIND SPOTS - DRIVER ALERT")
                
                # Show top 5 most critical
                critical_spots = sorted(blind_spots, key=lambda x: x.get('angle', 0), reverse=True)[:5]
                
                headers = ["#", "Location", "Angle", "Speed Limit"]
                data = []
                
                for i, spot in enumerate(critical_spots, 1):
                    data.append([
                        str(i),
                        f"{spot['lat']:.4f}, {spot['lng']:.4f}",
                        f"{spot['angle']:.1f}°",
                        "20-30 KM/H"
                    ])
                
                pdf.add_table(headers, data)
        
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