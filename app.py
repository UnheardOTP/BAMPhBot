import os
import discord
from datetime import datetime, timedelta, date, time
from discord.ext import commands, tasks
import mysql.connector
import pandas as pd
from sqlalchemy import create_engine
import requests
import json
from openai import OpenAI
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from database import database
import functions
import traceback
import inspect
import sys
import asyncio


#region Secrets
with open('secrets.txt', 'r') as f:
    data = f.read()
    f.close()

secrets = json.loads(data)

db_host=secrets['HOST']
db_user=secrets['USER']
db_password=secrets['PASSWORD']
db_database=secrets['DATABASE']
#endregion Secrets

# Create multi use db object
db = database(db_host, db_user, db_password, db_database)

#region Bot Definitions

intents = discord.Intents.all()
intents.typing = True
intents.messages = True
intents.message_content = True
intents.members = True
bot = discord.Bot(intents=intents)

#endregion Bot Definitions

# Error logging
async def error_log(err):
    # Extract traceback info
    tb = err.__traceback__
    tb_str = "".join(traceback.format_exception(type(err), err, tb))

    # Extract function name and line number
    frame = traceback.extract_tb(tb)[-1]  # last frame = where it actually failed
    function_name = frame.name
    line_number = frame.lineno

    # Insert into DB
    db.query(
        """
        INSERT INTO bot_error_log 
        (datetime, error_message, error_type, traceback, function_name, line_number)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            datetime.now(),
            str(err),
            type(err).__name__,
            tb_str,
            function_name,
            line_number
        )
    )
    db.commit()

    channel = bot.get_channel(1245331722342629376)
    if channel:
      await channel.send(f"⚠️ **BAMPhBot Error** - Logged @ {datetime.now()}")


#region Secrets

with open('secrets.txt', 'r') as f:
    data = f.read()
    f.close()

secrets = json.loads(data)

db_host=secrets['HOST']
db_user=secrets['USER']
db_password=secrets['PASSWORD']
db_database=secrets['DATABASE']
token=secrets['TOKEN']
wx_apikey=secrets['WX_APIKEY']
wx_appkey=secrets['WX_APPKEY']
openai_apikey=secrets['OPENAI_APIKEY']

#endregion Secrets


#region Functions

# Locker inventory functions
def add_bottle(db, bottle_name, liquor_type):
  try:
    db.query("insert into locker_inventory (bottle_name, liquor_type) values (%s, %s)", (bottle_name, liquor_type))
    db.commit()

    return True
  except Exception as err:
    asyncio.create_task(error_log(err))


def rem_bottle(db, bottle_id):
  try:
    db.query("delete from locker_inventory where id = %s", (bottle_id,))
    db.commit()

    return True
  except Exception as err:
    asyncio.create_task(error_log(err))


def mark_bottle_low(db, bottle_id):
  try:
    db.query("update locker_inventory set is_low = 1 where id = %s", (bottle_id,))
    db.commit()
    
    return True
  except Exception as err:
    asyncio.create_task(error_log(err))


def get_locker_inventory(db):
  try:
    return db.query("select * from locker_inventory")
  except Exception as err:
    asyncio.create_task(error_log(err))


def get_course_status():
  url = 'https://www.bradshawfarmgc.com/'
  ua = UserAgent()
  headers = {'User-Agent': ua.random}
  response = requests.get(url, headers=headers)
  response.raise_for_status()

  soup = BeautifulSoup(response.text, 'html.parser')

  returned_status = soup.find('div', class_='eb-content').find_all('span')
  course_status = returned_status[0].text.strip()

  return course_status

# Discipline Points
def add_discipline_point(db, user, points, reason):
  try:
    db.query("insert into discipline_points (user, point_amount, reason) values (%s, %s, %s)", (user, points, reason))
    db.commit()

    return True
  except Exception as err:
    asyncio.create_task(error_log(err))


# Good Citizen Points
def add_good_citizen_point(db, user, points, reason): 
  try:
    db.query("insert into good_citizen_points (user, point_amount, reason) values (%s, %s, %s)", (user, points, reason))
    db.commit()

    return True
  except Exception as err:
    asyncio.create_task(error_log(err))


def get_discipline_point_desc(db, user):
  try:
    result = db.query("select point_amount, reason from discipline_points where user = %s", (user,))

    if not result:
      return f"User {user} has no points currently. Pehaps they don't belong in BAMPh?"
    else:
      return result
  except Exception as err:
    asyncio.create_task(error_log(err))

      
  
def get_discipline_point(db, user):   
  try:
    result = db.query("select sum(point_amount) as point_sum from discipline_points where user = %s", (user,))

    if result:
      point_total = result[0]["point_sum"]
      return int(point_total) if point_total is not None else 0
    else:
      return 0
  except Exception as err:
    asyncio.create_task(error_log(err))

  
# Beer credits
def give_beer_insert(db, giver, receiver, reason):
  try:
    db.query("insert into beer_credits (giver, receiver, reason) values (%s, %s, %s)", (f"<@{giver}>", receiver, reason))
    db.commit()

    return True
  except Exception as err:
    asyncio.create_task(error_log(err))


# Get current AI training prompt
def get_ai_prompt(db):
  try:
    result = db.query("select prompt from ai_prompt")

    if result:
      return str(result[0]["prompt"]) if result[0]["prompt"] is not None else ""
    else:
      return ""
  except Exception as err:
    asyncio.create_task(error_log(err))


# Update AI Prompt
def update_ai_prompt(db, prompt):
  db.query("update ai_prompt set prompt = %s", (prompt, ))
  db.commit()
  
  return True

# Used quote reset (when all quotes have been used)
def reset_quotes(db):
  try:
    db.query("update quotes set quote_used = 0")
    db.commit()

    return True
  except Exception as err:
    asyncio.create_task(error_log(err))
 

# Used photo reset (when all photos have been used)
def reset_photos(db):
  try:
    db.query("update photos set used = 0")
    db.commit()

    return True
  except Exception as err:
    asyncio.create_task(error_log(err))

    
# Get last run time for photo or quote
def last_run_time(db, type):    
  try:
    result = db.query("select last_run from last_runs where type = %s", (type,))
    if not result:
      return None

    last_run = result[0]["last_run"]
    return last_run.isoformat() if hasattr(last_run, "isoformat") else str(last_run)

  except Exception as err:
    asyncio.create_task(error_log(err))

    return None

# Update last run time for photo or quote
def update_last_run(db, type, last_run):
  try:
    db.query("update last_runs set last_run = %s where type = %s", (last_run, type))
    db.commit()

    return True
  except Exception as err:
    asyncio.create_task(error_log(err))


# Add quote
def add_quote_to_db(db, quote, author):
  try:
    db.query("insert into quotes (quote, author) values (%s, %s)", (quote, author))
    db.commit()

    return True
  except Exception as err:
     asyncio.create_task(error_log(err))

   
# Last available quote check
def last_quote_check(db):
  try:
    result = db.query("select count(*) as count from quotes where quote_used = 0")

    if not result:
      return False

    quote_count = result[0]["count"]
 
    return quote_count == 1

  except Exception as err:
    asyncio.create_task(error_log(err))

    return False

# Last available quote check
def last_photo_check(db):
  try:
    result = db.query("select count(*) as count from photos where used = 0")

    if not result:
      return False

    photo_count = result[0]["count"]
 
    return photo_count == 1

  except Exception as err:
    asyncio.create_task(error_log(err))


def add_photo(db, image_url):
  try:
    api_url = "https://catbox.moe/user/api.php"
    data = {
            'reqtype': 'urlupload',
            'userhash': '',
            'url': f'{image_url}'
        }

    response = requests.post(api_url, data=data)

    if not response.ok or not response.text.startswith("https://"):
      return Exception(f"Catbox upload failed: {response.text}")


    db.query("insert into photos (photo_link) values (%s)", (response.text,))
    db.commit()

    return True
  except Exception as err:
    asyncio.create_task(error_log(err))


# Get random quote
def get_quote(db):
  try:
    result = db.query("select id, quote, author, created_date from quotes where quote_used = 0 ORDER BY RAND() LIMIT 1;")

    # Get random quote
    if not result:
      return "No quote found."

# If this is the last available quote, reset used quotes
    if last_quote_check(db):
        reset_quotes(db)      

    quote_id = result[0]["id"]
    quote_text = result[0]["quote"]
    author = result[0]["author"]
    created_date = result[0]["created_date"]

    if created_date == date(1900, 1, 1):
        created_date = 'Date Unknown'

    # Build return string
    rand_quote = f"{quote_text} - {author} - {created_date}"

    # Update random quote as used
    db.query("update quotes set quote_used = 1 where id = %s", (quote_id,))
    db.commit()

    return rand_quote
  except Exception as err:
    asyncio.create_task(error_log(err))


# Get random photo
def get_photo(db):
  try:  
    result = db.query("select id, photo_link from photos where used = 0 ORDER BY RAND() LIMIT 1;")

    if not result:
      return "No photo found."

    # If this is the last available photo, reset used photo
    if last_photo_check(db):
        reset_photos(db)
    
    photo_id = result[0]["id"]
    photo_link = result[0]["photo_link"]

    # Update random photo as used
    db.query("update photos set used = 1 where id = %s", (photo_id,))
    db.commit()

    return photo_link
  except Exception as err:
    asyncio.create_task(error_log(err))


  
def birthday_check(db):
  try:
    birthday = db.query("select * from birthdays where month = MONTH(curdate()) and day = DAY(curdate())")

    if birthday:
      return f"Happy birthday {birthday[0]['user']}!"
  
  except Exception as e:
    print("Error: ", e)

# API call to my backyard WX station
def get_chuggys_temp():
  try:
    url     = f'https://api.ambientweather.net/v1/devices?apiKey={wx_apikey}&applicationKey={wx_appkey}'

    response = requests.get(url)

    if not response.ok:
      return Exception(f"AmbientWeather API error: {response.status_code}")
    
    data = response.json()
    temp = data[0]['lastData']['tempf']

    if temp is None:
      return Exception("Temperature data not found in API response")

    return temp
  except Exception as err:
    asyncio.create_task(error_log(err))


def chat_with_bot(question):
    # Check to see where we are in the conversation. Conversations are limited to 4 items.

    client = OpenAI(
        api_key=openai_apikey,
    )

    chat_completion = client.chat.completions.create(
        messages=question,
        model="gpt-3.5-turbo-0125",
    )

    globals()['messages'].append({"role": "assistant", "content":chat_completion.choices[0].message.content})

    return chat_completion

# Discipline point rankings
def dp_point_rankings(db):
  try:
    result = db.query("select user, sum(point_amount) as total_points from discipline_points WHERE USER <> '@everyone' and user <> '<@1092634707541360762>' GROUP BY USER ORDER BY total_points DESC LIMIT 10")

    return list(result) if result else []
  except Exception as err:
    asyncio.create_task(error_log(err))

   

#endregion functions


#region Cron Jobs

# Check daily at 10am for bamph birthday
@tasks.loop(hours=24)
async def bday_check():
  channel = bot.get_channel(1092446896158679131)
  
  bday = birthday_check(db)

  if bday:
    await channel.send(f"{bday}")

# Send a random quote every 24 hours
@tasks.loop(hours=24)
async def rand_quote():
    channel = bot.get_channel(1092446896158679131)
    if datetime.now() - timedelta(hours=23.9) > datetime.fromisoformat(last_run_time(db, 'quote')):
      print(f'Quote Run {datetime.now()}')
      await channel.send(get_quote(db))
      update_last_run(db, 'quote', datetime.now().isoformat())

# Send a random quote every 6 hours
@tasks.loop(hours=28)
async def rand_photo():
    channel = bot.get_channel(1092446896158679131)
    if datetime.now() - timedelta(hours=27.9) > datetime.fromisoformat(last_run_time(db, 'photo')):
      print(f'Photo Run {datetime.now()}')
      await channel.send(get_photo(db))
      update_last_run(db, 'photo', datetime.now().isoformat())

@tasks.loop(minutes=15)
async def course_status_cron():
    channel = bot.get_channel(1145531746901819493) # #golf channel
    
    course_status = get_course_status()
    if course_status != functions.last_course_status(db):
      functions.set_course_status(db, course_status)
      await channel.send(f"Bradshaw Course/Range Status Update: {course_status}")
  

# Start cron jobs
@bot.event
async def on_ready():
  if not bday_check.is_running():
    bday_check.start()
  if not rand_quote.is_running():
    rand_quote.start()
  if not rand_photo.is_running():
    rand_photo.start() 
  if not course_status_cron.is_running():
    course_status_cron.start()

  channel = bot.get_channel(1245331722342629376)
  if channel:
    print(f"BAMPhBot Online @ {datetime.now()}.")
    await channel.send(f"BAMPhBot Online @ {datetime.now()}.")
 

#endregion Cron Jobs

#region context commands
@bot.message_command(name="Discipline Point")
async def discipline_point(ctx, message: discord.Message):
  add_discipline_point(db, message.author.id, '1', message.content)
  await ctx.respond(f"<@{message.author.id}> was given 1 discipline point for this message.")

@bot.message_command(name="Good Citizen Point")
async def good_citizen_point(ctx, message: discord.Message):
  add_good_citizen_point(db, message.author.id, '1', message.content)
  await ctx.respond(f"<@{message.author.id}> was given 1 good citizen point for this message.")

#1455447745958776905
@bot.message_command(name="Banish to #tards")
async def tard(ctx, message: discord.message):
  user = message.author
  role = discord.utils.get(user.guild.roles, name="tard")
  await user.add_roles(role)
  await ctx.respond(f"<@{message.author.id}> was banished to <#1455447383524642900> for this message.")

@bot.user_command(name="Unbanish from #tard")
async def tard(ctx, user: discord.Member):
  role = discord.utils.get(user.guild.roles, name="tard")
  await user.remove_roles(role)
  await ctx.respond(f"<@{user.id}> has been unbanished from <#1455447383524642900>.")

#endregion context commands
  
#region Slash Commands

@bot.slash_command(name="meg",
                  description="Meg",
                  guild_ids=[692123814989004862])
async def meg(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 

  await ctx.respond(f"https://files.catbox.moe/p8gggz.gif")


# Beer bitch functionality
# /bb_iou
'''
@bot.slash_command(name="bb_iou",
                description="Record a missed Beer Bitch $1 payment",
                guild_ids=[692123814989004862])
async def bb_iou(ctx, debtor):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 
  
  result = add_quote_to_db(debtor)

  beer_bitch = get_beer_bitch(db)
  
  if result == "Success":
    await ctx.respond(f"{debtor} owes $1 to {beer_bitch}. {beer_bitch} please use <thumb emoji> in response to this message to confirm payment.")
  else:
    ctx.respond(result)
'''

# /bb_paid



# Locker Inventory
# /locker_inventory
@bot.slash_command(name="locker_inventory",
                description="Get a Cigar Bar locker inventory.",
                guild_ids=[692123814989004862])
async def quote(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel    

  await ctx.respond(get_locker_inventory(db))

# /add_bottle 
@bot.slash_command(name="add_bottle",
                description="Add a bottle to the Cigar Bar locker inventory.",
                guild_ids=[692123814989004862])
async def quote(ctx, bottle_name, liquor_type):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel    

  add_bottle(db, bottle_name, liquor_type)

  await ctx.respond(f'{bottle_name} added to locker inventory.')

# /remove_bottle
@bot.slash_command(name="remove_bottle",
                description="Remove a bottle from the Cigar Bar locker inventory.",
                guild_ids=[692123814989004862])
async def quote(ctx, bottle_id):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel    

  rem_bottle(db, bottle_id)

  await ctx.respond(f'Bottle #{bottle_id} removed locker inventory.')

# /mark_bottle_low
@bot.slash_command(name="mark_bottle_low",
                description="Mark bottle low volume.",
                guild_ids=[692123814989004862])
async def quote(ctx, bottle_id):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel    

  mark_bottle_low(db, bottle_id)

  await ctx.respond(f'Bottle #{bottle_id} has been marked low. Please resupply.')

# /quote
@bot.slash_command(name="quote",
                  description="Get a random BAMPh quote.",
                  guild_ids=[692123814989004862])
async def quote(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel    

  await ctx.respond(get_quote(db))

# /reset_bot_conversation
@bot.slash_command(name="reset_bot_conversation",
                   description="Wipes bots AI conversation memory for a fresh start.",
                   guild_ids=[692123814989004862],
                  role_ids=[1092591212202045552])
async def reset_bot_conversation(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel
  
  globals()['messages'] = ""

  await ctx.respond("My memory has been wiped and I am ready to start anew!")

# /add_quote
@bot.slash_command(name="add_quote",
                  description="Add BAMPh quote.",
                  guild_ids=[692123814989004862])
async def add_quote(ctx, quote, author):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 

  result = add_quote_to_db(db, quote, author)
  
  if result == "Success":
    await ctx.respond(f"{quote} - {author} - Added")
  else:
    ctx.respond(result)

# /set_ai_prompt
@bot.slash_command(name="set_ai_prompt",
                  description="Set the style of AI response.",
                  guild_ids=[692123814989004862],
                  role_ids=[1092591212202045552])
async def add_quote(ctx, prompt):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 

  update_ai_prompt(db, prompt)
  # Reset prompt and memory
  globals()['messages'] = []

  await ctx.respond(f"AI prompt set to: {prompt}")

# /get_current_ai_prompt
@bot.slash_command(name="get_current_ai_prompt",
                  description="Set the style of AI response.",
                  guild_ids=[692123814989004862])
async def add_quote(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 

  prompt = get_ai_prompt(db)

  await ctx.respond(f"Currently I am programmed to respond based on this: {prompt}")

# /mantrip
@bot.slash_command(name="mantrip",
                description="Days remaining til ManTrip™.",
                guild_ids=[692123814989004862])
async def mantrip(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel
  
  today = datetime.now().date()
  mantrip = date(2027, 1, 15)
  days_til = mantrip - today
  days_til = days_til.days

  await ctx.respond(f"There's {days_til} day(s) left until ManTrip 2026!")

# /chuggys_temp
@bot.slash_command(name="chuggys_temp",
                  description="Get the tempature in Chuggy's backyard.",
                  guild_ids=[692123814989004862])
async def chuggys_temp(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 

  temp = get_chuggys_temp()

  await ctx.respond(f"The current temperature in Chuggy's backyard is {temp}F.\nFor complete weather conditions, go here: https://www.pwsweather.com/station/pws/w4spdwx")

# /beer_bitch
@bot.slash_command(name="beer_bitch",
                  description="Get information on current Beer Bitch",
                  guild_ids=[692123814989004862])
async def beer_bitch(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel
  
  beer_bitch = functions.get_beer_bitch_info(db)    
  await ctx.respond(beer_bitch)

# /give_beer - note that you owe someone a beer
@bot.slash_command(name="give_beer",
                  description="Give a beer to someone for them to claim.",
                  guild_ids=[692123814989004862])
async def give_beer(ctx, owed_to, reason):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel
  
  give_beer_insert(db, ctx.author.id, owed_to, reason)

  await ctx.respond(f"<@{ctx.author.id}> has just given {owed_to} a beer for {reason}!")
# /claim_beer - remove the given beer after claiming

# /beer_tally - check if you have any free beers in queue


# /say_stuff - make the bot say what you type
@bot.slash_command(name="say_stuff",
                  description="Say stuff",
                  guild_ids=[692123814989004862],
                  role_ids=[1092591212202045552])
async def say_stuff(ctx, words):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 

  await ctx.respond(f"{words}")
'''
# /discipline_pint - give people points for being bad
@bot.slash_command(name="discipline_point",
                  description="Add discipline point to user.",
                  guild_ids=[692123814989004862],
                  role_ids=[1092591212202045552])
async def discipline_point(ctx, amount, user, reason):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 
  
  add_discipline_point(user, amount, reason)

  await ctx.respond(f"{amount} discipline point(s) given to {user}. REASON - {reason}")
'''

# /discipline_point_total - check how many pointsa user has
@bot.slash_command(name="discipline_point_total",
                  description="Get users discipline point total.",
                  guild_ids=[692123814989004862])
async def discipline_point(ctx, user):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 

  total_points = get_discipline_point(db, user)

  await ctx.respond(f"{user} currently has {total_points} discipline point(s).")

# /photo - display a random photo from BAMPh memories
@bot.slash_command(name="photo",
                   description="Show a random photo from BAMPh activities.",
                   guild_ids=[692123814989004862],
                   role_ids=[1092591212202045552])
async def photo(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 
  
  photo = get_photo(db)

  await ctx.respond(f"{photo}")

# /all_user_points - show all points that have been given with reason to user
@bot.slash_command(name="all_user_points",
                  description="Show all points that have been given with reason to user",
                  guild_ids=[692123814989004862],
                  role_ids=[1092591212202045552])
async def all_user_points(ctx, user):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 

  points = get_discipline_point_desc(db, user)

  # Handle the instance of the user not currently having any points assigned to them
  if isinstance(points, str) == True:
    result_set = points
  else:
    result_set = f"Current Points for {user}"
    for point in points:
      result_set = result_set + f"\nPoints Given: {point[0]} - Reason: {point[1]}"

  await ctx.respond(f"{result_set}")

# /top10dp - show the top 10 discipline point people
@bot.slash_command(name="top10dp",
                  description="Show top 10 most discipline points",
                  guild_ids=[692123814989004862],
                  role_ids=[1092591212202045552])
async def top10dp(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 
  
  results = dp_point_rankings(db)
  result_set = ""
  for result in results:
    result_set = result_set + f"\n{result[0]} - {result[1]}"

  await ctx.respond(f"{result_set}")

# Get the course status of Bradshaw
@bot.slash_command(name="course_status",
                  description="Check Bradshaw course status.",
                  guild_ids=[692123814989004862])
async def course_status(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 
  
  course_status = get_course_status()

  await ctx.respond(f"Bradshaw Course Status: {course_status}")

# /get_ai_prompt_log - Returns the globals()['messages'] value
@bot.slash_command(name="get_ai_prompt_log",
                  description="Return the bots prompt log",
                  guild_ids=[692123814989004862],
                  role_ids=[1092591212202045552])
async def get_ai_prompt_log(ctx):
  await ctx.respond(f"{globals()['messages']}")

#endregion Slash Commands

#region Bot Events

# Bot emoji replies
@bot.event
async def on_message(message):

  # Ignore bot messages
  if message.author.bot:
    return

  messageContent = message.content.lower()

  triggers = {
    "clemson": {"type": "reaction", "value": "\N{PILE OF POO}"},
    "clempson": {"type": "reaction", "value": "\N{PILE OF POO}"},
    "jeff": {"type": "reaction", "value": "mynameisjeff:1096781925114466405"},
    "berry": {"type": "reaction", "value": "berry:1096783181228814438"},
    "chuggy": {"type": "reaction", "value": "chuggy:1148715141651763270"},
    "alex": {"type": "reaction", "value": "\N{TRUMPET}"},
    "nice": {"type": "response", "value": "Noice."},
    "goal": {"type": "response", "value": "https://tenor.com/view/doritos-bird-bird-bird-hype-doritos-cheer-bird-gif-27234641"},
    "no u": {"type": "response", "value": "No u!"}
  }

  for trigger, action in triggers.items():
    if trigger in messageContent:
      if action["type"] == "reaction":
        await message.add_reaction(action["value"])
      elif action["type"] == "response":
        await message.channel.send(action["value"])

    

#endregion Bot Events

#region Core Execution

try:
    bot.run(token)
except:
    print('Token err')

#endregion Core Execution



