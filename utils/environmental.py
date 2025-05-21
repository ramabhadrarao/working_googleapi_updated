import os
import json
import logging
from geopy.distance import geodesic
import random  # For demo data generation

# Set up logger
logger = logging.getLogger(__name__)

class EnvironmentalAnalyzer:
    """Analyze route for environmental considerations and protected areas"""
    
    def __init__(self, config_dir="environmental_data"):
        self.config_dir = config_dir
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            
        # Load environmental data
        self.protected_areas = self._load_json_data('protected_areas.json')
        self.emission_zones = self._load_json_data('emission_zones.json')
        self.noise_restriction_zones = self._load_json_data('noise_restriction_zones.json')
        self.wildlife_corridors = self._load_json_data('wildlife_corridors.json')
    
    def _load_json_data(self, filename):
        """Load JSON data from file, create with default if doesn't exist"""
        filepath = os.path.join(self.config_dir, filename)
        
        if not os.path.exists(filepath):
            # Create default data based on filename
            default_data = self._get_default_data(filename)
            with open(filepath, 'w') as f:
                json.dump(default_data, f, indent=2)
            return default_data
            
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            # If file is corrupted, create with defaults
            default_data = self._get_default_data(filename)
            with open(filepath, 'w') as f:
                json.dump(default_data, f, indent=2)
            return default_data
    
    def _get_default_data(self, filename):
        """Get default data structure based on filename"""
        if filename == 'protected_areas.json':
            return {
                "protected_areas": [
                    {
                        "name": "National Park Example",
                        "type": "national_park",
                        "coordinates": {"lat": 17.3850, "lng": 78.4867},
                        "radius_km": 10,
                        "restrictions": {
                            "speed_limit": 40,
                            "no_honking": True,
                            "hazmat_prohibited": True,
                            "night_driving_prohibited": False
                        }
                    },
                    {
                        "name": "Wildlife Sanctuary Example",
                        "type": "wildlife_sanctuary",
                        "coordinates": {"lat": 17.4567, "lng": 78.3456},
                        "radius_km": 5,
                        "restrictions": {
                            "speed_limit": 30,
                            "no_honking": True,
                            "hazmat_prohibited": True,
                            "night_driving_prohibited": True
                        }
                    },
                    {
                        "name": "Forest Reserve Example",
                        "type": "forest_reserve",
                        "coordinates": {"lat": 17.2890, "lng": 78.5678},
                        "radius_km": 8,
                        "restrictions": {
                            "speed_limit": 40,
                            "no_honking": True,
                            "hazmat_prohibited": True,
                            "night_driving_prohibited": False
                        }
                    }
                ]
            }
        elif filename == 'emission_zones.json':
            return {
                "emission_control_areas": [
                    {
                        "name": "City Center Low Emission Zone",
                        "type": "low_emission_zone",
                        "coordinates": {"lat": 17.4000, "lng": 78.4800},
                        "radius_km": 5,
                        "restrictions": {
                            "min_emission_standard": "BS-VI",
                            "restricted_hours": ["07:00-20:00"],
                            "restricted_vehicles": ["heavy_truck", "medium_truck", "old_vehicles"],
                            "congestion_charge": True
                        }
                    }
                ]
            }
        elif filename == 'noise_restriction_zones.json':
            return {
                "noise_restriction_zones": [
                    {
                        "name": "Hospital Zone",
                        "type": "hospital_zone",
                        "coordinates": {"lat": 17.4223, "lng": 78.4777},
                        "radius_km": 0.5,
                        "restrictions": {
                            "no_honking": True,
                            "noise_limit_db": 55,
                            "restricted_hours": ["all"]
                        }
                    },
                    {
                        "name": "Residential Zone",
                        "type": "residential_zone",
                        "coordinates": {"lat": 17.4123, "lng": 78.4126},
                        "radius_km": 2,
                        "restrictions": {
                            "no_honking": True,
                            "noise_limit_db": 65,
                            "restricted_hours": ["22:00-06:00"]
                        }
                    }
                ]
            }
        elif filename == 'wildlife_corridors.json':
            return {
                "wildlife_corridors": [
                    {
                        "name": "Wildlife Crossing Corridor",
                        "type": "wildlife_crossing",
                        "coordinates": {"lat": 17.3333, "lng": 78.5555},
                        "radius_km": 1,
                        "restrictions": {
                            "speed_limit": 30,
                            "no_stopping": True,
                            "watch_for_wildlife": True,
                            "night_driving_caution": True
                        },
                        "wildlife_types": ["deer", "small_mammals"]
                    }
                ]
            }
        else:
            return {}
    
    def check_sensitive_zones(self, route_points):
        """Check if route passes through environmentally sensitive zones"""
        sensitive_areas = []
        
        # Check each point in the route against all sensitive zones
        sample_interval = max(1, len(route_points) // 20)  # Check approximately every 5% of route
        
        for i in range(0, len(route_points), sample_interval):
            if i >= len(route_points):
                break
                
            point_coord = (route_points[i][0], route_points[i][1])
            
            # Check protected areas
            for area in self.protected_areas.get("protected_areas", []):
                area_center = (area["coordinates"]["lat"], area["coordinates"]["lng"])
                distance = geodesic(point_coord, area_center).kilometers
                
                if distance <= area["radius_km"]:
                    sensitive_areas.append({
                        "type": area["type"],
                        "name": area["name"],
                        "point_index": i,
                        "coordinates": {"lat": point_coord[0], "lng": point_coord[1]},
                        "restrictions": area["restrictions"]
                    })
            
            # Check emission control areas
            for zone in self.emission_zones.get("emission_control_areas", []):
                zone_center = (zone["coordinates"]["lat"], zone["coordinates"]["lng"])
                distance = geodesic(point_coord, zone_center).kilometers
                
                if distance <= zone["radius_km"]:
                    sensitive_areas.append({
                        "type": zone["type"],
                        "name": zone["name"],
                        "point_index": i,
                        "coordinates": {"lat": point_coord[0], "lng": point_coord[1]},
                        "restrictions": zone["restrictions"]
                    })
            
            # Check noise restriction zones
            for zone in self.noise_restriction_zones.get("noise_restriction_zones", []):
                zone_center = (zone["coordinates"]["lat"], zone["coordinates"]["lng"])
                distance = geodesic(point_coord, zone_center).kilometers
                
                if distance <= zone["radius_km"]:
                    sensitive_areas.append({
                        "type": zone["type"],
                        "name": zone["name"],
                        "point_index": i,
                        "coordinates": {"lat": point_coord[0], "lng": point_coord[1]},
                        "restrictions": zone["restrictions"]
                    })
            
            # Check wildlife corridors
            for corridor in self.wildlife_corridors.get("wildlife_corridors", []):
                corridor_center = (corridor["coordinates"]["lat"], corridor["coordinates"]["lng"])
                distance = geodesic(point_coord, corridor_center).kilometers
                
                if distance <= corridor["radius_km"]:
                    sensitive_areas.append({
                        "type": corridor["type"],
                        "name": corridor["name"],
                        "point_index": i,
                        "coordinates": {"lat": point_coord[0], "lng": point_coord[1]},
                        "restrictions": corridor["restrictions"],
                        "wildlife_types": corridor.get("wildlife_types", [])
                    })
        
        # Remove duplicates (same zone detected multiple times)
        unique_zones = {}
        for area in sensitive_areas:
            zone_key = f"{area['type']}_{area['name']}"
            if zone_key not in unique_zones:
                unique_zones[zone_key] = area
        
        return list(unique_zones.values())
    
    def get_environmental_restrictions(self, sensitive_areas):
        """Generate a list of environmental restrictions based on sensitive areas"""
        if not sensitive_areas:
            return []
            
        restrictions = []
        
        # Check for speed limits
        speed_restricted_areas = [area for area in sensitive_areas 
                                if 'restrictions' in area and 'speed_limit' in area['restrictions']]
        if speed_restricted_areas:
            area_names = [area['name'] for area in speed_restricted_areas]
            restrictions.append({
                "description": "Reduced speed limits in environmentally sensitive areas",
                "applicable_areas": area_names
            })
        
        # Check for no honking zones
        no_honking_areas = [area for area in sensitive_areas 
                          if 'restrictions' in area and 'no_honking' in area['restrictions']
                          and area['restrictions']['no_honking']]
        if no_honking_areas:
            area_names = [area['name'] for area in no_honking_areas]
            restrictions.append({
                "description": "No honking in noise-sensitive areas",
                "applicable_areas": area_names
            })
        
        # Check for hazmat prohibitions
        hazmat_prohibited_areas = [area for area in sensitive_areas 
                                 if 'restrictions' in area and 'hazmat_prohibited' in area['restrictions']
                                 and area['restrictions']['hazmat_prohibited']]
        if hazmat_prohibited_areas:
            area_names = [area['name'] for area in hazmat_prohibited_areas]
            restrictions.append({
                "description": "Hazardous materials prohibited",
                "applicable_areas": area_names
            })
        
        # Check for night driving restrictions
        night_restricted_areas = [area for area in sensitive_areas 
                               if 'restrictions' in area and 'night_driving_prohibited' in area['restrictions']
                               and area['restrictions']['night_driving_prohibited']]
        if night_restricted_areas:
            area_names = [area['name'] for area in night_restricted_areas]
            restrictions.append({
                "description": "Night driving prohibited",
                "applicable_areas": area_names
            })
        
        # Check for wildlife corridors
        wildlife_areas = [area for area in sensitive_areas if area['type'] == 'wildlife_crossing']
        if wildlife_areas:
            area_names = [area['name'] for area in wildlife_areas]
            restrictions.append({
                "description": "Wildlife crossing zone - proceed with caution",
                "applicable_areas": area_names
            })
        
        # Check for emission restrictions
        emission_areas = [area for area in sensitive_areas if area['type'] == 'low_emission_zone']
        if emission_areas:
            area_names = [area['name'] for area in emission_areas]
            restrictions.append({
                "description": "Low emission zone - vehicle must meet emission standards",
                "applicable_areas": area_names
            })
        
        return restrictions
    
    def generate_environmental_advisories(self, sensitive_areas, vehicle_type="car"):
        """Generate environmental advisories based on route and vehicle type"""
        if not sensitive_areas:
            return []
            
        advisories = []
        
        # Vehicle-specific advisories
        if vehicle_type in ['heavy_truck', 'tanker']:
            # Heavy vehicles have more stringent requirements
            
            # Emission advisory
            emission_areas = [area for area in sensitive_areas if area['type'] == 'low_emission_zone']
            if emission_areas:
                advisories.append({
                    "heading": "Emissions Requirements",
                    "description": "Your vehicle must meet BS-VI emission standards to enter low emission zones on this route.",
                    "level": "warning",
                    "icon": "alert-circle"
                })
            
            # Weight restriction advisory
            protected_areas = [area for area in sensitive_areas 
                             if area['type'] in ['national_park', 'wildlife_sanctuary', 'forest_reserve']]
            if protected_areas:
                advisories.append({
                    "heading": "Weight & Size Restrictions",
                    "description": "Heavy vehicles may face additional restrictions in protected areas. Consider an alternative route if possible.",
                    "level": "warning",
                    "icon": "truck"
                })
        
        # General advisories
        
        # Wildlife advisory
        wildlife_areas = [area for area in sensitive_areas if area['type'] == 'wildlife_crossing']
        if wildlife_areas:
            wildlife_types = []
            for area in wildlife_areas:
                if 'wildlife_types' in area:
                    wildlife_types.extend(area['wildlife_types'])
            
            wildlife_types = list(set(wildlife_types))  # Remove duplicates
            
            wildlife_description = "Watch for wildlife crossing the road"
            if wildlife_types:
                wildlife_description += f", especially {', '.join(wildlife_types)}"
            wildlife_description += ". Reduce speed and stay alert, particularly at dawn and dusk."
            
            advisories.append({
                "heading": "Wildlife Crossing Zone",
                "description": wildlife_description,
                "level": "info",
                "icon": "paw"
            })
        
        # Noise advisory
        noise_areas = [area for area in sensitive_areas 
                      if 'restrictions' in area and 'no_honking' in area['restrictions']
                      and area['restrictions']['no_honking']]
        if noise_areas:
            advisories.append({
                "heading": "Noise Sensitive Zone",
                "description": "No honking allowed in noise-sensitive areas. Keep engine noise to a minimum.",
                "level": "info",
                "icon": "volume-x"
            })
        
        # Protected area advisory
        protected_areas = [area for area in sensitive_areas 
                         if area['type'] in ['national_park', 'wildlife_sanctuary', 'forest_reserve']]
        if protected_areas:
            advisories.append({
                "heading": "Protected Environmental Area",
                "description": "This route passes through environmentally protected areas. Adhere to all posted regulations and avoid stopping except in designated areas.",
                "level": "info",
                "icon": "tree"
            })
        
        # Emission zone advisory
        emission_areas = [area for area in sensitive_areas if area['type'] == 'low_emission_zone']
        if emission_areas:
            emission_times = []
            for area in emission_areas:
                if 'restrictions' in area and 'restricted_hours' in area['restrictions']:
                    emission_times.extend(area['restrictions']['restricted_hours'])
            
            emission_description = "Low emission zone requirements in effect"
            if emission_times and emission_times != ["all"]:
                emission_description += f" during: {', '.join(emission_times)}"
            
            advisories.append({
                "heading": "Low Emission Zone",
                "description": emission_description,
                "level": "info",
                "icon": "leaf"
            })
        
        return advisories
    
    def calculate_carbon_footprint(self, distance_km, vehicle_type="car"):
        """Calculate approximate carbon footprint for the route"""
        # CO2 emission factors in kg per km (approximate values)
        emission_factors = {
            "car": 0.12,  # Average passenger car
            "medium_truck": 0.25,  # Medium goods vehicle
            "heavy_truck": 0.9,  # Heavy goods vehicle
            "tanker": 1.0,  # Tanker/heavy vehicle
            "bus": 0.8  # Passenger bus
        }
        
        factor = emission_factors.get(vehicle_type, 0.12)  # Default to car if type not found
        co2_emissions = distance_km * factor
        
        return {
            "co2_kg": round(co2_emissions, 2),
            "vehicle_type": vehicle_type,
            "distance_km": distance_km,
            "emission_factor": factor
        }
    
    def generate_eco_driving_tips(self, route_data, vehicle_type="car"):
        """Generate eco-driving tips based on route characteristics"""
        tips = [
            {
                "heading": "Maintain Steady Speed",
                "description": "Avoid rapid acceleration and braking to save fuel and reduce emissions.",
                "icon": "gauge"
            },
            {
                "heading": "Optimal Speed Range",
                "description": "Maintain speed between 50-80 km/h where possible for optimal fuel efficiency.",
                "icon": "speedboat"
            },
            {
                "heading": "Engine Idling",
                "description": "Minimize idling. If stopping for more than 30 seconds, consider turning off the engine.",
                "icon": "engine"
            }
        ]
        
        # Add vehicle-specific tips
        if vehicle_type in ["medium_truck", "heavy_truck", "tanker"]:
            tips.append({
                "heading": "Use Engine Braking",
                "description": "On downhill sections, use engine braking rather than the foot brake to save fuel.",
                "icon": "trending-down"
            })
            
            tips.append({
                "heading": "Tire Pressure",
                "description": "Ensure correct tire pressure. Under-inflated tires increase rolling resistance and fuel consumption.",
                "icon": "circle"
            })
        
        # Check for elevation changes
        if 'elevation' in route_data and len(route_data['elevation']) > 1:
            elevation_values = [point.get('elevation', 0) for point in route_data['elevation']]
            elevation_change = max(elevation_values) - min(elevation_values)
            
            if elevation_change > 100:  # Significant elevation changes
                tips.append({
                    "heading": "Elevation Strategy",
                    "description": "This route has significant elevation changes. Use momentum on uphill sections and avoid excessive acceleration.",
                    "icon": "mountain"
                })
        
        # Randomly select 3-4 tips to avoid overwhelming the user
        if len(tips) > 4:
            return random.sample(tips, 4)
        return tips
    
    def rank_route_environmental_impact(self, distance_km, sensitive_areas, vehicle_type="car"):
        """Rank the environmental impact of a route on a scale of 1-5 (1 best, 5 worst)"""
        # Base score starts at 3 (medium impact)
        score = 3.0
        
        # Adjust based on distance (longer routes have more impact)
        if distance_km < 5:
            score -= 1.0  # Short route, less impact
        elif distance_km > 50:
            score += 0.5  # Long route, more impact
        
        # Adjust based on vehicle type
        vehicle_impact = {
            "car": 0,  # Baseline
            "medium_truck": 0.5,
            "heavy_truck": 1.0,
            "tanker": 1.5,
            "bus": 0.5
        }
        score += vehicle_impact.get(vehicle_type, 0)
        
        # Adjust based on sensitive areas
        if sensitive_areas:
            # More weight for highly protected areas
            national_parks = sum(1 for area in sensitive_areas if area.get('type') == 'national_park')
            wildlife_sanctuaries = sum(1 for area in sensitive_areas if area.get('type') == 'wildlife_sanctuary')
            
            # Increase score based on number and type of sensitive areas
            score += min(1.0, (len(sensitive_areas) * 0.2))  # Cap at +1.0
            score += min(1.0, (national_parks * 0.3 + wildlife_sanctuaries * 0.3))  # Cap at +1.0
        else:
            # Route doesn't pass through any sensitive areas
            score -= 1.0
        
        # Ensure score is within bounds (1-5)
        return max(1, min(5, round(score)))