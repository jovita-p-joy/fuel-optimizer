import pandas as pd
import requests
import time
import os

INPUT_FILE = "fuel_optimizer/data/fuel-prices-for-be-assessment.csv"
OUTPUT_FILE = "fuel_optimizer/data/fuel_with_coords.csv"

# 🔥 Cache to avoid duplicate API calls
cache = {}


def get_coordinates(address, city, state):
    key = f"{city}_{state}"

    if key in cache:
        return cache[key]

    query = f"{city}, {state}, USA"
    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": query,
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "fuel-optimizer-app"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])

                cache[key] = (lat, lon)
                return lat, lon

    except Exception as e:
        print(f"Error: {e}")

    return None, None


def main():
    df = pd.read_csv(INPUT_FILE)

    if os.path.exists(OUTPUT_FILE):
        try:
            processed_df = pd.read_csv(OUTPUT_FILE)
            start_index = len(processed_df)
            print(f"Resuming from row {start_index}")
        except:
            print("⚠️ Corrupted file detected. Restarting...")
            processed_df = pd.DataFrame()
            start_index = 0
    else:
        processed_df = pd.DataFrame()
        start_index = 0

    total = len(df)

    for i in range(start_index, total):
        row = df.iloc[i]

        address = str(row["Address"])
        city = str(row["City"])
        state = str(row["State"])

        lat, lon = get_coordinates(address, city, state)

        new_row = row.to_dict()
        new_row["latitude"] = lat
        new_row["longitude"] = lon

        processed_df = pd.concat(
            [processed_df, pd.DataFrame([new_row])],
            ignore_index=True
        )

        # 🔥 Save every 20 rows instead of every row
        if i % 20 == 0:
            processed_df.to_csv(OUTPUT_FILE, index=False)

        print(f"Processed {i+1}/{total} → {city}, {state}")

        time.sleep(1)  # REQUIRED for Nominatim

    # Final save
    processed_df.to_csv(OUTPUT_FILE, index=False)

    print("✅ DONE! File saved as fuel_with_coords.csv")


if __name__ == "__main__":
    main()