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

    def get_nearby_stations(self, lat, lon, radius=0.5):
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

        mileage = 10  # miles per gallon
        tank_capacity = 100  # gallons

        fuel_left = tank_capacity
        total_cost = 0
        stops = []
        used_stations = set() 

        for i in range(0, len(route), 20):
            current_point = route[i]

            nearby = self.get_nearby_stations(
                current_point[0], current_point[1], radius=0.5
            )

            if not nearby:
                continue

            current_station = min(nearby, key=lambda x: x["price"])

            cheaper_found = False

            # Look ahead for cheaper station
            for j in range(i + 1, min(i + 50, len(route))):
                next_point = route[j]

                future_stations = self.get_nearby_stations(
                    next_point[0], next_point[1], radius=0.5
                )

                if not future_stations:
                    continue

                cheapest_future = min(future_stations, key=lambda x: x["price"])

                if cheapest_future["price"] < current_station["price"]:
                    cheaper_found = True
                    break

            # Refuel decision
            if fuel_left < tank_capacity * 0.3:
                gallons_needed = tank_capacity - fuel_left
                cost = gallons_needed * current_station["price"]

                total_cost += cost
                fuel_left = tank_capacity

                station_id = current_station["OPIS Truckstop ID"]

                if station_id not in used_stations:
                    used_stations.add(station_id)

                    stops.append({
                        "city": current_station["City"].strip(),
                        "price": float(current_station["price"]),
                        "cost": float(cost)
                    })

            # simulate fuel consumption
            fuel_left -= 5
            if fuel_left < 0:
                fuel_left = 0

        return stops, total_cost