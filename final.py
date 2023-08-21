import pandas as pd
import math
from telethon import TelegramClient, events, types, custom



### ---- PANDAS ---- ###
### ---- IMPORT OF TEST DATA ---- ###
df = pd.read_csv('Final_joined.csv')
df.info()
print(df.head(5))


### ---- FUNCTIONS ---- ###

### ---- DISTANCE FORMULA ---- ###
### Calculates distance between 2 locations ###
### In this work, it calculates distance between user's geolocation and petrol stations and shows it in KM ###
def haversine(lat1, lon1, lat2, lon2): 
    # Convert degrees to radians 
    lat1 = math.radians(lat1) 
    lon1 = math.radians(lon1)
    
    lat2 = math.radians(lat2) 
    lon2 = math.radians(lon2) 
     
    # Haversine formula 
    dlat = lat2 - lat1 
    dlon = lon2 - lon1 
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2 
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)) 
    distance = 6371.01 * c  # Earth's radius in kilometers 
     
    return distance 

### ---- CALC DISTANCES FUNCTION ---- ###
### ---- INPUTS FROM DATAFRAME: ---- ###
### current_lat = latitude of the user ###
### current_lon = longitude of the user ###
### places_df = main dataframe/dataset ###
### lat_column = name of the column in dataset that has Latitude coordinates ###
### lon_column = name of the column in dataset that has Longitude coordinates ###
### name_column = name of the column in dataset that has names of the petrol stations ###

### Given function:
### 1. Takes all the inputs from the dataset.
### 2. Calculates distance between user's geolocation and petrol stations using distance formula (haversine function).
### 3. Creates a column 'distance' in dataframe with distance written  for each petrol station and returns the dataframe. 
def calc_distances(current_lat, current_lon, places_df, lat_column, lon_column, name_column):
    print(current_lat, current_lon)
    nearest_place = None 
    places_df['distance'] = None 
     
    for index, row in places_df.iterrows(): 
        place_name = row[name_column] 
        place_lat = row[lat_column] 
        place_lon = row[lon_column] 
        distance = haversine(current_lat, current_lon, place_lat, place_lon) 
        places_df.loc[index, 'distance'] = distance

    return places_df

### ---- TELEGRAM ---- ###
### Variables needed to creates pages when user is choosing specific organization ###
organization_options = []
current_page = 0

### A function that creates a new user id after bot is started with /start function ###
### It also collects all the data chosen by user throughout the interaction with bot ### 
users = {}
def usercheck(id):
    global users
    if id not in users.keys():
        print(f'[+] Creating new user with id={id}')
        users[id] = {
            'lat': None,
            'long': None,
            'region': None,
            'fuel': None,
            'fuel_type': None,
            'zapravka': None, 
            'page': 0
        }
    else:
        print(f'[+] User already exists with id={id}')

        
print('Connecting...')
# Variable that connects to bot using key, id and bot_token taken from BotFather in Telegram.
bot = TelegramClient('bot', 21867668, '66078d4b52bd2aea2de3f5b5fef75541').start(bot_token='6624798337:AAEIohfbbyWahhZcER3bZTuy3RfjQxqlP8s')
#print('Disconnecting...')

### Bot function that makes bot answer to /start command and creates a button that takes geolocation of the user
@bot.on(events.NewMessage(pattern='/start'))
async def handler(event):
    user_id = event.sender_id
    print(f'[+] Command start for user_id={user_id}')
    usercheck(user_id)
    location_button = [[custom.Button.request_location("Отправить позицию")]]
    
    await event.respond('Добро пожаловать', buttons=location_button)

### Bot function that saves the coordinates sent by the user in users dictionary by user_id ###
### It then asks to choose region (Astana or Almaty) by taking data from the dataframe and creating a button "Выберите ваш регион:" ###
@bot.on(events.NewMessage(func=lambda e: e.message.media and isinstance(e.message.media, types.MessageMediaGeo)))
async def handler(event):
    user_id = event.sender_id
    
    print(f'[+] Sending geoposition for user_id={user_id}')
    global users
    usercheck(user_id)
    users[user_id]['lat'] = float(event.message.media.geo.lat)
    users[user_id]['long'] = float(event.message.media.geo.long)
    
    region_buttons = [[custom.Button.inline(title, data=title)]
    for title in df['REGION'].unique()]
    
    await event.respond('Выберите ваш регион:',
        buttons=region_buttons)

### Bot function that saves the region chosen in users dictionary and creates another button that asks user to choose a specific fuel ###
    ### Fuel options are also filtered and based on the region chosen by the user ###
    ### For example, if user chooses Astana, fuel unique to Almaty is not going to pop-up in choose options ###
    ## After user made a choice, bot returns user a choice he made and saves chosen variable to the users list ### 
@bot.on(events.CallbackQuery)
async def handler(event):
    user_id = event.sender_id
    print(f'[+] Sending region for user_id={user_id}')
    global users, df
    usercheck(user_id)
    choice = event.data.decode('utf-8')
    msg_id = event.original_update.msg_id
    fuel_buttons = [[custom.Button.inline(title, data=title)] for title in df[df['REGION'] == choice]['NEFTEPRODUKT_NAME'].unique()
            ]

    if choice in df['REGION'].unique():
        users[event.query.user_id]['region'] = choice
        await bot.edit_message(event.query.peer, msg_id, 'Выбрано: ' + choice + '\nКакое топливо?',
            buttons=fuel_buttons
        )
    elif choice in df['NEFTEPRODUKT_NAME'].unique():
        users[event.query.user_id]['fuel'] = choice

### Function of the bot that asks user to choose organization and then writes the choice to users dictionary. ###
        ### This function creates pages with 5 organization names shown per page ###
@bot.on(events.CallbackQuery)
async def handler(event):
    user_id = event.sender_id
    global users, organization_options, df, current_page
    user_data = users[user_id]
    user_data['page'] = current_page
    usercheck(event.query.user_id)
    choice = event.data.decode('utf-8')
    msg_id = event.original_update.msg_id
    
    ### Variable that determines how many organization names can be shown in one page ### 
    organizations_per_page = 5

    if choice in df['NEFTEPRODUKT_NAME'].unique():
        users[event.query.user_id]['fuel'] = choice
    
        if not len(organization_options):
            print('[+] Initializing list of organizations')
            # Provide options to choose an organization based on the selected region
            organization_options = df[df['NEFTEPRODUKT_NAME'] == choice]['ORGANIZATION'].unique()
        else:
            print('[+] Organizations list if filled')
        
        ### Divides organization names into pages (e.g., 5 organizations per page) ###
            ### This function also should give option to user to choose any nearest organization, but it doesn't work ### 
        num_pages = math.ceil(len(organization_options) / organizations_per_page)
        buttons = [
            [custom.Button.inline(title, data=f'org_{current_page}_{title}')] 
            for title in organization_options[current_page * organizations_per_page:(current_page + 1) * organizations_per_page]
        ]
        buttons.append([custom.Button.inline("Выбрать любую организацию", data="any_organization")])
        
        
        await bot.edit_message(event.query.peer, msg_id, 'Выбрано: ' + choice + '\nВыберите организацию:',
            buttons=buttons + [[custom.Button.inline('>>', data='next_page')]]
        )
    ### If user chooses specific organization name, this function saves the name in users data as org_name variable ###
        ### Then bot asks to choose specific fuel type (A92, A95, Prime 95, etc) and options that are available are filtered and based on
        ### organization and fuel chosen ### 
    elif choice.startswith('org_'):
        _, page_num, org_name = choice.split('_')
        users[event.query.user_id]['organization'] = org_name
        await bot.edit_message(event.query.peer, msg_id, 'Выбрано: ' + org_name + '\nКакое топливо?',
            buttons=[
                [custom.Button.inline(title, data=title)] for title in df[(df['ORGANIZATION'] == org_name) & (df['NEFTEPRODUKT_NAME'] == users[user_id]['fuel'])]['NEFTEPRODUKT_VID'].unique()
                
            ]
        )
    ### Here function should continue the option if user chooses any nearest organization. It should then give option to choose
        ### fuel type based on region and fuel, but it doesn't work ### 
    elif choice == 'any_organization':
        users[event.query.user_id]['organization'] = "Выбрать любую организацию"
        region = users[event.query.user_id]['region']
        fuel = users[event.query.user_id]['fuel']
        fuel_types = df[(df['REGION'] == region) & (df['NEFTEPRODUKT_NAME'] == fuel)]['NEFTEPRODUKT_VID'].unique()
    
    # Create inline buttons for each fuel type
        fuel_buttons = [
        [custom.Button.inline(fuel_type, data=fuel_type)] for fuel_type in fuel_types
    ]
    
        await bot.edit_message(
        event.query.peer, 
        msg_id, 
        'Выбрано: Выбрать любую организацию\nКакой вид топлива?',
        buttons=fuel_buttons
    )
    
    ### Given function maintains the feature that allows user to go to next page when choosing an organization ###
    elif choice == 'next_page':
        # Show the next page of organization options
        current_page += 1
        buttons = [
            [custom.Button.inline(title, data=f'org_{current_page}_{title}')] 
            for title in organization_options[current_page * organizations_per_page:(current_page + 1) * organizations_per_page]
        ]
        
        await bot.edit_message(event.query.peer, msg_id, 'Выберите организацию:',
            buttons=buttons + [[custom.Button.inline('<<', data='prev_page'), custom.Button.inline('>>', data='next_page')]]
        )
    
    ### Given function maintains the feature that allows user to go to previous page when choosing an organization ###
    elif choice == 'prev_page':
        # Show the previous page of organization options
        if current_page > 0:
            current_page -= 1
            buttons = [
                [custom.Button.inline(title, data=f'org_{current_page}_{title}')] 
                for title in organization_options[current_page * organizations_per_page:(current_page + 1) * organizations_per_page]
            ]
            
            await bot.edit_message(event.query.peer, msg_id, 'Выберите организацию:',
                buttons=buttons + [[custom.Button.inline('<<', data='prev_page'), custom.Button.inline('>>', data='next_page')]]
            )
    
    ### Function writes user choice of fuel type to users dictionary ### 
    elif choice in df['NEFTEPRODUKT_VID'].unique():
        users[event.query.user_id]['fuel_type'] = choice
        
        ### Function filters main dataframe by the choices that were made by the user ### 
        df_filter = df[(df['NEFTEPRODUKT_NAME'] == users[event.query.user_id]['fuel']) & (df['NEFTEPRODUKT_VID'] == users[event.query.user_id]['fuel_type']) & (df['REGION'] == users[event.query.user_id]['region'])  & (df['ORGANIZATION'] == users[event.query.user_id]['organization']) & (df['PROC']>0.30)]
        ### New df variable is created using calc_distances function. Dataframe has all petrol stations relevant to the choices made by the user
        ### and new column distance is also created in the dataframe ###
        new_df = calc_distances(users[event.query.user_id]['lat'], users[event.query.user_id]['long'], df_filter, 'Latitude', 'Longitude', 'AZS')
        
        ### New dataframe is sorted by distance in ascending order ###
        new_df = new_df[['AZS', 'Address', 'Latitude', 'Longitude', 'distance']].sort_values('distance', ascending=True)
        new_df.head()
        
        ### New dataframe is converted to top_org dictionary and top_org dictionary is filtered on top 3 rows ###
        top_org = new_df.to_dict('records')
        top_org = top_org[:3]
        print(top_org)
        users[event.query.user_id]['zapravka'] = top_org
        
        
        ### Output produces names, addresses and geolocations of top 3 nearest petrol stations to the user ### 
        output = 'Ваш выбор: %s %s \n\nБлижайшие заправки: %s \n\n' % (users[event.query.user_id]['fuel_type'], users[event.query.user_id]['fuel'], '\n\n'.join([x['AZS'] + '\n' + x['Address'] + '\n' + 'Дистанция в км: ' + str(round(x['distance'], 1)) for x in top_org]))

        if len(top_org) > 0:
            for i in range(len(top_org)):
                await bot.send_file(event.query.peer, types.InputMediaGeoPoint(types.InputGeoPoint(float(top_org[i]['Latitude']), float(top_org[i]['Longitude']))), reply_to=msg_id)

        await bot.edit_message(event.query.peer, msg_id, output)
          

with bot:
    bot.run_until_disconnected()
