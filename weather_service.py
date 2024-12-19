import requests
from config import ACCUWEATHER_API_KEY, GRAPHHOPPER_API_KEY

HEADERS = {
    "User-Agent": "WeatherBot/1.0 (d.druzhinin@edu.centraluniversity.ru)"  # Укажите ваш email или название приложения
}

def get_location_key(location):
    """
    Получение ключа локации из API AccuWeather.
    """
    url = f"http://dataservice.accuweather.com/locations/v1/cities/search?apikey={ACCUWEATHER_API_KEY}&q={location}&language=ru-ru"
    try:
        response = requests.get(url)
        response.raise_for_status()  
        data = response.json()
        if not data:
            raise Exception(f"Локация {location} не найдена.")
        return data[0]['Key']
    except requests.RequestException as e:
        raise Exception(f"Ошибка при получении ключа локации для {location}: {e}")
    except ValueError as e:
        raise Exception(f"Ошибка при обработке ответа API для {location}: {e}")

def get_weather_forecast(locations, days):
    """
    Получение прогноза погоды для заданных точек маршрута.
    """
    forecast = {}
    for location in locations:
        location_key = get_location_key(location)
        if not location_key:
            raise Exception(f"Локация {location} не найдена.")

        url = f"http://dataservice.accuweather.com/forecasts/v1/daily/5day/{location_key}?apikey={ACCUWEATHER_API_KEY}&language=ru-ru&details=true&metric=true"
        try:
            response = requests.get(url)
            response.raise_for_status()  
            data = response.json()
            forecast[location] = {}
            for day_data in data['DailyForecasts'][:days]:
                date = day_data['Date']
                forecast[location][date] = {
                    'temperature_min': day_data['Temperature']['Minimum']['Value'],
                    'temperature_max': day_data['Temperature']['Maximum']['Value'],
                    'precipitation_probability': day_data['Day']['PrecipitationProbability'],
                    'wind_speed': day_data['Day']['Wind']['Speed']['Value']
                }
        except requests.RequestException as e:
            raise Exception(f"Ошибка при получении данных о погоде для {location}: {e}")
        except ValueError as e:
            raise Exception(f"Ошибка при обработке ответа API для {location}: {e}")
    return forecast

def get_coordinates(location):
    """
    Получение координат локации с использованием OpenStreetMap API.
    """
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={location}"
    try:
        response = requests.get(url, headers=HEADERS)  # Добавляем заголовок User-Agent
        response.raise_for_status()  # Проверяем статус ответа
        data = response.json()
        if not data:
            raise Exception(f"Координаты для локации {location} не найдены.")
        return float(data[0]['lat']), float(data[0]['lon'])
    except requests.RequestException as e:
        raise Exception(f"Ошибка при получении координат для {location}: {e}")
    except ValueError as e:
        raise Exception(f"Ошибка при обработке ответа API для {location}: {e}")

def format_city_name(city):
    """
    Форматирование названия города по правилам русского языка.
    """
    return city.strip().title()

def generate_graphhopper_route_url(coordinates):
    """
    Генерация ссылки на маршрут с использованием GraphHopper.
    """
    data = {
        "points": [[lon, lat] for lat, lon in coordinates],  
        "profile": "car",  
        "locale": "ru",  
        "instructions": True, 
        "calc_points": True,  
        "points_encoded": False 
    }

    url = f"https://graphhopper.com/api/1/route?key={GRAPHHOPPER_API_KEY}"

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        result = response.json()

        if "paths" in result and len(result["paths"]) > 0:
            map_url = result["paths"][0]["points_encoded"]
            return f"https://graphhopper.com/maps/?point={'&point='.join([f'{lat},{lon}' for lat, lon in coordinates])}&vehicle=car&locale=ru&points_encoded={map_url}"
        else:
            raise Exception("Маршрут не найден.")
    except requests.RequestException as e:
        raise Exception(f"Ошибка при получении маршрута: {e}")
