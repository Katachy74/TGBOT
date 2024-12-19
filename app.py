import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from weather_service import get_weather_forecast, get_coordinates, format_city_name, generate_graphhopper_route_url
import plotly.graph_objs as go
import plotly.io as pio
from config import BOT_TOKEN

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация Telegram-бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Состояния для машины состояний
class WeatherForm(StatesGroup):
    start_point = State()
    end_point = State()
    intermediate_points = State()
    days = State()

# Команда /start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    """
    Приветствие пользователя и описание возможностей бота.
    """
    await message.answer("Привет! Я бот для прогноза погоды по маршруту. "
                         "Используй команду /weather, чтобы узнать погоду для начальной, конечной и промежуточных точек маршрута.")

# Команда /help
@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    """
    Вывод справки по командам.
    """
    await message.answer("Доступные команды:\n"
                         "/start - Приветствие и описание бота\n"
                         "/help - Справка по командам\n"
                         "/weather - Получить прогноз погоду для маршрута")

# Команда /weather
@dp.message_handler(commands=['weather'])
async def cmd_weather(message: types.Message):
    """
    Начало процесса получения прогноза погоды.
    """
    await message.answer("Введите начальную точку маршрута:")
    await WeatherForm.start_point.set()

# Обработка начальной точки
@dp.message_handler(state=WeatherForm.start_point)
async def process_start_point(message: types.Message, state: FSMContext):
    """
    Обработка ввода начальной точки маршрута.
    """
    start_point = format_city_name(message.text)  # Форматируем город
    await state.update_data(start_point=start_point)
    await message.answer("Введите конечную точку маршрута:")
    await WeatherForm.next()

# Обработка конечной точки
@dp.message_handler(state=WeatherForm.end_point)
async def process_end_point(message: types.Message, state: FSMContext):
    """
    Обработка ввода конечной точки маршрута.
    """
    end_point = format_city_name(message.text)  # Форматируем город
    await state.update_data(end_point=end_point)
    await message.answer("Введите промежуточные точки маршрута (через запятую, если их несколько, или введите 'нет', если их нет):")
    await WeatherForm.next()

# Обработка промежуточных точек
@dp.message_handler(state=WeatherForm.intermediate_points)
async def process_intermediate_points(message: types.Message, state: FSMContext):
    """
    Обработка ввода промежуточных точек маршрута.
    """
    intermediate_points = message.text.strip().lower()
    if intermediate_points.lower() == "нет":  # Если пользователь ввел "нет"
        intermediate_points = []
    else:
        intermediate_points = [format_city_name(point.strip()) for point in intermediate_points.split(',') if point.strip()]
    await state.update_data(intermediate_points=intermediate_points)
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(InlineKeyboardButton("1 день", callback_data="1"),
                 InlineKeyboardButton("3 дня", callback_data="3"),
                 InlineKeyboardButton("5 дней", callback_data="5"))
    await message.answer("Выберите временной интервал прогноза:", reply_markup=keyboard)
    await WeatherForm.next()

# Обработка выбора временного интервала
@dp.callback_query_handler(lambda c: c.data.isdigit(), state=WeatherForm.days)
async def process_days(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обработка выбора временного интервала прогноза.
    """
    await state.update_data(days=int(callback_query.data))
    data = await state.get_data()
    start_point = data['start_point']
    end_point = data['end_point']
    intermediate_points = data['intermediate_points']
    days = data['days']

    # Формируем маршрут
    locations = [start_point, *intermediate_points, end_point]

    # Получаем прогноз погоды
    try:
        forecast = get_weather_forecast(locations, days)
        response = "Прогноз погоды для маршрута:\n"
        for location, data in forecast.items():
            response += f"🌍 {location}:\n"
            for day, info in data.items():
                response += f"📅 {day}:\n"
                response += f"🌡️ Температура: {info['temperature_min']}°C - {info['temperature_max']}°C\n"
                response += f"💧 Вероятность осадков: {info['precipitation_probability']}%\n"
                response += f"💨 Скорость ветра: {info['wind_speed']} м/с\n"

            # Создаем графики для текущей локации
            # График температуры
            fig_temp = go.Figure()
            fig_temp.add_trace(go.Scatter(
                x=[day for day in data.keys()],
                y=[info['temperature_max'] for info in data.values()],
                mode='lines+markers',
                name='Макс. температура'
            ))
            fig_temp.add_trace(go.Scatter(
                x=[day for day in data.keys()],
                y=[info['temperature_min'] for info in data.values()],
                mode='lines+markers',
                name='Мин. температура'
            ))
            fig_temp.update_layout(
                title=f"{location} - Температура",
                xaxis_title="Дни",
                yaxis_title="Температура (°C)",
                legend=dict(x=0.1, y=1.1),
                template="plotly_white"
            )

            # График вероятности осадков
            fig_precip = go.Figure()
            fig_precip.add_trace(go.Bar(
                x=[day for day in data.keys()],
                y=[info['precipitation_probability'] for info in data.values()],
                name='Вероятность осадков',
                marker_color='blue'
            ))
            fig_precip.update_layout(
                title=f"{location} - Вероятность осадков",
                xaxis_title="Дни",
                yaxis_title="Вероятность осадков (%)",
                template="plotly_white"
            )

            # График скорости ветра
            fig_wind = go.Figure()
            fig_wind.add_trace(go.Scatter(
                x=[day for day in data.keys()],
                y=[info['wind_speed'] for info in data.values()],
                mode='lines+markers',
                name='Скорость ветра',
                line=dict(color='green')
            ))
            fig_wind.update_layout(
                title=f"{location} - Скорость ветра",
                xaxis_title="Дни",
                yaxis_title="Скорость ветра (м/с)",
                template="plotly_white"
            )

            # Сохраняем графики в файлы
            temp_path = f"{location}_temperature.png"
            precip_path = f"{location}_precipitation.png"
            wind_path = f"{location}_wind.png"
            pio.write_image(fig_temp, temp_path)
            pio.write_image(fig_precip, precip_path)
            pio.write_image(fig_wind, wind_path)

            # Отправляем графики пользователю
            with open(temp_path, 'rb') as photo:
                await bot.send_photo(callback_query.message.chat.id, photo)
            with open(precip_path, 'rb') as photo:
                await bot.send_photo(callback_query.message.chat.id, photo)
            with open(wind_path, 'rb') as photo:
                await bot.send_photo(callback_query.message.chat.id, photo)

            # Удаляем временные файлы
            os.remove(temp_path)
            os.remove(precip_path)
            os.remove(wind_path)

        # Генерируем ссылку на маршрут с помощью GraphHopper
        try:
            coordinates = [get_coordinates(location) for location in locations]
            if all(coordinates):
                # Генерируем ссылку на маршрут
                route_url = generate_graphhopper_route_url(coordinates)
                await bot.send_message(callback_query.message.chat.id, f"Ссылка на маршрут: {route_url}")
            else:
                await bot.send_message(callback_query.message.chat.id, "Не удалось получить координаты для отображения маршрута.")
        except Exception as e:
            await bot.send_message(callback_query.message.chat.id, f"Ошибка при создании ссылки на маршрут: {e}")

        await bot.send_message(callback_query.message.chat.id, response)
    except Exception as e:
        await bot.send_message(callback_query.message.chat.id, f"Ошибка при получении прогноза: {e}")

    await state.finish()

# Запуск Telegram-бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)