import requests
import sqlite3
import os
import time
import json

db_path = 'jma2.db'

# Create database table if it doesn't exist
if not os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE weather (
            region_code INTEGER PRIMARY KEY,
            area TEXT NOT NULL,
            "Presenting organization" TEXT NOT NULL,
            "Announcement date and time" TEXT NOT NULL,
            "weather forecast" TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_weather(region_code):
    url = f'https://www.jma.go.jp/bosai/forecast/data/forecast/{region_code}.json'
    try:
        response = requests.get(url)
        response.raise_for_status()  # This will raise an error if the status code is 4xx or 5xx
        data = response.json()

        # Extract weather data
        area_name = data[0]['timeSeries'][0]['areas'][0]['area']['name']
        report_datetime = data[0]['reportDatetime']
        weather_forecast = "\n".join(data[0]['timeSeries'][0]['areas'][0]['weathers'])

        # Insert or update the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM weather WHERE region_code = ?', (region_code,))
        result = cursor.fetchone()

        if result:
            # Update existing record
            cursor.execute('''
                UPDATE weather
                SET area = ?, "Presenting organization" = ?, "Announcement date and time" = ?, "weather forecast" = ?
                WHERE region_code = ?
            ''', (area_name, "Japan Meteorological Agency", report_datetime, weather_forecast, region_code))
        else:
            # Insert new record
            cursor.execute('''
                INSERT INTO weather (region_code, area, "Presenting organization", "Announcement date and time", "weather forecast")
                VALUES (?, ?, ?, ?, ?)
            ''', (region_code, area_name, "Japan Meteorological Agency", report_datetime, weather_forecast))

        conn.commit()
        conn.close()

        print(f"Weather data for region {region_code} updated successfully!")

    except requests.RequestException as e:
        print(f"Failed to fetch weather data for region {region_code}: {e}")

if __name__ == "__main__":
    # Initialize region_codes as an empty list
    region_codes = []

    # Load region codes from areas.json dynamically
    areas_path = 'areas.json'

    if os.path.exists(areas_path):
        with open(areas_path, 'r', encoding='utf-8') as f:
            areas_data = json.load(f)
            for area in areas_data:
                if 'offices' in area:  # Assuming 'offices' contains the region codes
                    for office in area['offices']:
                        region_codes.append(office['code'])  # Add the region code to the list
                        print(f"Added region code: {office['code']}")

    # Fetch weather data for each region code
    for code in region_codes:
        get_weather(code)
        time.sleep(1)  # Delay for 1 second between requests
