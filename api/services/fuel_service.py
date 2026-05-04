import pandas as pd
from scipy.spatial import KDTree
import os
from api.services.route_service import RouteService


def calculate_distance(p1, p2):
    rs = RouteService()
    result = rs.get_route(p1, p2)

    if result is None:
        return None

    _, distance = result
    return distance


class FuelService:
    def __init__(self):
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "fuel_with_coords.csv"
        )

        if not os.path.exists(file_path):
            raise FileNotFoundError("fuel_with_coords.csv not found")

        df = pd.read_csv(file_path)

        # Clean data
        df = df.dropna(subset=["latitude", "longitude"])
        df = df.rename(columns={"Retail Price": "price"})
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df = df.dropna(subset=["price"])
        df = df.reset_index(drop=True)

        self.df = df

        # Build KDTree
        coords = df[["latitude", "longitude"]].values
        self.tree = KDTree(coords)

    def convert_route(self, route):
        # OSRM gives [lon, lat] → convert to (lat, lon)
        return [(point[1], point[0]) for point in route]

    def find_nearest_station(self, point):
        if self.tree is None:
            return None
        distance, index = self.tree.query(point)
        return self.df.iloc[index]

    def get_nearby_stations(self, lat, lon, radius=1.0):
        if self.tree is None:
            return []
        indexes = self.tree.query_ball_point([lat, lon], r=radius)
        return [self.df.iloc[i] for i in indexes]

    def get_cheapest_station(self, lat, lon, radius=0.5):
        stations = self.get_nearby_stations(lat, lon, radius)

        if not stations:
            return None

        return min(stations, key=lambda x: x["price"])

    def get_stations_along_route(self, route):
        stations = []
        seen = set()

        lat_lon_route = self.convert_route(route)

        for point in lat_lon_route:
            station = self.find_nearest_station(point)

            if station is None:
                continue

            station_id = station["OPIS Truckstop ID"]

            if station_id not in seen:
                seen.add(station_id)
                stations.append(station)

        return stations

    def optimize_fuel_stops(self, route):
        route = self.convert_route(route)

        fuel_left = 100
        tank_capacity = 100
        total_cost = 0
        stops = []
        used_stations = set()
        max_stops = 2 

        for point in route[::20]:
            if len(stops) >= max_stops:
                break
            nearby = self.get_nearby_stations(point[0], point[1], radius=2.0)

            if not nearby:
                continue

            # pick cheapest nearby station
            station = min(nearby, key=lambda x: x["price"])
            station_id = station["OPIS Truckstop ID"]

            # simple condition → refill when fuel < 50%
            if fuel_left < 50 and station_id not in used_stations:
                gallons_needed = min(tank_capacity - fuel_left, 50)
                cost = gallons_needed * station["price"]

                total_cost += cost
                fuel_left = tank_capacity

                used_stations.add(station_id)

                stops.append({
                    "city": station["City"],
                    "price": station["price"],
                    "cost": round(cost, 2)
                })

            fuel_left -= 5   # simulate consumption

        if not stops:
            first_point = route[0]
            nearby = self.get_nearby_stations(first_point[0], first_point[1], radius=3.0)

            if nearby:
                station = min(nearby, key=lambda x: x["price"])
                stops.append({
                    "city": station["City"],
                    "price": station["price"],
                    "cost": 100
                })
                total_cost = 100

        return stops, round(total_cost, 2)