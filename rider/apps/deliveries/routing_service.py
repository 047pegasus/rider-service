"""
Route calculation service using OSRM (Open Source Routing Machine)
Falls back to direct line if OSRM is unavailable
"""
import requests
from typing import List, Tuple, Optional
from .services import DeliveryService


class RoutingService:
    OSRM_BASE_URL = "http://router.project-osrm.org/route/v1/driving"
    
    @staticmethod
    def calculate_route(
        start: Tuple[float, float],
        end: Tuple[float, float],
        via_points: Optional[List[Tuple[float, float]]] = None
    ) -> List[Tuple[float, float]]:
        """
        Calculate route between points using OSRM.
        Returns list of (lat, lng) tuples.
        """
        try:
            # Build coordinates string
            coords = [f"{start[1]},{start[0]}"]  # OSRM uses lng,lat
            if via_points:
                for point in via_points:
                    coords.append(f"{point[1]},{point[0]}")
            coords.append(f"{end[1]},{end[0]}")
            
            coords_str = ";".join(coords)
            url = f"{RoutingService.OSRM_BASE_URL}/{coords_str}?overview=full&geometries=geojson"
            
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "Ok" and data.get("routes"):
                    route = data["routes"][0]
                    geometry = route["geometry"]["coordinates"]
                    # Convert from [lng, lat] to [lat, lng]
                    return [(coord[1], coord[0]) for coord in geometry]
        except Exception as e:
            print(f"OSRM routing failed: {e}, using direct route")
        
        # Fallback to direct line with intermediate points
        return RoutingService._direct_route(start, end)
    
    @staticmethod
    def _direct_route(
        start: Tuple[float, float],
        end: Tuple[float, float],
        num_points: int = 50
    ) -> List[Tuple[float, float]]:
        """Generate intermediate points for direct route"""
        points = []
        for i in range(num_points + 1):
            ratio = i / num_points
            lat = start[0] + (end[0] - start[0]) * ratio
            lng = start[1] + (end[1] - start[1]) * ratio
            points.append((lat, lng))
        return points
    
    @staticmethod
    def calculate_route_distance(route_points: List[Tuple[float, float]]) -> float:
        """Calculate total distance for a route"""
        if len(route_points) < 2:
            return 0.0
        
        total = 0.0
        for i in range(len(route_points) - 1):
            total += DeliveryService.calculate_distance(
                route_points[i][0], route_points[i][1],
                route_points[i + 1][0], route_points[i + 1][1]
            )
        return total


routing_service = RoutingService()
