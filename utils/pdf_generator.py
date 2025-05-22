# Complete Enhanced PDF Generator with corrected risk analysis and comprehensive maps
# utils/pdf_generator.py

from fpdf import FPDF
import os
import datetime
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import requests
import tempfile
import json
import matplotlib.patches as mpatches

class RoutePDF(FPDF):
    def __init__(self, title=None):
        super().__init__()
        self.title = title or "Route Analytics Report"
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
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
    
    def add_corrected_risk_chart(self, risk_segments):
        # """Add CORRECTED risk chart emphasizing high risk when applicable"""
        # # Count risk levels
        high = len([s for s in risk_segments if s.get('risk_level') == 'HIGH'])
        medium = len([s for s in risk_segments if s.get('risk_level') == 'MEDIUM'])
        low = len([s for s in risk_segments if s.get('risk_level') == 'LOW'])

        # # If no risk data, set default values to highlight high risk
        # if high + medium + low == 0:
        #     high, medium, low = 50, 0, 0  # Emphasize high risk

        # # Create a bar chart
        # plt.figure(figsize=(10, 6))

        # # Data for the chart
        # categories = ['Low Risk', 'Medium Risk', 'High Risk']
        # values = [low, medium, high]

        # # Colors for the bars
        # colors = ['#28a745', '#fd7e14', '#dc3545']  # Red, Orange, Green

        # # Create bars with specific styling
        # bars = plt.bar(categories, values, color=colors, edgecolor='black', linewidth=0.5, width=0.6)

        # # Add value labels on top of bars
        # for bar, value in zip(bars, values):
        #     height = bar.get_height()
        #     plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
        #             str(int(value)), ha='center', va='bottom',
        #             fontweight='bold', fontsize=14, color='black')

        # # Customize the chart
        # plt.title('Risk Level Distribution Along Route', fontsize=16, fontweight='bold', pad=20)
        # plt.ylabel('Number of Segments', fontsize=12, fontweight='bold')

        # # Set y-axis limit
        # max_value = max(values)
        # plt.ylim(0, max(50, max_value + 5))

        # # Add grid
        # plt.grid(axis='y', alpha=0.3, linestyle='-', linewidth=0.5)

        # # Add legend
        # legend_patches = [
        #     mpatches.Patch(color='#dc3545', label='High Risk (Extreme Caution)'),
        #     mpatches.Patch(color='#fd7e14', label='Medium Risk'),
        #     mpatches.Patch(color='#28a745', label='Low Risk')
        # ]
        # plt.legend(handles=legend_patches, loc='upper right', fontsize=10)

        # # Remove top and right spines
        # ax = plt.gca()
        # ax.spines['top'].set_visible(False)
        # ax.spines['right'].set_visible(False)

        # # Improve layout
        # plt.tight_layout()

        # # Save to buffer
        # buf = io.BytesIO()
        # plt.savefig(buf, format='png', dpi=200, bbox_inches='tight', facecolor='white')
        # buf.seek(0)

        # # Add the chart to the PDF
        # self.chapter_title("Driver Briefing")
        # self.image(buf, x=10, w=190)
        # self.ln(10)
        # plt.close()

        # Overall risk assessment
        if high > 0:
            risk_level = "HIGH"
            risk_message = "This route contains HIGH-RISK segments requiring EXTREME CAUTION."
        elif medium > 0:
            risk_level = "MEDIUM"
            risk_message = "This route contains MEDIUM-RISK segments requiring increased caution."
        else:
            risk_level = "LOW"
            risk_message = "This route is generally LOW-RISK with normal driving conditions."

        self.set_font('Arial', 'B', 12)
        self.cell(0, 8, f"Overall Route Risk Level: {risk_level}", 0, 1)
        self.ln(2)

        # Add risk description
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 6, self.clean_text(risk_message))
        self.ln(5)


    def add_street_view_image(self, lat, lng, api_key, heading=0, pitch=0, fov=90):
        """Add Google Street View image with specific viewing angle"""
        try:
            url = f"https://maps.googleapis.com/maps/api/streetview?size=600x400&location={lat},{lng}&heading={heading}&pitch={pitch}&fov={fov}&key={api_key}"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200 and len(response.content) > 1000:
                # Save image to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp:
                    temp.write(response.content)
                    temp_path = temp.name
                
                # Add image to PDF
                self.image(temp_path, x=15, w=180)
                
                # Clean up
                os.unlink(temp_path)
                return True
            
            return False
        except Exception as e:
            print(f"Error adding street view: {e}")
            return False

    def add_static_map_image(self, center_lat, center_lng, markers, api_key, zoom=15, size="640x400"):
        """Add Google Static Maps image with markers"""
        try:
            base_url = "https://maps.googleapis.com/maps/api/staticmap"
            params = [
                f"center={center_lat},{center_lng}",
                f"zoom={zoom}",
                f"size={size}",
                "maptype=roadmap"
            ]
            
            # Add markers
            for marker in markers:
                color = marker.get('color', 'red')
                label = marker.get('label', '')
                lat = marker.get('lat')
                lng = marker.get('lng')
                params.append(f"markers=color:{color}|label:{label}|{lat},{lng}")
            
            params.append(f"key={api_key}")
            
            url = f"{base_url}?" + "&".join(params)
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp:
                    temp.write(response.content)
                    temp_path = temp.name
                
                self.image(temp_path, x=15, w=180)
                os.unlink(temp_path)
                return True
            
            return False
        except Exception as e:
            print(f"Error adding static map: {e}")
            return False

    def add_enhanced_blind_spots_section(self, turns, route_polyline=None, api_key=None):
        """Add comprehensive blind spots analysis with maps and street views"""
        blind_spots = [t for t in turns if t.get('angle', 0) > 70] if turns else []
        
        if not blind_spots:
            self.chapter_title("Blind Spots Analysis")
            self.chapter_body("No blind spots (turns >70°) detected on this route.")
            return
        
        self.add_page()
        self.chapter_title("BLIND SPOTS - CRITICAL SAFETY ANALYSIS")
        
        # Summary section
        summary_text = f"CRITICAL ALERT: {len(blind_spots)} blind spots identified on this route.\n\n"
        summary_text += "Blind spots are sharp turns with angles greater than 70° that significantly limit visibility.\n"
        summary_text += "These locations require EXTREME CAUTION and REDUCED SPEED.\n\n"
        
        if blind_spots:
            max_angle = max(blind_spots, key=lambda x: x.get('angle', 0))['angle']
            avg_angle = sum(spot.get('angle', 0) for spot in blind_spots) / len(blind_spots)
            summary_text += f"Most Severe Blind Spot: {max_angle:.1f}°\n"
            summary_text += f"Average Blind Spot Angle: {avg_angle:.1f}°"
        
        self.set_font('Arial', 'B', 11)
        self.set_text_color(220, 20, 20)  # Red text for warning
        self.multi_cell(0, 6, self.clean_text(summary_text))
        self.set_text_color(0, 0, 0)  # Reset to black
        self.ln(5)
        
        # Process each blind spot with detailed analysis
        for i, blind_spot in enumerate(blind_spots, 1):
            self.add_page()
            
            # Blind spot header
            self.set_font('Arial', 'B', 16)
            self.set_text_color(220, 20, 20)
            header_text = f"BLIND SPOT #{i} - {blind_spot['angle']:.1f}° ANGLE"
            self.cell(0, 12, self.clean_text(header_text), 0, 1, 'C')
            self.set_text_color(0, 0, 0)
            self.ln(5)
            
            # Location and severity details
            self.set_font('Arial', 'B', 12)
            self.cell(0, 8, "LOCATION & SEVERITY DETAILS:", ln=True)
            self.set_font('Arial', '', 11)
            
            angle = blind_spot['angle']
            if angle > 90:
                severity = "EXTREME DANGER"
                speed_rec = "15-20 km/h"
                risk_level = "MAXIMUM"
            elif angle > 85:
                severity = "VERY HIGH RISK"
                speed_rec = "20-25 km/h"
                risk_level = "VERY HIGH"
            elif angle > 80:
                severity = "HIGH RISK"
                speed_rec = "25-30 km/h"
                risk_level = "HIGH"
            else:
                severity = "MODERATE RISK"
                speed_rec = "30-35 km/h"
                risk_level = "MODERATE"
            
            details = f"Coordinates: {blind_spot['lat']:.6f}, {blind_spot['lng']:.6f}\n"
            details += f"Turn Angle: {blind_spot['angle']:.1f}°\n"
            details += f"Severity Classification: {severity}\n"
            details += f"Risk Level: {risk_level}\n"
            details += f"Maximum Safe Speed: {speed_rec}\n"
            
            self.multi_cell(0, 6, self.clean_text(details))
            self.ln(5)
            
            # Safety instructions
            self.set_font('Arial', 'B', 12)
            self.set_text_color(220, 20, 20)
            self.cell(0, 8, "MANDATORY SAFETY INSTRUCTIONS:", ln=True)
            self.set_text_color(0, 0, 0)
            self.set_font('Arial', '', 11)
            
            instructions = [
                f"REDUCE SPEED to {speed_rec} BEFORE entering the turn",
                "SOUND HORN continuously to alert oncoming traffic",
                "TURN ON HEADLIGHTS even during daytime",
                "STAY STRICTLY in your lane - DO NOT cut corners",
                "BE PREPARED TO STOP IMMEDIATELY if necessary",
                "AVOID OVERTAKING within 200m of this location",
                "INCREASE FOLLOWING DISTANCE to 5+ seconds"
            ]
            
            for instruction in instructions:
                self.cell(8, 6, ".", ln=False)
                self.cell(0, 6, self.clean_text(instruction), ln=True)
            
            self.ln(5)
            
            # Add map for this blind spot
            if api_key:
                self.set_font('Arial', 'B', 12)
                self.cell(0, 8, "LOCATION MAP:", ln=True)
                
                # Create markers for the map
                markers = [
                    {
                        'lat': blind_spot['lat'],
                        'lng': blind_spot['lng'],
                        'color': 'red',
                        'label': str(i)
                    }
                ]
                
                if self.add_static_map_image(blind_spot['lat'], blind_spot['lng'], markers, api_key, zoom=16):
                    self.ln(3)
                    self.set_font('Arial', 'I', 10)
                    self.cell(0, 5, f"Blind Spot Location: {blind_spot['lat']:.6f}, {blind_spot['lng']:.6f}", ln=True)
                else:
                    self.set_font('Arial', '', 10)
                    self.cell(0, 5, "Map not available for this location.", ln=True)
                
                self.ln(5)
                
                # Add street view
                self.set_font('Arial', 'B', 12)
                self.cell(0, 8, "STREET VIEW:", ln=True)
                
                if self.add_street_view_image(blind_spot['lat'], blind_spot['lng'], api_key):
                    self.ln(3)
                    self.set_font('Arial', 'I', 10)
                    self.cell(0, 5, f"Street view at: {blind_spot['lat']:.6f}, {blind_spot['lng']:.6f}", ln=True)
                else:
                    self.set_font('Arial', '', 10)
                    self.cell(0, 5, "Street view not available for this location.", ln=True)
            
            self.ln(10)

    def add_all_sharp_turns_with_street_view(self, turns, api_key=None):
        """Add ALL sharp turns with street view images"""
        if not turns:
            return
            
        self.add_page()
        self.chapter_title("COMPLETE SHARP TURNS ANALYSIS WITH STREET VIEWS")
        
        # Summary
        blind_spots = [t for t in turns if t.get('angle', 0) > 70]
        moderate_turns = [t for t in turns if 45 <= t.get('angle', 0) <= 70]
        
        summary = f"COMPREHENSIVE SHARP TURNS ANALYSIS:\n\n"
        summary += f"Total Sharp Turns: {len(turns)}\n"
        summary += f"• Blind Spots (>70°): {len(blind_spots)}\n"
        summary += f"• Moderate Sharp Turns (45-70°): {len(moderate_turns)}\n\n"
        
        if turns:
            max_angle = max(t.get('angle', 0) for t in turns)
            avg_angle = sum(t.get('angle', 0) for t in turns) / len(turns)
            summary += f"Most Severe Turn: {max_angle:.1f}°\n"
            summary += f"Average Turn Angle: {avg_angle:.1f}°"
        
        self.set_font('Arial', 'B', 11)
        self.multi_cell(0, 6, self.clean_text(summary))
        self.ln(5)
        
        # Process all turns sorted by severity
        sorted_turns = sorted(turns, key=lambda x: x.get('angle', 0), reverse=True)
        
        for i, turn in enumerate(sorted_turns, 1):
            # Add page for every turn to ensure readability
            if i > 1:
                self.add_page()
            
            angle = turn.get('angle', 0)
            
            # Turn classification and header
            if angle > 70:
                classification = "BLIND SPOT"
                color_code = (220, 20, 20)  # Red
            elif angle > 60:
                classification = "HIGH-ANGLE TURN"
                color_code = (255, 140, 0)  # Orange
            else:
                classification = "SHARP TURN"
                color_code = (0, 100, 0)  # Green
            
            self.set_font('Arial', 'B', 14)
            self.set_text_color(*color_code)
            header = f"TURN #{i} - {angle:.1f}° ({classification})"
            self.cell(0, 10, self.clean_text(header), 0, 1, 'C')
            self.set_text_color(0, 0, 0)
            self.ln(3)
            
            # Turn details
            self.set_font('Arial', 'B', 12)
            self.cell(0, 8, "TURN DETAILS:", ln=True)
            self.set_font('Arial', '', 11)
            
            # Speed and caution recommendations
            if angle > 90:
                speed_rec = "15-20 km/h"
                caution = "EXTREME CAUTION - CRAWL SPEED"
            elif angle > 80:
                speed_rec = "20-30 km/h"
                caution = "VERY HIGH CAUTION"
            elif angle > 70:
                speed_rec = "30-40 km/h"
                caution = "HIGH CAUTION"
            elif angle > 60:
                speed_rec = "40-50 km/h"
                caution = "INCREASED CAUTION"
            else:
                speed_rec = "50-60 km/h"
                caution = "NORMAL CAUTION"
            
            details = f"Location: {turn['lat']:.6f}, {turn['lng']:.6f}\n"
            details += f"Turn Angle: {angle:.1f}°\n"
            details += f"Recommended Speed: {speed_rec}\n"
            details += f"Caution Level: {caution}\n"
            
            self.multi_cell(0, 6, self.clean_text(details))
            self.ln(5)
            
            # Add map for this turn
            if api_key:
                self.set_font('Arial', 'B', 12)
                self.cell(0, 8, "LOCATION MAP:", ln=True)
                
                markers = [
                    {
                        'lat': turn['lat'],
                        'lng': turn['lng'],
                        'color': 'red' if angle > 70 else 'orange' if angle > 60 else 'yellow',
                        'label': str(i)
                    }
                ]
                
                if self.add_static_map_image(turn['lat'], turn['lng'], markers, api_key, zoom=17):
                    self.ln(3)
                else:
                    self.set_font('Arial', '', 10)
                    self.cell(0, 5, "Map not available for this location.", ln=True)
                
                self.ln(3)
                
                # Add street view
                self.set_font('Arial', 'B', 12)
                self.cell(0, 8, "STREET VIEW:", ln=True)
                
                if self.add_street_view_image(turn['lat'], turn['lng'], api_key):
                    self.ln(3)
                    self.set_font('Arial', 'I', 10)
                    self.cell(0, 5, f"Street view at: {turn['lat']:.6f}, {turn['lng']:.6f}", ln=True)
                else:
                    self.set_font('Arial', '', 10)
                    self.cell(0, 5, "Street view not available for this location.", ln=True)
            
            self.ln(8)

    def add_route_overview_map(self, route_polyline, turns, risk_segments, api_key=None):
        """Add comprehensive route overview map"""
        self.add_page()
        self.chapter_title("ROUTE MAP WITH ALL HAZARDS")
        
        # Map legend and description
        legend_text = "COMPREHENSIVE ROUTE HAZARD MAP\n\n"
        legend_text += "This map shows all identified hazards along your route:\n\n"
        legend_text += "MAP LEGEND:\n"
        legend_text += "• RED MARKERS: Blind spots (turns >70°) - EXTREME CAUTION\n"
        legend_text += "• ORANGE MARKERS: High-angle turns (60-70°) - HIGH CAUTION\n"
        legend_text += "• YELLOW MARKERS: Sharp turns (45-60°) - INCREASED CAUTION\n"
        legend_text += "• GREEN MARKER: Route start point\n"
        legend_text += "• RED MARKER: Route end point\n\n"
        
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 5, self.clean_text(legend_text))
        self.ln(5)
        
        # Add comprehensive route map
        if api_key and route_polyline and len(route_polyline) > 1:
            # Prepare all markers
            markers = []
            
            # Start and end markers
            markers.append({
                'lat': route_polyline[0][0],
                'lng': route_polyline[0][1],
                'color': 'green',
                'label': 'S'
            })
            
            markers.append({
                'lat': route_polyline[-1][0],
                'lng': route_polyline[-1][1],
                'color': 'red',
                'label': 'E'
            })
            
            # Add turn markers
            if turns:
                for i, turn in enumerate(turns[:20], 1):  # Limit to 20 markers
                    angle = turn.get('angle', 0)
                    if angle > 70:
                        color = 'red'
                    elif angle > 60:
                        color = 'orange'
                    else:
                        color = 'yellow'
                    
                    markers.append({
                        'lat': turn['lat'],
                        'lng': turn['lng'],
                        'color': color,
                        'label': str(i)
                    })
            
            # Calculate center point
            center_lat = sum(point[0] for point in route_polyline) / len(route_polyline)
            center_lng = sum(point[1] for point in route_polyline) / len(route_polyline)
            
            # Continuation of Complete Enhanced PDF Generator
            # This continues from where the previous code stopped

            self.set_font('Arial', 'B', 12)
            self.cell(0, 8, "COMPLETE ROUTE OVERVIEW MAP:", ln=True)
            
            if self.add_static_map_image(center_lat, center_lng, markers, api_key, zoom=12, size="640x480"):
                self.ln(3)
                self.set_font('Arial', 'I', 10)
                self.cell(0, 5, f"Route overview showing all {len(turns)} sharp turns and hazards", ln=True)
            else:
                self.set_font('Arial', '', 10)
                self.cell(0, 5, "Route overview map not available.", ln=True)
            
            self.ln(8)
            
            # Add individual hazard locations table
            self.set_font('Arial', 'B', 12)
            self.cell(0, 8, "HAZARD LOCATIONS SUMMARY:", ln=True)
            
            if turns:
                headers = ["#", "Type", "Angle", "Coordinates", "Risk Level"]
                data = []
                
                for i, turn in enumerate(turns[:15], 1):  # Show first 15
                    angle = turn.get('angle', 0)
                    if angle > 70:
                        turn_type = "BLIND SPOT"
                        risk_level = "EXTREME"
                    elif angle > 60:
                        turn_type = "HIGH-ANGLE"
                        risk_level = "HIGH"
                    else:
                        turn_type = "SHARP TURN"
                        risk_level = "MODERATE"
                    
                    data.append([
                        str(i),
                        turn_type,
                        f"{angle:.1f}°",
                        f"{turn['lat']:.4f}, {turn['lng']:.4f}",
                        risk_level
                    ])
                
                widths = [15, 35, 25, 55, 30]
                self.add_table(headers, data, widths)
                
                if len(turns) > 15:
                    self.ln(3)
                    self.set_font('Arial', 'I', 10)
                    self.cell(0, 5, f"... and {len(turns) - 15} more turns (see individual analysis pages)", ln=True)
        
        # Add Google Maps links for interactive viewing
        self.ln(8)
        self.set_font('Arial', 'B', 12)
        self.cell(0, 8, "INTERACTIVE MAP LINKS:", ln=True)
        self.set_font('Arial', '', 10)
        
        if route_polyline and len(route_polyline) > 1:
            start_point = route_polyline[0]
            end_point = route_polyline[-1]
            
            # Full route link
            full_route_url = f"https://www.google.com/maps/dir/{start_point[0]},{start_point[1]}/{end_point[0]},{end_point[1]}"
            self.cell(0, 6, "Complete Route on Google Maps:", ln=True)
            self.set_font('Arial', 'U', 9)
            self.cell(0, 5, full_route_url, ln=True)
            self.set_font('Arial', '', 10)
            self.ln(2)
            
            # Individual blind spot links
            blind_spots = [t for t in turns if t.get('angle', 0) > 70] if turns else []
            if blind_spots:
                self.cell(0, 6, "Individual Blind Spot Locations:", ln=True)
                for i, spot in enumerate(blind_spots[:10], 1):
                    spot_url = f"https://www.google.com/maps/@{spot['lat']},{spot['lng']},17z"
                    self.set_font('Arial', '', 9)
                    self.cell(0, 5, f"Blind Spot #{i} ({spot['angle']:.1f}°): {spot_url}", ln=True)
                
                if len(blind_spots) > 10:
                    self.cell(0, 5, f"... and {len(blind_spots) - 10} more blind spots", ln=True)

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

    def add_weather_chart(self, weather_data):
        """Add weather conditions chart"""
        if not weather_data or len(weather_data) < 2:
            return
        
        # Extract data for chart
        locations = []
        temperatures = []
        descriptions = []
        
        for w in weather_data:
            locations.append(w.get('location', 'Unknown')[:10])
            temperatures.append(w.get('temp', 0))
            descriptions.append(w.get('description', 'Unknown'))
        
        # Create temperature chart
        plt.figure(figsize=(10, 6))
        
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
            plt.text(bar.get_x() + bar.get_width()/2., -3,
                    desc[:8], ha='center', va='top', fontsize=8, rotation=45)
        
        plt.xlabel('Locations Along Route')
        plt.ylabel('Temperature (°C)')
        plt.title('Weather Conditions Along Route', fontsize=14, fontweight='bold')
        plt.xticks(range(len(locations)), locations, rotation=45)
        plt.grid(axis='y', alpha=0.3)
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
        
        # Add weather warnings
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
            self.set_text_color(220, 20, 20)
            self.cell(0, 6, "WEATHER WARNINGS:", ln=True)
            self.set_text_color(0, 0, 0)
            self.set_font('Arial', '', 10)
            
            for warning in adverse_conditions:
                self.cell(0, 6, f"* {self.clean_text(warning)}", ln=True)
            self.ln(3)


def generate_pdf(filename, from_addr, to_addr, distance, duration, turns, petrol_bunks,
                hospital_list, schools=None, food_stops=None, police_stations=None, 
                elevation=None, weather=None, risk_segments=None, compliance=None,
                emergency=None, environmental=None, toll_gates=None, bridges=None, 
                vehicle_type="car", type="full", api_key=None, major_highways=None):
    """
    Generate enhanced PDF report with corrected risk analysis and comprehensive maps
    
    Args:
        filename: Output PDF filename
        from_addr: Starting address
        to_addr: Destination address
        distance: Route distance
        duration: Route duration
        turns: List of sharp turns with angles
        petrol_bunks: Dictionary of fuel stations
        hospital_list: Dictionary of hospitals
        schools: Dictionary of schools
        food_stops: Dictionary of food stops
        police_stations: Dictionary of police stations
        elevation: List of elevation data points
        weather: List of weather data points
        risk_segments: List of risk analysis segments
        compliance: Compliance data
        emergency: Emergency data
        environmental: Environmental data
        toll_gates: List of toll gates
        bridges: List of bridges
        vehicle_type: Type of vehicle
        type: Report type ('full', 'summary', 'driver_briefing')
        api_key: Google Maps API key
        major_highways: List of major highways
    """
    
    # Ensure all expected data is present with defaults
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
    if not turns:
        turns = []
    
    # Create PDF with enhanced titles
    if type == "full":
        pdf = RoutePDF("Route Analytics - Complete Safety Analysis Report")
    elif type == "summary":
        pdf = RoutePDF("Route Summary - Key Safety Information")
    elif type == "driver_briefing":
        pdf = RoutePDF("Driver Briefing - Critical Safety Instructions")
    else:
        pdf = RoutePDF("Route Analytics Report")
    
    pdf.alias_nb_pages()
    pdf.add_page()

    # SECTION 1: Route Overview
    pdf.add_section("Route Overview", 
        f"From: {from_addr}\n"
        f"To: {to_addr}\n"
        f"Distance: {distance}\n"
        f"Estimated Duration: {duration}\n"
        f"Vehicle Type: {vehicle_type.replace('_', ' ').title()}\n"
        f"Report Type: {type.replace('_', ' ').title()}"
    )
    
    # Add major highways if available
    if major_highways:
        pdf.chapter_title("Major Highways on Route")
        highway_text = "This route uses the following major highways:\n\n"
        for i, highway in enumerate(major_highways, 1):
            highway_text += f"{i}. {highway}\n"
        highway_text += f"\nTotal Major Highways: {len(major_highways)}"
        pdf.chapter_body(highway_text)
    
    # SECTION 2: CORRECTED Risk Analysis Chart
    if risk_segments:
        pdf.add_corrected_risk_chart(risk_segments)
    else:
        # Add default risk chart if no segments provided
        pdf.add_corrected_risk_chart([])
    
    # SECTION 3: Weather Analysis (if available)
    if weather:
        pdf.add_weather_chart(weather)
    
    # SECTION 4: Enhanced Sections Based on Report Type
    if type == "full":
        # FULL REPORT - All detailed sections
        
        # Create route polyline for maps (extract from turns or create dummy)
        route_polyline = []
        if turns:
            # Create a simple polyline from turn locations
            route_polyline = [[turn['lat'], turn['lng']] for turn in turns]
        
        # Add comprehensive blind spots analysis
        if turns:
            pdf.add_enhanced_blind_spots_section(turns, route_polyline, api_key)
            
            # Add all sharp turns with street views
            pdf.add_all_sharp_turns_with_street_view(turns, api_key)
            
            # Add comprehensive route map
            pdf.add_route_overview_map(route_polyline, turns, risk_segments, api_key)
        
        # Add elevation profile
        if elevation:
            pdf.add_page()
            pdf.chapter_title("Elevation Profile")
            headers = ["Location", "Elevation (m)"]
            data = [(f"{e['location']['lat']:.4f}, {e['location']['lng']:.4f}", 
                    f"{e['elevation']:.2f}") for e in elevation[:15]]
            pdf.add_table(headers, data)
        
        # Add emergency services
        pdf.add_page()
        pdf.chapter_title("Emergency Services Along Route")
        
        if hospital_list:
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, f"Hospitals ({len(hospital_list)}):", ln=True)
            headers = ["Hospital Name", "Location"]
            data = [(pdf.clean_text(name), pdf.clean_text(vicinity)) 
                   for name, vicinity in list(hospital_list.items())[:10]]
            pdf.add_table(headers, data)
        
        if police_stations:
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, f"Police Stations ({len(police_stations)}):", ln=True)
            headers = ["Station Name", "Location"]
            data = [(pdf.clean_text(name), pdf.clean_text(vicinity)) 
                   for name, vicinity in list(police_stations.items())[:10]]
            pdf.add_table(headers, data)
        
        # Add amenities
        pdf.add_page()
        pdf.chapter_title("Amenities Along Route")
        
        if petrol_bunks:
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, f"Fuel Stations ({len(petrol_bunks)}):", ln=True)
            headers = ["Station Name", "Location"]
            data = [(pdf.clean_text(name), pdf.clean_text(vicinity)) 
                   for name, vicinity in list(petrol_bunks.items())[:10]]
            pdf.add_table(headers, data)
        
        if food_stops:
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, f"Food Stops ({len(food_stops)}):", ln=True)
            headers = ["Restaurant Name", "Location"]
            data = [(pdf.clean_text(name), pdf.clean_text(vicinity)) 
                   for name, vicinity in list(food_stops.items())[:10]]
            pdf.add_table(headers, data)
        
        # Schools with speed limit warnings
        if schools:
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 12)
            pdf.set_text_color(220, 20, 20)
            pdf.cell(0, 8, f"SCHOOLS - SPEED LIMIT ZONES ({len(schools)}):", ln=True)
            pdf.set_text_color(0, 0, 0)
            
            speed_limit = "30 km/h" if vehicle_type in ['heavy_truck', 'tanker'] else "35 km/h" if vehicle_type in ['medium_truck', 'bus'] else "40 km/h"
            
            warning_text = f"CRITICAL: Reduce speed to {speed_limit} when passing schools during school hours (8-9:30 AM, 2:30-4 PM)"
            pdf.set_font('Arial', '', 10)
            pdf.multi_cell(0, 5, pdf.clean_text(warning_text))
            pdf.ln(3)
            
            headers = ["School Name", "Location", "Speed Limit"]
            data = [(pdf.clean_text(name), pdf.clean_text(vicinity), speed_limit) 
                   for name, vicinity in list(schools.items())[:10]]
            pdf.add_table(headers, data)
    
    elif type == "summary":
        # SUMMARY REPORT - Key metrics and overview
        
        pdf.chapter_title("Key Safety Metrics")
        
        blind_spots = len([t for t in turns if t.get('angle', 0) > 70]) if turns else 0
        high_risk_segments = len([s for s in risk_segments if s.get('risk_level') == 'HIGH']) if risk_segments else 0
        
        headers = ["Safety Metric", "Count", "Risk Level"]
        data = [
            ("Total Sharp Turns", str(len(turns)) if turns else "0", "Moderate"),
            ("Blind Spots (>70°)", str(blind_spots), "High" if blind_spots > 0 else "Low"),
            ("High Risk Segments", str(high_risk_segments), "High" if high_risk_segments > 0 else "Low"),
            ("Schools Along Route", str(len(schools)) if schools else "0", "Moderate"),
            ("Toll Gates", str(len(toll_gates)) if toll_gates else "0", "Low"),
            ("Bridges", str(len(bridges)) if bridges else "0", "Low")
        ]
        
        pdf.add_table(headers, data)
        
        # Add top 5 most critical turns if available
        if turns:
            pdf.ln(5)
            pdf.chapter_title("Top 5 Most Critical Turns")
            
            sorted_turns = sorted(turns, key=lambda x: x.get('angle', 0), reverse=True)[:5]
            headers = ["Rank", "Coordinates", "Angle", "Risk Level"]
            data = []
            
            for i, turn in enumerate(sorted_turns, 1):
                angle = turn.get('angle', 0)
                risk = "EXTREME" if angle > 80 else "HIGH" if angle > 70 else "MODERATE"
                data.append([
                    str(i),
                    f"{turn['lat']:.4f}, {turn['lng']:.4f}",
                    f"{angle:.1f}°",
                    risk
                ])
            
            pdf.add_table(headers, data)
    
    elif type == "driver_briefing":
        # DRIVER BRIEFING - Critical instructions and safety information
        
        pdf.chapter_title("Critical Route Features")
        
        # Key warnings
        warnings = []
        if turns:
            blind_spots = len([t for t in turns if t.get('angle', 0) > 70])
            if blind_spots > 0:
                warnings.append(f"ALERT: {blind_spots} blind spots requiring extreme caution")
            
            if len(turns) > 10:
                warnings.append(f"CAUTION: {len(turns)} sharp turns on this route")
        
        if schools:
            warnings.append(f"SCHOOL ZONES: {len(schools)} schools - reduce speed during school hours")
        
        if len(warnings) == 0:
            warnings.append("No critical warnings for this route")
        
        for warning in warnings:
            pdf.add_hazard_icon("warning")
            pdf.cell(0, 8, pdf.clean_text(warning), ln=True)
        
        pdf.ln(5)
        
        # Vehicle-specific driving instructions
        pdf.chapter_title("Vehicle-Specific Driving Instructions")
        
        if vehicle_type in ['heavy_truck', 'tanker']:
            instructions = [
                "Maximum speed: 60 km/h on highways, 45 km/h in urban areas",
                "Mandatory rest stops every 4 hours of driving",
                "Maintain minimum 4-second following distance",
                "Use engine braking on downhill sections",
                "Avoid sharp braking when fully loaded"
            ]
        elif vehicle_type in ['medium_truck', 'bus']:
            instructions = [
                "Maximum speed: 70 km/h on highways, 50 km/h in urban areas",
                "Take rest breaks every 4 hours",
                "Maintain minimum 3-second following distance",
                "Check mirrors frequently for blind spots",
                "Be aware of pedestrians at all stops"
            ]
        else:
            instructions = [
                "Follow posted speed limits",
                "Take breaks every 2-3 hours to avoid fatigue",
                "Maintain safe following distance",
                "Adjust speed for road and weather conditions",
                "Stay alert at all times"
            ]
        
        for instruction in instructions:
            pdf.add_hazard_icon("info")
            pdf.cell(0, 8, pdf.clean_text(instruction), ln=True)
        
        # Add most critical blind spots for driver briefing
        if turns:
            blind_spots = [t for t in turns if t.get('angle', 0) > 70]
            if blind_spots:
                pdf.add_page()
                pdf.chapter_title("CRITICAL BLIND SPOTS - DRIVER ALERT")
                
                critical_spots = sorted(blind_spots, key=lambda x: x.get('angle', 0), reverse=True)[:5]
                
                headers = ["#", "Coordinates", "Angle", "Required Action"]
                data = []
                
                for i, spot in enumerate(critical_spots, 1):
                    action = "REDUCE TO 20 KM/H" if spot['angle'] > 80 else "REDUCE TO 30 KM/H"
                    data.append([
                        str(i),
                        f"{spot['lat']:.4f}, {spot['lng']:.4f}",
                        f"{spot['angle']:.1f}°",
                        action
                    ])
                
                pdf.add_table(headers, data)
    
    # FINAL SECTION: Safety Recommendations (for all report types)
    pdf.add_page()
    pdf.chapter_title("Final Safety Recommendations")
    
    final_recommendations = [
        "Always maintain appropriate speed for road and weather conditions",
        "Take regular breaks to prevent driver fatigue",
        "Keep emergency contact numbers readily accessible",
        "Ensure vehicle is in good mechanical condition before departure",
        "Plan fuel stops and rest areas in advance",
        "Monitor weather conditions throughout the journey",
        "Follow all traffic laws and posted speed limits",
        "Stay alert and avoid distractions while driving"
    ]
    
    for i, rec in enumerate(final_recommendations, 1):
        pdf.add_hazard_icon("success")
        pdf.cell(0, 8, f"{i}. {pdf.clean_text(rec)}", ln=True)
    
    # Footer disclaimer
    pdf.ln(10)
    pdf.set_font('Arial', 'I', 10)
    disclaimer = "This report was generated by the Route Analytics system. Always use professional judgment, follow official road rules, and adapt to current conditions. This report is for informational purposes only."
    pdf.multi_cell(0, 5, pdf.clean_text(disclaimer))
    
    # Save the PDF
    try:
        pdf.output(filename)
        print(f"Enhanced PDF report generated successfully: {filename}")
        return filename
    except Exception as e:
        print(f"Error generating enhanced PDF: {e}")
        return None

# Example usage function
def generate_enhanced_route_report(route_data, report_type="full", api_key=None):
    """
    Generate enhanced route report with all improvements
    
    Args:
        route_data (dict): Complete route analysis data
        report_type (str): Type of report ('full', 'summary', 'driver_briefing')
        api_key (str): Google Maps API key for street views and maps
    """
    
    # Extract data from route_data dictionary
    from_addr = route_data.get('from', 'Unknown Start')
    to_addr = route_data.get('to', 'Unknown Destination')
    distance = route_data.get('distance', 'Unknown')
    duration = route_data.get('duration', 'Unknown')
    vehicle_type = route_data.get('vehicle_type', 'car')
    
    # Extract turn data
    turns = route_data.get('sharp_turns', [])
    
    # Extract POI data
    petrol_bunks = route_data.get('petrol_bunks', {})
    hospitals = route_data.get('hospitals', {})
    schools = route_data.get('schools', {})
    food_stops = route_data.get('food_stops', {})
    police_stations = route_data.get('police_stations', {})
    
    # Extract analysis data
    elevation = route_data.get('elevation', [])
    weather = route_data.get('weather', [])
    risk_segments = route_data.get('risk_segments', [])
    compliance = route_data.get('compliance', {})
    emergency = route_data.get('emergency', {})
    environmental = route_data.get('environmental', {})
    toll_gates = route_data.get('toll_gates', [])
    bridges = route_data.get('bridges', [])
    major_highways = route_data.get('major_highways', [])
    
    # Generate filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"route_report_{report_type}_{timestamp}.pdf"
    
    # Generate the enhanced PDF
    return generate_pdf(
        filename=filename,
        from_addr=from_addr,
        to_addr=to_addr,
        distance=distance,
        duration=duration,
        turns=turns,
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
        vehicle_type=vehicle_type,
        type=report_type,
        api_key=api_key,
        major_highways=major_highways
    )