import requests
import sqlite3
import os
import time
import json
import flet as ft

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

# Set the relative path to the JSON file
json_file_path = os.path.join("jma", "areas.json")

# Load the region data from the uploaded JSON file
with open(json_file_path, "r", encoding="utf-8") as file:
    region_data = json.load(file)

# Extract the region names and codes for the initial dropdown
REGIONS = {region["name"]: region_code for region_code, region in region_data["centers"].items()}

def get_weather_forecast(region_code):
    # Fetch weather forecast for the given region code
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{region_code}.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()
        area_name = data[0]["timeSeries"][0]["areas"][0]["area"]["name"]
        report_datetime = data[0]["reportDatetime"]
        weather_forecast = data[0]["timeSeries"][0]["areas"][0]["weathers"]

        formatted_forecast = f"発表機関: 気象庁\n発表日時: {report_datetime}\n{area_name} の天気予報:\n"
        formatted_forecast += "\n".join([f"- {weather}" for weather in weather_forecast])

        # Save the forecast to the database as well
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM weather WHERE region_code = ?', (region_code,))
        result = cursor.fetchone()

        if result:
            # Update existing record
            cursor.execute('''
                UPDATE weather
                SET "weather forecast" = ?
                WHERE region_code = ?
            ''', (formatted_forecast, region_code))
        else:
            # Insert new record
            cursor.execute('''
                INSERT INTO weather (region_code, area, "Presenting organization", "Announcement date and time", "weather forecast")
                VALUES (?, ?, ?, ?, ?)
            ''', (region_code, area_name, "Japan Meteorological Agency", report_datetime, formatted_forecast))

        conn.commit()
        conn.close()

        return formatted_forecast

    except requests.Timeout:
        return "リクエストがタイムアウトしました。再度試してください。"
    except requests.RequestException as e:
        return f"天気予報の取得に失敗しました: {e}"

def update_weather(region_code, weather_info, page):
    if region_code:
        # サブ地域の名前を取得
        region_name = next(
            (region["name"] for region in region_data["centers"].values() if region_code in region["children"]),
            "不明な地域"
        )

        # 天気予報情報を取得
        weather_forecast = get_weather_forecast(region_code)

        # 天気情報を表示
        weather_info.value = f"地域: {region_name}\n\n{weather_forecast}"
        page.update()

def update_children(region_code, dropdown_children, page):
    # 子地域を取得
    children = region_data["centers"].get(region_code, {}).get("children", [])

    # 子地域のオプションを設定
    dropdown_children.options = [
        ft.dropdown.Option(text=f"{region_data['offices'].get(child, {}).get('name', child)} 地域", key=child)
        for child in children
    ]
    page.update()

def show_past_data(e, page):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM weather')
    rows = cursor.fetchall()
    conn.close()

    # Clear previous controls
    page.controls.clear()

    # Display past weather data
    data = "\n".join([f"Region: {row[1]}, Date: {row[3]}, Forecast: {row[4]}" for row in rows])
    page.add(ft.Text(data))

    # Add the "Back to Main" button
    back_button = ft.ElevatedButton(text="Back to Main", on_click=lambda e: back_to_main(page))
    page.add(back_button)
    page.update()

def back_to_main(page):
    # Return to the main page layout
    page.controls.clear()

    # Add the dropdowns and weather info section back
    weather_info = ft.Text(value="地域を選択してください", size=16)
    dropdown = ft.Dropdown(
        hint_text="地域を選択",
        options=[ft.dropdown.Option(text=name, key=code) for name, code in REGIONS.items()],
        on_change=lambda e: update_children(e.control.value, dropdown_children, page)
    )
    dropdown_children = ft.Dropdown(hint_text="サブ地域を選択")
    dropdown_children.on_change = lambda e: update_weather(e.control.value, weather_info, page)

    # Layout structure
    page.add(
        ft.Column(
            [
                ft.Container(
                    ft.Text("天気予報", size=24, weight="bold", color=ft.colors.WHITE),
                    padding=20,
                    bgcolor=ft.colors.BLUE,
                    alignment=ft.alignment.center_left,
                ),
                dropdown,
                dropdown_children,
                ft.Container(
                    content=weather_info,
                    padding=20,
                    bgcolor=ft.colors.BLUE_50,
                    border_radius=ft.border_radius.all(8),
                ),
            ],
            spacing=20,
            width=600,
        )
    )
    page.update()

def main(page: ft.Page):
    page.title = "天気予報検索"
    page.horizontal_alignment = ft.CrossAxisAlignment.START
    page.vertical_alignment = ft.MainAxisAlignment.START

    # Text box for displaying weather info
    weather_info = ft.Text(value="地域を選択してください", size=16)

    # Dropdown for selecting a region
    dropdown = ft.Dropdown(
        hint_text="地域を選択",
        options=[ft.dropdown.Option(text=name, key=code) for name, code in REGIONS.items()],
        on_change=lambda e: update_children(e.control.value, dropdown_children, page)
    )

    # Dropdown for selecting sub-regions (children)
    dropdown_children = ft.Dropdown(hint_text="サブ地域を選択")
    dropdown_children.on_change = lambda e: update_weather(e.control.value, weather_info, page)

    # Layout structure
    page.add(
        ft.Column(
            [
                ft.Container(
                    ft.Text("天気予報", size=24, weight="bold", color=ft.colors.WHITE),
                    padding=20,
                    bgcolor=ft.colors.BLUE,
                    alignment=ft.alignment.center_left,
                ),
                dropdown,
                dropdown_children,
                ft.Container(
                    content=weather_info,
                    padding=20,
                    bgcolor=ft.colors.BLUE_50,
                    border_radius=ft.border_radius.all(8),
                ),
            ],
            spacing=20,
            width=600,
        )
    )

    past_data_button = ft.ElevatedButton(text="Past Data", on_click=lambda e: show_past_data(e, page))
    page.add(past_data_button)

# Run the application
ft.app(target=main)
