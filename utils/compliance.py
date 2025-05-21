import json
import os
import datetime
import logging
from geopy.distance import geodesic

# Set up logger
logger = logging.getLogger(__name__)

class ComplianceChecker:
    """Handle regulatory compliance checks for routes"""
    
    def __init__(self, config_dir="compliance_data"):
        self.config_dir = config_dir
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        # Load compliance data
        self.cmvr_rules = self._load_json_data('cmvr_rules.json')
        self.ais_requirements = self._load_json_data('ais_requirements.json')
        self.restricted_zones = self._load_json_data('restricted_zones.json')
        self.rtsp_rules = self._load_json_data('rtsp_rules.json')
    
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
        if filename == 'cmvr_rules.json':
            return {
                "vehicle_categories": {
                    "car": "Personal vehicle with GVW not exceeding 3.5 tonnes",
                    "medium_truck": "Goods vehicle with GVW exceeding 3.5 tonnes but not exceeding 12 tonnes",
                    "heavy_truck": "Goods vehicle with GVW exceeding 12 tonnes",
                    "tanker": "Vehicle carrying hazardous materials in liquid form",
                    "bus": "Passenger vehicle with seating capacity exceeding 13 passengers"
                },
                "speed_limits": {
                    "car": {
                        "national_highway": 80,
                        "state_highway": 70,
                        "urban_road": 60,
                        "residential_area": 40
                    },
                    "medium_truck": {
                        "national_highway": 70,
                        "state_highway": 60,
                        "urban_road": 50,
                        "residential_area": 35
                    },
                    "heavy_truck": {
                        "national_highway": 60,
                        "state_highway": 55,
                        "urban_road": 45,
                        "residential_area": 30
                    },
                    "tanker": {
                        "national_highway": 60,
                        "state_highway": 55,
                        "urban_road": 45,
                        "residential_area": 30
                    },
                    "bus": {
                        "national_highway": 70,
                        "state_highway": 60,
                        "urban_road": 50,
                        "residential_area": 35
                    }
                },
                "driver_requirements": {
                    "commercial_driving_license": True,
                    "medical_fitness_certificate": True,
                    "training_certificate": True
                },
                "vehicle_requirements": {
                    "car": {
                        "pollution_certificate": {"required": True, "validity_days": 180},
                        "insurance": {"required": True, "validity_days": 365},
                        "first_aid_kit": {"required": True}
                    },
                    "medium_truck": {
                        "pollution_certificate": {"required": True, "validity_days": 180},
                        "fitness_certificate": {"required": True, "validity_days": 365},
                        "insurance": {"required": True, "validity_days": 365},
                        "reflective_tape": {"required": True},
                        "fire_extinguisher": {"required": True},
                        "first_aid_kit": {"required": True}
                    },
                    "heavy_truck": {
                        "pollution_certificate": {"required": True, "validity_days": 180},
                        "fitness_certificate": {"required": True, "validity_days": 365},
                        "insurance": {"required": True, "validity_days": 365},
                        "reflective_tape": {"required": True},
                        "rear_marking_plate": {"required": True},
                        "fire_extinguisher": {"required": True},
                        "first_aid_kit": {"required": True},
                        "speed_governor": {"required": True, "max_speed": 60}
                    },
                    "tanker": {
                        "pollution_certificate": {"required": True, "validity_days": 180},
                        "fitness_certificate": {"required": True, "validity_days": 365},
                        "insurance": {"required": True, "validity_days": 365},
                        "reflective_tape": {"required": True},
                        "rear_marking_plate": {"required": True},
                        "fire_extinguisher": {"required": True, "count": 2},
                        "first_aid_kit": {"required": True},
                        "speed_governor": {"required": True, "max_speed": 60},
                        "hazmat_license": {"required": True, "validity_days": 365},
                        "emergency_information_panel": {"required": True}
                    },
                    "bus": {
                        "pollution_certificate": {"required": True, "validity_days": 180},
                        "fitness_certificate": {"required": True, "validity_days": 365},
                        "insurance": {"required": True, "validity_days": 365},
                        "reflective_tape": {"required": True},
                        "fire_extinguisher": {"required": True},
                        "first_aid_kit": {"required": True},
                        "emergency_exit": {"required": True},
                        "speed_governor": {"required": True, "max_speed": 70}
                    }
                }
            }
        elif filename == 'ais_requirements.json':
            return {
                "gps_tracking": {
                    "required": True,
                    "update_frequency_seconds": 30,
                    "accuracy_meters": 5,
                    "applicable_vehicles": ["medium_truck", "heavy_truck", "tanker", "bus"]
                },
                "panic_button": {
                    "required": True,
                    "alert_recipients": ["control_room", "nearest_police", "owner"],
                    "applicable_vehicles": ["tanker", "bus"]
                },
                "vehicle_health_monitoring": {
                    "required": True,
                    "parameters": ["engine_temperature", "fuel_level", "battery_status"],
                    "applicable_vehicles": ["heavy_truck", "tanker", "bus"]
                }
            }
        elif filename == 'restricted_zones.json':
            return {
                "time_restricted_zones": [
                    {
                        "name": "City Center",
                        "coordinates": {"lat": 17.3850, "lng": 78.4867},
                        "radius_km": 5,
                        "restrictions": {
                            "heavy_vehicles": {
                                "restricted_hours": ["07:00-10:00", "17:00-20:00"]
                            }
                        }
                    }
                ],
                "no_entry_zones": [
                    {
                        "name": "School Zone",
                        "coordinates": {"lat": 17.4123, "lng": 78.4126},
                        "radius_km": 0.5,
                        "restrictions": {
                            "all_vehicles": {
                                "restricted_hours": ["08:00-09:30", "14:30-16:00"]
                            }
                        }
                    }
                ],
                "hazardous_materials_restricted": [
                    {
                        "name": "Water Body Protection Zone",
                        "coordinates": {"lat": 17.4150, "lng": 78.4680},
                        "radius_km": 2,
                        "restrictions": {
                            "hazardous_materials": {
                                "restricted_materials": ["flammable", "toxic", "corrosive"],
                                "restricted_hours": ["always"]
                            }
                        }
                    }
                ]
            }
        elif filename == 'rtsp_rules.json':
            return {
                "driving_hour_limits": {
                    "car": {
                        "continuous_driving_hours": 4,
                        "daily_driving_hours": 8,
                        "weekly_driving_hours": 48
                    },
                    "medium_truck": {
                        "continuous_driving_hours": 4,
                        "daily_driving_hours": 8,
                        "weekly_driving_hours": 48
                    },
                    "heavy_truck": {
                        "continuous_driving_hours": 4,
                        "daily_driving_hours": 8,
                        "weekly_driving_hours": 48
                    },
                    "tanker": {
                        "continuous_driving_hours": 3.5,
                        "daily_driving_hours": 7,
                        "weekly_driving_hours": 42
                    },
                    "bus": {
                        "continuous_driving_hours": 4,
                        "daily_driving_hours": 8,
                        "weekly_driving_hours": 48
                    }
                },
                "rest_period_requirements": {
                    "car": {
                        "short_break_minutes": 30,
                        "daily_rest_hours": 10,
                        "weekly_rest_hours": 24
                    },
                    "medium_truck": {
                        "short_break_minutes": 30,
                        "daily_rest_hours": 10,
                        "weekly_rest_hours": 24
                    },
                    "heavy_truck": {
                        "short_break_minutes": 45,
                        "daily_rest_hours": 11,
                        "weekly_rest_hours": 45
                    },
                    "tanker": {
                        "short_break_minutes": 45,
                        "daily_rest_hours": 11,
                        "weekly_rest_hours": 45
                    },
                    "bus": {
                        "short_break_minutes": 30,
                        "daily_rest_hours": 10,
                        "weekly_rest_hours": 24
                    }
                },
                "night_driving_restrictions": {
                    "car": {
                        "restricted_hours": ["none"]
                    },
                    "medium_truck": {
                        "restricted_hours": ["none"]
                    },
                    "heavy_truck": {
                        "restricted_hours": ["23:00-05:00"],
                        "exemptions": ["essential_supplies", "emergency_services"]
                    },
                    "tanker": {
                        "restricted_hours": ["22:00-06:00"],
                        "exemptions": ["emergency_services"]
                    },
                    "bus": {
                        "restricted_hours": ["none"]
                    }
                }
            }
        else:
            return {}
    
    def check_vehicle_compliance(self, vehicle_type):
        """Check vehicle compliance requirements"""
        compliance_status = {
            "compliant": True,
            "requirements": [],
            "violations": []
        }
        
        # Check if vehicle type is recognized
        if vehicle_type not in self.cmvr_rules["vehicle_categories"]:
            compliance_status["compliant"] = False
            compliance_status["violations"].append({
                "code": "UNKNOWN_VEHICLE_TYPE",
                "description": f"Vehicle type '{vehicle_type}' not recognized in CMVR rules"
            })
            return compliance_status
        
        # Add vehicle-specific requirements
        if vehicle_type in self.cmvr_rules["vehicle_requirements"]:
            for req, details in self.cmvr_rules["vehicle_requirements"][vehicle_type].items():
                required = details.get("required", False)
                
                compliance_status["requirements"].append({
                    "name": req,
                    "description": self._get_requirement_description(req),
                    "mandatory": required,
                    "details": details
                })
            
        # AIS-140 compliance check
        if "gps_tracking" in self.ais_requirements:
            gps_req = self.ais_requirements["gps_tracking"]
            applicable_vehicles = gps_req.get("applicable_vehicles", [])
            
            if vehicle_type in applicable_vehicles:
                compliance_status["requirements"].append({
                    "name": "gps_tracking",
                    "description": "GPS Tracking as per AIS-140 standards",
                    "update_frequency": f"{gps_req['update_frequency_seconds']} seconds",
                    "mandatory": gps_req.get("required", False)
                })
            
        # Panic button compliance check
        if "panic_button" in self.ais_requirements:
            panic_req = self.ais_requirements["panic_button"]
            applicable_vehicles = panic_req.get("applicable_vehicles", [])
            
            if vehicle_type in applicable_vehicles:
                compliance_status["requirements"].append({
                    "name": "panic_button",
                    "description": "Emergency Panic Button as per AIS-140",
                    "mandatory": panic_req.get("required", False)
                })
        
        # Vehicle health monitoring compliance check
        if "vehicle_health_monitoring" in self.ais_requirements:
            health_req = self.ais_requirements["vehicle_health_monitoring"]
            applicable_vehicles = health_req.get("applicable_vehicles", [])
            
            if vehicle_type in applicable_vehicles:
                compliance_status["requirements"].append({
                    "name": "vehicle_health_monitoring",
                    "description": "Vehicle Health Monitoring System",
                    "mandatory": health_req.get("required", False),
                    "parameters": health_req.get("parameters", [])
                })
        
        return compliance_status
    
    def _get_requirement_description(self, req_code):
        """Get human-readable description for requirement code"""
        descriptions = {
            "pollution_certificate": "Valid Pollution Under Control (PUC) Certificate",
            "fitness_certificate": "Vehicle Fitness Certificate",
            "insurance": "Commercial Vehicle Insurance",
            "reflective_tape": "High-Visibility Reflective Tape on vehicle body",
            "rear_marking_plate": "Rear Marking Plate for commercial vehicles",
            "fire_extinguisher": "Fire Extinguisher",
            "first_aid_kit": "First Aid Kit",
            "speed_governor": "Speed Limiting Device/Governor",
            "hazmat_license": "Hazardous Materials Transportation License",
            "emergency_information_panel": "Emergency Information Panel",
            "emergency_exit": "Emergency Exit",
            "gps_tracking": "GPS Vehicle Tracking System",
            "panic_button": "Emergency Panic Button",
            "vehicle_health_monitoring": "Vehicle Health Monitoring System"
        }
        return descriptions.get(req_code, req_code.replace("_", " ").title())
    
    def check_speed_limits(self, vehicle_type, route_data):
        """Check speed limits for the route based on vehicle type"""
        speed_compliance = {
            "vehicle_type": vehicle_type,
            "road_segments": []
        }
        
        # Only process if vehicle type is known
        if vehicle_type not in self.cmvr_rules["vehicle_categories"]:
            speed_compliance["error"] = "Unknown vehicle type"
            return speed_compliance
        
        # Extract speed limits for this vehicle type
        vehicle_speed_limits = self.cmvr_rules["speed_limits"].get(vehicle_type, {})
        
        # Process route segments to determine road types and applicable speed limits
        # This is a simplified approach - in a real implementation, you would analyze
        # the route more thoroughly to determine road types
        
        return vehicle_speed_limits
    
    def check_restricted_zones(self, route_points):
        """Check if route passes through restricted zones"""
        restricted_zone_warnings = []
        
        # Check each point in the route against all restricted zones
        sample_interval = max(1, len(route_points) // 20)  # Check approximately every 5% of route
        
        for i in range(0, len(route_points), sample_interval):
            if i >= len(route_points):
                break
                
            point_coord = (route_points[i][0], route_points[i][1])
            
            # Check time restricted zones
            for zone in self.restricted_zones.get("time_restricted_zones", []):
                zone_center = (zone["coordinates"]["lat"], zone["coordinates"]["lng"])
                distance = geodesic(point_coord, zone_center).kilometers
                
                if distance <= zone["radius_km"]:
                    # Route passes through this restricted zone
                    restrictions = zone.get("restrictions", {})
                    
                    # Check if there are heavy vehicle restrictions
                    if "heavy_vehicles" in restrictions:
                        restricted_hours = restrictions["heavy_vehicles"].get("restricted_hours", [])
                        
                        restricted_zone_warnings.append({
                            "type": "time_restricted_zone",
                            "name": zone["name"],
                            "point_index": i,
                            "coordinates": {"lat": point_coord[0], "lng": point_coord[1]},
                            "restricted_hours": restricted_hours
                        })
            
            # Check no entry zones
            for zone in self.restricted_zones.get("no_entry_zones", []):
                zone_center = (zone["coordinates"]["lat"], zone["coordinates"]["lng"])
                distance = geodesic(point_coord, zone_center).kilometers
                
                if distance <= zone["radius_km"]:
                    # Route passes through this no entry zone
                    restrictions = zone.get("restrictions", {})
                    
                    if "all_vehicles" in restrictions:
                        restricted_hours = restrictions["all_vehicles"].get("restricted_hours", [])
                        
                        restricted_zone_warnings.append({
                            "type": "no_entry_zone",
                            "name": zone["name"],
                            "point_index": i,
                            "coordinates": {"lat": point_coord[0], "lng": point_coord[1]},
                            "restricted_hours": restricted_hours
                        })
            
            # Check hazardous materials restricted zones
            for zone in self.restricted_zones.get("hazardous_materials_restricted", []):
                zone_center = (zone["coordinates"]["lat"], zone["coordinates"]["lng"])
                distance = geodesic(point_coord, zone_center).kilometers
                
                if distance <= zone["radius_km"]:
                    # Route passes through this hazmat restricted zone
                    restrictions = zone.get("restrictions", {})
                    
                    if "hazardous_materials" in restrictions:
                        restricted_materials = restrictions["hazardous_materials"].get("restricted_materials", [])
                        restricted_hours = restrictions["hazardous_materials"].get("restricted_hours", [])
                        
                        restricted_zone_warnings.append({
                            "type": "hazmat_restricted_zone",
                            "name": zone["name"],
                            "point_index": i,
                            "coordinates": {"lat": point_coord[0], "lng": point_coord[1]},
                            "restricted_materials": restricted_materials,
                            "restricted_hours": restricted_hours
                        })
        
        # Remove duplicates (same zone detected multiple times)
        unique_zones = {}
        for warning in restricted_zone_warnings:
            zone_key = f"{warning['type']}_{warning['name']}"
            if zone_key not in unique_zones:
                unique_zones[zone_key] = warning
        
        return list(unique_zones.values())
    
    def check_rtsp_compliance(self, route_duration_seconds, vehicle_type="car"):
        """Check compliance with Road Transport Safety Protocol (driving hours, rest periods)"""
        rtsp_compliance = {
            "compliant": True,
            "warnings": [],
            "recommendations": []
        }
        
        # Ensure vehicle type is valid
        if vehicle_type not in self.rtsp_rules["driving_hour_limits"]:
            rtsp_compliance["warnings"].append({
                "code": "UNKNOWN_VEHICLE_TYPE",
                "description": f"Unknown vehicle type '{vehicle_type}' for RTSP rules, using default values"
            })
            vehicle_type = "car"  # Default to car rules
        
        # Get RTSP rules for this vehicle type
        driving_limits = self.rtsp_rules["driving_hour_limits"].get(vehicle_type, 
                                                                   self.rtsp_rules["driving_hour_limits"]["car"])
        rest_requirements = self.rtsp_rules["rest_period_requirements"].get(vehicle_type,
                                                                           self.rtsp_rules["rest_period_requirements"]["car"])
        night_restrictions = self.rtsp_rules["night_driving_restrictions"].get(vehicle_type,
                                                                              self.rtsp_rules["night_driving_restrictions"]["car"])
        
        # Calculate driving hours
        driving_hours = route_duration_seconds / 3600
        
        # Check continuous driving limit
        continuous_driving_limit = driving_limits["continuous_driving_hours"]
        if driving_hours > continuous_driving_limit:
            rtsp_compliance["compliant"] = False
            rtsp_compliance["warnings"].append({
                "code": "CONTINUOUS_DRIVING_EXCEEDED",
                "description": f"Route duration ({driving_hours:.1f} hours) exceeds continuous driving limit ({continuous_driving_limit} hours)"
            })
            
            # Calculate required breaks
            breaks_needed = max(1, int(driving_hours / continuous_driving_limit))
            short_break_minutes = rest_requirements["short_break_minutes"]
            
            rtsp_compliance["recommendations"].append({
                "code": "SCHEDULED_BREAKS",
                "description": f"Schedule {breaks_needed} break(s) of at least {short_break_minutes} minutes each"
            })
        
        # Check daily driving limit
        daily_driving_limit = driving_limits["daily_driving_hours"]
        if driving_hours > daily_driving_limit:
            rtsp_compliance["compliant"] = False
            rtsp_compliance["warnings"].append({
                "code": "DAILY_DRIVING_EXCEEDED",
                "description": f"Route duration ({driving_hours:.1f} hours) exceeds daily driving limit ({daily_driving_limit} hours)"
            })
            
            # Recommend overnight halts
            overnight_halts_needed = max(1, int(driving_hours / daily_driving_limit))
            
            rtsp_compliance["recommendations"].append({
                "code": "OVERNIGHT_HALTS",
                "description": f"Plan {overnight_halts_needed} overnight halt(s) for driver rest"
            })
        
        # Check night driving restrictions
        restricted_hours = night_restrictions["restricted_hours"]
        if restricted_hours and restricted_hours[0] != "none":
            rtsp_compliance["recommendations"].append({
                "code": "AVOID_NIGHT_DRIVING",
                "description": f"Avoid driving during restricted night hours: {', '.join(restricted_hours)}"
            })
        
        return rtsp_compliance
    
    def generate_rest_stop_recommendations(self, route_data, duration_seconds, poi_data, vehicle_type="car"):
        """Generate recommendations for rest stops based on RTSP rules"""
        # Get vehicle-specific rules
        if vehicle_type not in self.rtsp_rules["driving_hour_limits"]:
            vehicle_type = "car"  # Default to car rules
            
        driving_limits = self.rtsp_rules["driving_hour_limits"].get(vehicle_type, 
                                                                   self.rtsp_rules["driving_hour_limits"]["car"])
        
        continuous_driving_seconds = driving_limits["continuous_driving_hours"] * 3600
        
        recommendations = []
        
        # Only make recommendations if route is long enough to require a break
        if duration_seconds <= continuous_driving_seconds:
            return recommendations
        
        # Calculate how many breaks are needed
        breaks_needed = int(duration_seconds / continuous_driving_seconds)
        
        # Identify potential rest stop locations
        potential_stops = []
        
        # Add fuel stations as potential stops
        if "petrol_bunks" in poi_data:
            for name, location in poi_data["petrol_bunks"].items():
                potential_stops.append({
                    "name": name,
                    "location": location,
                    "type": "fuel",
                    "amenities": ["fuel", "restroom"]
                })
        
        # Add food stops as potential stops
        if "food_stops" in poi_data:
            for name, location in poi_data["food_stops"].items():
                potential_stops.append({
                    "name": name,
                    "location": location,
                    "type": "food",
                    "amenities": ["food", "restroom"]
                })
        
        # If we have potential stops, space them evenly along the route
        if potential_stops and breaks_needed > 0:
            # This is a simplified approach - in a real implementation,
            # you would calculate the actual position along the route
            segment_duration = duration_seconds / (breaks_needed + 1)
            
            for i in range(1, breaks_needed + 1):
                target_time = i * segment_duration
                # Find closest potential stop to this time point
                # (simplified - in reality, would match to route position)
                
                if i <= len(potential_stops):
                    stop = potential_stops[i-1]
                    driving_hours = (target_time / 3600)
                    
                    recommendations.append({
                        "stop_number": i,
                        "estimated_driving_time": f"{driving_hours:.1f} hours",
                        "recommended_break_minutes": self.rtsp_rules["rest_period_requirements"][vehicle_type]["short_break_minutes"],
                        "name": stop["name"],
                        "location": stop["location"],
                        "type": stop["type"],
                        "amenities": stop["amenities"]
                    })
        
        return recommendations