import requests



def get_coordinates(place):
    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": place,
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "fuel-optimizer-app"
    }

    response = requests.get(url, params=params, headers=headers, timeout=5)

    if response.status_code != 200 or not response.json():
        return None

    data = response.json()[0]

    lat = float(data["lat"])
    lon = float(data["lon"])

    return [lon, lat]   # IMPORTANT: OSRM needs [lon, lat]

def get_coordinates(place):
    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": place,
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "fuel-optimizer-app"
    }

    response = requests.get(url, params=params, headers=headers)

    if response.status_code != 200:
        return None

    data = response.json()

    if not data:
        return None

    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])

    return [lon, lat]   # IMPORTANT: [lon, lat]

class RouteService:
    def get_route(self, start_coords, end_coords):
        url = f"https://router.project-osrm.org/route/v1/driving/{start_coords[0]},{start_coords[1]};{end_coords[0]},{end_coords[1]}?overview=full&geometries=geojson"

        try:
            response = requests.get(url, timeout=20)

            print("STATUS:", response.status_code)

            if response.status_code != 200:
                print("ERROR RESPONSE:", response.text)
                return None

            data = response.json()

            if "routes" not in data or len(data["routes"]) == 0:
                print("NO ROUTE FOUND")
                return None

            route = data["routes"][0]["geometry"]["coordinates"]
            distance = data["routes"][0]["distance"]

            return route, distance / 1000

        except Exception as e:
            print("ROUTE ERROR:", e)
            return None