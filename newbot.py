import telebot
from telebot import types
import pandas as pd
import math
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = telebot.TeleBot('***')
df = pd.read_csv('Final_joined.csv')

def haversine(lat1, lon1, lat2, lon2):
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = 6371.01 * c  # Earth's radius in kilometers
    return distance

def calc_distances(current_lat, current_lon, places_df, lat_column, lon_column, name_column):
    nearest_place = None
    places_df['distance'] = None
    for index, row in places_df.iterrows():
        place_name = row[name_column]
        place_lat = row[lat_column]
        place_lon = row[lon_column]
        distance = haversine(current_lat, current_lon, place_lat, place_lon)
        places_df.loc[index, 'distance'] = distance
    return places_df

users = {}


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id

    # Отправляем инструкцию по использованию бота
    instructions = "Давайте начнем!\nИнструкция по использованию бота.\n\n" \
                   "1. Команда для начала поиска - /poisk\n" \
                   "2. Отправьте мне ваше местоположение, чтобы я мог найти ближайшие заправки.\n" \
                   "3. Выберите ваш регион.\n" \
                   "4. Выберите вид топлива.\n" \
                   "5. Я покажу вам ближайшие заправки и их геопозиции.\n"
    bot.send_message(user_id, instructions)
    logger.info(f'User {user_id} started interaction with the bot')


@bot.message_handler(commands=['guide'])
def guide(message):
    user_id = message.chat.id

    # Отправляем инструкцию по использованию бота
    instructions = "Как пользоваться ботом?\n\n" \
                   "1. Команда для начала поиска - /poisk\n" \
                   "2. Отправьте мне ваше местоположение, чтобы я мог найти ближайшие заправки.\n" \
                   "3. Выберите ваш регион.\n" \
                   "4. Выберите вид топлива.\n" \
                   "5. Я покажу вам ближайшие заправки и их геопозиции.\n"
    bot.send_message(user_id, instructions)
    logger.info(f'User {user_id} started interaction with the bot')


@bot.message_handler(commands=['poisk'])
def poisk(message):
    user_id = message.chat.id
    if user_id not in users:
        users[user_id] = {
            'lat': None,
            'long': None,
            'region': None,
            'fuel': None,
            'fuel_type': None,
            'zapravka': None,
            'page': 0
        }
        logger.info(f'New user registered with user_id={user_id}')

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    location_button = types.KeyboardButton("Отправить местоположение", request_location=True)
    markup.add(location_button)

    bot.send_message(user_id, "Чтобы найти ближайшие заправки, нажмите кнопку ниже:", reply_markup=markup)
    logger.info(f'User {user_id} started interaction with the bot')

@bot.callback_query_handler(func=lambda call: call.data == "send_location")
def send_location(call):
    user_id = call.message.chat.id
    bot.send_message(user_id, "Отправьте ваше местоположение, чтобы найти ближайшие заправки.",
                     reply_markup=types.ReplyKeyboardRemove(selective=True))
    bot.send_location(user_id, latitude=0.0, longitude=0.0)  # Это пример координат



@bot.message_handler(content_types=['location'])
def handle_location(message):
    user_id = message.chat.id
    users[user_id]['lat'] = message.location.latitude
    users[user_id]['long'] = message.location.longitude
    region_buttons = [
        telebot.types.InlineKeyboardButton(title, callback_data=title)
        for title in df['REGION'].unique()
    ]
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(*region_buttons)
    bot.send_message(user_id, 'Выберите ваш регион:', reply_markup=markup)
    logger.info(f'User {user_id} sent their location')


@bot.callback_query_handler(func=lambda call: call.data in df['NEFTEPRODUKT_VID'].unique())
def choose_fuel_type(call):
    user_id = call.message.chat.id
    users[user_id]['fuel_type'] = call.data
    df_filter = df[
        (df['NEFTEPRODUKT_NAME'] == users[user_id]['fuel']) &
        (df['NEFTEPRODUKT_VID'] == users[user_id]['fuel_type']) &
        (df['REGION'] == users[user_id]['region']) &
        (df['PROC'] > 0.30)
    ]
    new_df = calc_distances(users[user_id]['lat'], users[user_id]['long'], df_filter, 'Latitude', 'Longitude', 'AZS')
    new_df = new_df[['AZS', 'Address', 'Latitude', 'Longitude', 'distance']].sort_values('distance', ascending=True)
    users[user_id]['zapravka'] = new_df.to_dict('records')
    users[user_id]['page'] = 0

    send_next_page(user_id)

def send_next_page(user_id):
    start_idx = users[user_id]['page'] * 5
    end_idx = start_idx + 5
    zapravki = users[user_id]['zapravka'][start_idx:end_idx]

    output = f"Ваш выбор: {users[user_id]['fuel_type']} {users[user_id]['fuel']}\n\nБлижайшие заправки:\n"

    for x in zapravki:
        output += f"{x['AZS']}\n{x['Address']}\nДистанция в км: {round(x['distance'], 1)}\n\n"

    markup = telebot.types.InlineKeyboardMarkup()
    if end_idx < len(users[user_id]['zapravka']):
        markup.add(telebot.types.InlineKeyboardButton(text="Показать следующие 5 заправок", callback_data="next_page"))

    for x in zapravki:
        bot.send_venue(user_id, x['Latitude'], x['Longitude'], x['AZS'], x['Address'])

    bot.send_message(user_id, output, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "next_page")
def show_next_page(call):
    user_id = call.message.chat.id
    users[user_id]['page'] += 1
    send_next_page(user_id)





@bot.callback_query_handler(func=lambda call: call.data in df[df['REGION'] == users[call.message.chat.id]['region']]['NEFTEPRODUKT_NAME'].unique())
def choose_fuel(call):
    user_id = call.message.chat.id  # Получаем user_id из call.message
    users[user_id]['fuel'] = call.data
    fuel_buttons = [
        telebot.types.InlineKeyboardButton(title, callback_data=title)
        for title in df[(df['REGION'] == users[user_id]['region']) & (df['NEFTEPRODUKT_NAME'] == users[user_id]['fuel'])]['NEFTEPRODUKT_VID'].unique()
    ]
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(*fuel_buttons)
    bot.edit_message_text('Выберите вид топлива: \n 📛 Продажа топлива регулируется АЗС!', user_id, call.message.message_id, reply_markup=markup)
    logger.info(f'User {user_id} chose fuel: {call.data}')

@bot.callback_query_handler(func=lambda call: call.data in df['REGION'].unique())
def choose_region(call):
    user_id = call.message.chat.id
    users[user_id]['region'] = call.data
    fuel_buttons = [
        telebot.types.InlineKeyboardButton(title, callback_data=title)
        for title in df[df['REGION'] == users[user_id]['region']]['NEFTEPRODUKT_NAME'].unique()
    ]
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(*fuel_buttons)
    bot.edit_message_text('Выберите вид топлива: \n 📛 Продажа топлива регулируется АЗС!', user_id, call.message.message_id, reply_markup=markup)
    logger.info(f'User {user_id} chose region: {call.data}')

bot.polling()
