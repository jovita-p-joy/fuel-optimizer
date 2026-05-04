from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.services.route_service import RouteService
from api.services.fuel_service import FuelService

import requests

cache = {}


from django.shortcuts import render

def home(request):
    return render(request, "index.html")


# 🔹 Convert place name → coordinates
def get_coordinates(place):
    if place in cache:
         return cache[place]
    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": place,
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "fuel-optimizer-app"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code != 200:
            print("Geocoding error:", response.status_code)
            return None

        data = response.json()

        if not data:
            print("No location found for:", place)
            return None

        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        
        coords = [lon, lat]
        cache[place] = coords

        return coords

  

    except Exception as e:
        print("Geocoding Exception:", e)
        return None


@api_view(["GET"])
def optimize_route(request):
    start = request.GET.get("start")
    end = request.GET.get("end")

    # ✅ Validate input
    if not start or not end:
        return Response(
            {"error": "Please provide both start and end locations"},
            status=400
        )

    try:
        # 🔹 Convert place → coordinates
        start_coords = get_coordinates(start)
        end_coords = get_coordinates(end)

        if not start_coords or not end_coords:
            return Response(
                {"error": "Invalid location. Try simpler place names"},
                status=400
            )

        # 🔹 Initialize services
        rs = RouteService()
        fs = FuelService()

        # 🔹 Get route
        result = rs.get_route(start_coords, end_coords)

        if result is None:
            return Response(
                {"error": "Route service unavailable. Try again later"},
                status=500
            )

        route, distance = result

        # 🔹 Optimize fuel stops
        stops, total_cost = fs.optimize_fuel_stops(route)

        # 🔹 Final response
        return Response({
            "start": start,
            "end": end,
            "distance_km": round(distance, 2),
            "fuel_stops": stops,
            "total_cost": round(total_cost, 2),
            "route_points_sample": route[:30]  # reduced for speed
        })

    except Exception as e:
        print("API ERROR:", e)
        return Response(
            {"error": "Internal server error"},
            status=500
        )