import math
import random
import logging
from geopy.distance import geodesic

# Set up logger
logger = logging.getLogger(__name__)

def categorize_emergency_services(hospitals, police_stations, petrol_bunks):
    """
    Categorize emergency services for quick access
    """
    emergency_services = {
        "hospitals": [],
        "police_stations": [],
        "fuel_stations": []
    }
    
    # Format hospitals
    if hospitals:
        for name, vicinity in hospitals.items():
            emergency_services["hospitals"].append({
                "name": name,
                "vicinity": vicinity,
                "type": "hospital",
                "icon": "hospital",
                "color": "primary"
            })
    
    # Format police stations
    if police_stations:
        for name, vicinity in police_stations.items():
            emergency_services["police_stations"].append({
                "name": name,
                "vicinity": vicinity,
                "type": "police",
                "icon": "shield",
                "color": "danger"
            })
    
    # Format fuel stations (petrol bunks)
    if petrol_bunks:
        for name, vicinity in petrol_bunks.items():
            emergency_services["fuel_stations"].append({
                "name": name,
                "vicinity": vicinity,
                "type": "fuel",
                "icon": "droplet",
                "color": "warning"
            })
    
    return emergency_services

def find_critical_emergency_points(route_points, emergency_services, max_distance_km=5):
    """
    Identify points along the route that are farther than max_distance_km from emergency services
    """
    critical_points = []
    
    # Create a list of all emergency service locations
    all_services = []
    for service_type, services in emergency_services.items():
        for service in services:
            if "vicinity" in service and service["vicinity"]:
                all_services.append({
                    "name": service["name"],
                    "type": service_type,
                    "vicinity": service["vicinity"]
                })
    
    # If no emergency services data, we can't identify critical points
    if not all_services:
        return critical_points
    
    # Check each point on the route
    check_interval = max(1, len(route_points) // 20)  # Check every ~5% of the route
    
    for i in range(0, len(route_points), check_interval):
        if i >= len(route_points):
            break
            
        point = route_points[i]
        point_coord = (point[0], point[1])
        
        # Find the closest emergency service
        closest_service = None
        closest_distance = float('inf')
        
        for service in all_services:
            # This is a simplified approach - in a real implementation, 
            # you would geocode the vicinity address to get coordinates
            try:
                # In a real implementation, you would have the actual coordinates
                # Here we're approximating based on route position with a random offset
                # Create a reasonable but random location relatively close to the route point
                service_lat = point[0] + (random.random() * 0.1 - 0.05)
                service_lng = point[1] + (random.random() * 0.1 - 0.05)
                service_coord = (service_lat, service_lng)
                
                distance = geodesic(point_coord, service_coord).kilometers
                
                if distance < closest_distance:
                    closest_distance = distance
                    closest_service = service
            except Exception as e:
                logger.error(f"Error calculating distance to emergency service: {e}")
                continue
        
        # If the closest service is farther than the maximum allowed distance
        if closest_distance > max_distance_km:
            critical_points.append({
                "index": i,
                "coordinates": {"lat": point[0], "lng": point[1]},
                "closest_service": closest_service["name"] if closest_service else "None",
                "closest_service_type": closest_service["type"] if closest_service else "None",
                "distance_km": closest_distance
            })
    
    return critical_points

def generate_emergency_contact_list(route_data, emergency_services):
    """
    Generate a list of emergency contacts along the route
    """
    emergency_contacts = []
    
    # Standard emergency numbers in India
    emergency_contacts.append({
        "name": "All Emergencies",
        "number": "112",
        "type": "general",
        "priority": 1
    })
    
    emergency_contacts.append({
        "name": "Police",
        "number": "100",
        "type": "police",
        "priority": 2
    })
    
    emergency_contacts.append({
        "name": "Ambulance",
        "number": "108",
        "type": "medical",
        "priority": 2
    })
    
    emergency_contacts.append({
        "name": "Fire",
        "number": "101",
        "type": "fire",
        "priority": 2
    })
    
    emergency_contacts.append({
        "name": "Highway Patrol (India)",
        "number": "1033",
        "type": "highway",
        "priority": 3
    })
    
    # Company emergency contact (would be loaded from config in real implementation)
    emergency_contacts.append({
        "name": "Company Emergency Control",
        "number": "1800-XXX-XXXX",
        "type": "company",
        "priority": 3
    })
    
    # Add contacts for hospitals along the route
    for hospital in emergency_services.get("hospitals", [])[:3]:  # Limit to first 3
        emergency_contacts.append({
            "name": hospital["name"],
            "vicinity": hospital.get("vicinity", ""),
            "type": "hospital",
            "priority": 4
        })
    
    # Add contacts for police stations along the route
    for police in emergency_services.get("police_stations", [])[:3]:  # Limit to first 3
        emergency_contacts.append({
            "name": police["name"],
            "vicinity": police.get("vicinity", ""),
            "type": "police",
            "priority": 4
        })
    
    return emergency_contacts

def create_emergency_response_plan(route_data, emergency_services, risk_segments):
    """
    Create an emergency response plan based on route risks and emergency services
    """
    emergency_plan = {
        "general_instructions": [
            "In case of ANY emergency, first call the national emergency number 112",
            "For vehicle breakdown on highways, call Highway Patrol at 1033",
            "For company-specific emergencies, contact Company Emergency Control"
        ],
        "high_risk_segments": [],
        "emergency_contacts": []
    }
    
    # Add emergency contacts
    emergency_plan["emergency_contacts"] = generate_emergency_contact_list(
        route_data, emergency_services
    )
    
    # Identify high-risk segments for special instructions
    if risk_segments:
        for segment in risk_segments:
            if segment.get("risk_level") == "HIGH":
                high_risk_data = {
                    "start_point": segment["start_point"],
                    "end_point": segment["end_point"],
                    "risk_factors": segment.get("risk_factors", []),
                    "emergency_instructions": []
                }
                
                # Add specific instructions based on risk factors
                for factor in segment.get("risk_factors", []):
                    if factor["type"] == "sharp_turns":
                        high_risk_data["emergency_instructions"].append(
                            "Approach turns at reduced speed, use hazard lights if stopping"
                        )
                    
                    elif factor["type"] == "elevation":
                        high_risk_data["emergency_instructions"].append(
                            "Use engine braking on steep descents, check brakes regularly"
                        )
                    
                    elif factor["type"] == "weather":
                        high_risk_data["emergency_instructions"].append(
                            f"In {factor.get('condition', 'adverse weather')}, pull over to safe location if visibility is poor"
                        )
                    
                    elif factor["type"] == "road_quality":
                        high_risk_data["emergency_instructions"].append(
                            "Drive slowly on poor road sections, be alert for sudden potholes"
                        )
                
                # Only add segments with instructions
                if high_risk_data["emergency_instructions"]:
                    emergency_plan["high_risk_segments"].append(high_risk_data)
    
    return emergency_plan

def find_nearby_emergency_services(route_point, emergency_services, radius_km=10):
    """
    Find emergency services near a specific route point
    """
    nearby_services = {
        "hospitals": [],
        "police_stations": [],
        "fuel_stations": []
    }
    
    point_coord = (route_point[0], route_point[1])
    
    # Loop through all service types
    for service_type, services in emergency_services.items():
        for service in services:
            # In a real implementation, the service would have actual coordinates
            # For this example, we'll generate random nearby coordinates
            try:
                service_lat = route_point[0] + (random.random() * 0.1 - 0.05)
                service_lng = route_point[1] + (random.random() * 0.1 - 0.05)
                service_coord = (service_lat, service_lng)
                
                distance = geodesic(point_coord, service_coord).kilometers
                
                if distance <= radius_km:
                    service_copy = service.copy()
                    service_copy["distance_km"] = round(distance, 2)
                    service_copy["coordinates"] = {"lat": service_lat, "lng": service_lng}
                    
                    nearby_services[service_type].append(service_copy)
            except Exception as e:
                logger.error(f"Error finding nearby emergency services: {e}")
    
    return nearby_services

def generate_emergency_map_data(route_points, emergency_services, critical_points):
    """
    Generate data for rendering emergency services on a map
    """
    map_data = {
        "hospitals": [],
        "police_stations": [],
        "fuel_stations": [],
        "critical_points": []
    }
    
    # Add emergency services with approximate coordinates
    for service_type, services in emergency_services.items():
        for i, service in enumerate(services):
            # In a real implementation, services would have proper coordinates
            # For this example, we'll place them along the route with offsets
            try:
                if route_points and len(route_points) > 0:
                    point_index = min(i * 3, len(route_points) - 1)
                    service_lat = route_points[point_index][0] + (random.random() * 0.05 - 0.025)
                    service_lng = route_points[point_index][1] + (random.random() * 0.05 - 0.025)
                    
                    service_data = {
                        "name": service["name"],
                        "type": service["type"],
                        "lat": service_lat,
                        "lng": service_lng,
                        "icon": service.get("icon", "circle"),
                        "color": service.get("color", "blue")
                    }
                    
                    if service_type == "hospitals":
                        map_data["hospitals"].append(service_data)
                    elif service_type == "police_stations":
                        map_data["police_stations"].append(service_data)
                    elif service_type == "fuel_stations":
                        map_data["fuel_stations"].append(service_data)
            except Exception as e:
                logger.error(f"Error generating emergency map data: {e}")
    
    # Add critical points
    for point in critical_points:
        map_data["critical_points"].append({
            "lat": point["coordinates"]["lat"],
            "lng": point["coordinates"]["lng"],
            "type": "critical",
            "distance": point["distance_km"],
            "nearest_service": point["closest_service"]
        })
    
    return map_data

def generate_emergency_action_cards(emergency_services, vehicle_type, risk_level):
    """
    Generate emergency action cards based on vehicle type and risk level
    """
    action_cards = []
    
    # Vehicle breakdown action card
    breakdown_card = {
        "title": "Vehicle Breakdown",
        "icon": "ti-car-crash",
        "color": "warning",
        "steps": [
            "Move vehicle to a safe location off the road if possible",
            "Turn on hazard lights",
            "Place warning triangles/reflectors 50m behind vehicle",
            "Call for roadside assistance or tow service",
            "Inform company dispatch about the breakdown"
        ]
    }
    
    # Add vehicle-specific steps
    if vehicle_type == "tanker":
        breakdown_card["steps"].append("Check for any leaks or damage to containment")
        breakdown_card["steps"].append("If hazardous material is leaking, call emergency services immediately")
    elif vehicle_type in ["heavy_truck", "medium_truck"]:
        breakdown_card["steps"].append("Secure the cargo before attempting any repairs")
    
    action_cards.append(breakdown_card)
    
    # Medical emergency action card
    medical_card = {
        "title": "Medical Emergency",
        "icon": "ti-activity",
        "color": "danger",
        "steps": [
            "Call emergency medical services (108 or 112)",
            "Provide first aid if trained and equipment is available",
            "Do not move injured persons unless absolutely necessary",
            "Share exact location coordinates with emergency services"
        ]
    }
    
    # Add nearest hospital information if available
    if emergency_services.get("hospitals"):
        nearest_hospital = emergency_services["hospitals"][0]["name"]
        medical_card["steps"].append(f"Nearest hospital: {nearest_hospital}")
    
    action_cards.append(medical_card)
    
    # Security incident action card
    security_card = {
        "title": "Security Incident",
        "icon": "ti-shield-alert",
        "color": "primary",
        "steps": [
            "Call police (100 or 112)",
            "Do not confront potentially dangerous individuals",
            "Lock vehicle doors and windows",
            "If safe to do so, drive to nearest police station or public area",
            "Document incident details as soon as possible"
        ]
    }
    
    # Add nearest police station information if available
    if emergency_services.get("police_stations"):
        nearest_police = emergency_services["police_stations"][0]["name"]
        security_card["steps"].append(f"Nearest police station: {nearest_police}")
    
    action_cards.append(security_card)
    
    # High risk specific card
    if risk_level == "HIGH":
        high_risk_card = {
            "title": "High Risk Area Response",
            "icon": "ti-alert-triangle",
            "color": "danger",
            "steps": [
                "Reduce speed immediately",
                "Increase following distance",
                "Avoid sudden maneuvers",
                "Be prepared for adverse conditions",
                "Monitor surroundings continuously",
                "Consider alternative routes if conditions worsen"
            ]
        }
        action_cards.append(high_risk_card)
    
    return action_cards