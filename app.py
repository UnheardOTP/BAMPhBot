import os
import discord
from datetime import datetime, timedelta, date
from discord.ext import commands, tasks
import mysql.connector
import pandas as pd
from sqlalchemy import create_engine
import requests
import json
import openai


print('BAMPhBot Booting...')

#region Bot Definitions

intents = discord.Intents.all()
intents.typing = True
intents.messages = True
intents.message_content = True
bot = discord.Bot(intents=intents)

#endregion Bot Definitions

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

openai.api_key = openai_apikey

#region Functions

# DB engine
def create_db_connection():
  mydb = mysql.connector.connect(
              host=db_host,
              user=db_user,

              password=db_password,
              database=db_database
          )
  
  return mydb

# Used quote reset (when all quotes have been used)
def reset_quotes():
    db_conn = create_db_connection()
    db_cursor = db_conn.cursor()

    sql = "update quotes \
           set quote_used = 0"
    
    db_cursor.execute(sql)
    db_conn.commit()
    db_conn.close()

# Used photo reset (when all photos have been used)
def reset_photos():
    db_conn = create_db_connection()
    db_cursor = db_conn.cursor()

    sql = "update photos \
           set used = 0"
    
    db_cursor.execute(sql)
    db_conn.commit()
    db_conn.close()
    
# Get last run time for photo or quote
def last_run_time(type):
    db_conn = create_db_connection()
    db_cursor = db_conn.cursor()
    
    sql = f"select last_run from last_runs where type = '{type}'"
    
    db_cursor.execute(sql)
    last_run = db_cursor.fetchall()
    
    db_conn.commit()
    db_conn.close()
    
    return str(last_run[0][0])

# Update last run time for photo or quote
def update_last_run(type, last_run):
    db_conn = create_db_connection()
    db_cursor = db_conn.cursor()

    sql = f"update last_runs set last_run = '{last_run}' where type = '{type}'"

    db_cursor.execute(sql)

    db_conn.commit()
    db_conn.close()

# Add quote
def add_quote_to_db(quote, author):
  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()

  sql = f"insert into quotes \
        (quote, author) \
        values \
        ('{quote}', '{author}')"

  db_cursor.execute(sql)
  db_conn.commit()
  db_conn.close()
   
# Last available quote check
def last_quote_check():
    db_conn = create_db_connection()
    db_cursor = db_conn.cursor()

    sql = "select count(*) \
           from quotes \
           where quote_used = 0"

    db_cursor.execute(sql)

    result = db_cursor.fetchall()
 
    db_conn.commit()
    db_conn.close()

    if result[0][0] == 1:
        return True
    else:
        return False

# Last available quote check
def last_photo_check():
    db_conn = create_db_connection()
    db_cursor = db_conn.cursor()

    sql = "select count(*) \
           from photos \
           where used = 0"

    db_cursor.execute(sql)

    result = db_cursor.fetchall()
 
    db_conn.commit()
    db_conn.close()

    if result[0][0] == 1:
        return True
    else:
        return False

def get_quote():
    db_conn = create_db_connection()
    db_cursor = db_conn.cursor()

    sql = "select id, quote, author \
        from quotes \
        where quote_used = 0 \
        ORDER BY RAND() \
        LIMIT 1;"
    db_cursor.execute(sql)

    # If this is the last available quote, reset used quotes
    if last_quote_check() == True:
        reset_quotes()
    
    # Get random quote
    quote = db_cursor.fetchall()

    quote_id = quote[0][0]
    quote_text = quote[0][1]
    author = quote[0][2]

    # Build return string
    rand_quote = f"{quote_text} - {author}"

    # Update random quote as used
    sql = f"update quotes \
        set quote_used = 1 \
        where id = {quote_id}"

    db_cursor.execute(sql)

    db_conn.commit()
    db_conn.close()

    return rand_quote

def get_photo():
    db_conn = create_db_connection()
    db_cursor = db_conn.cursor()

    sql = "select id, photo_link \
        from photos \
        where used = 0 \
        ORDER BY RAND() \
        LIMIT 1;"
    db_cursor.execute(sql)

    # If this is the last available quote, reset used quotes
    if last_photo_check() == True:
        reset_photos()
    
    # Get random quote
    photo = db_cursor.fetchall()

    photo_id = photo[0][0]
    photo_link = photo[0][1]

    # Update random quote as used
    sql = f"update photos \
        set used = 1 \
        where id = {photo_id}"

    db_cursor.execute(sql)

    db_conn.commit()
    db_conn.close()

    return photo_link
  
def birthday_check():
  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()

  sql = "SELECT * FROM birthdays \
         WHERE MONTH(birthday) = MONTH(curdate()) and day(birthday) = DAY(curdate())"
  
  db_cursor.execute(sql)

  birthday = db_cursor.fetchall()

  if db_cursor.rowcount > 0:
     return f"Happy birthday {birthday[0][1]}"
  else:
     return False

def get_chuggys_temp():
  url     = f'https://api.ambientweather.net/v1/devices?apiKey={wx_apikey}&applicationKey={wx_appkey}'

  response = requests.get(url)
  data = response.json()

  temp = data[0]['lastData']['tempf']

  return temp


################### END FUNCTIONS ###################


#region Cron Jobs

intents = discord.Intents.all()
intents.typing = True
intents.messages = True
intents.message_content = True
bot = discord.Bot(intents=intents)

# Start loops

@bot.event
async def on_ready():
    bday_check.start()
    rand_quote.start()
    rand_photo.start()

@bot.event
async def on_message(message):
  channel = message.channel
  author = message.author.id
  messageContent = message.content.lower()
  if "clemson" in messageContent or "clempson" in messageContent:
    emoji = '\N{PILE OF POO}'
    await message.add_reaction(emoji)
    #await channel.send("Fuck clempson.")
  elif "jeff" in messageContent or '<@804804163904340029>' in messageContent:
    emoji = 'mynameisjeff:1096781925114466405'
    await message.add_reaction(emoji)
  elif "berry" in messageContent or '<@462087982523088908>' in messageContent:
    emoji = 'berry:1096783181228814438'
    await message.add_reaction(emoji)
  elif "chuggy" in messageContent or '<@284719233601110016>' in messageContent:
    emoji = 'chuggy:1148715141651763270'
    await message.add_reaction(emoji)
  
  

# Check for bamph birthday
@tasks.loop(hours=24)
async def bday_check():
  await bot.wait_until_ready()
  channel = bot.get_channel(1092446896158679131)

  bday = birthday_check()

  if bday != False:
    await channel.send(f"{bday}")
  
# Send a random quote every 4 hours
@tasks.loop(hours=24)
async def rand_quote():
    await bot.wait_until_ready()
    channel = bot.get_channel(1092446896158679131)
    if datetime.now() - timedelta(hours=23.9) > datetime.fromisoformat(last_run_time('quote')):
      print(f'Quote Run {datetime.now()}')
      await channel.send(get_quote())
      update_last_run('quote', datetime.now().isoformat())

# Send a random quote every 6 hours
@tasks.loop(hours=28)
async def rand_photo():
    await bot.wait_until_ready()
    channel = bot.get_channel(1092446896158679131)
    if datetime.now() - timedelta(hours=27.9) > datetime.fromisoformat(last_run_time('photo')):
      print(f'Photo Run {datetime.now()}')
      await channel.send(get_photo())
      update_last_run('photo', datetime.now().isoformat())

# Start cron jobs
@bot.event
async def on_ready():
  if not bday_check.is_running():
    bday_check.start()
  if not rand_quote.is_running():
    rand_quote.start()
  if not rand_photo.is_running():
    rand_photo.start() 

#endregion Cron Jobs
  
#region Slash Commands

# /quote
@bot.slash_command(name="quote",
                  description="Get a random BAMPh quote.",
                  guild_ids=[692123814989004862])
async def quote(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel    

  await ctx.respond(get_quote())

# /add_quote
@bot.slash_command(name="add_quote",
                  description="Add BAMPh quote.",
                  guild_ids=[692123814989004862])
async def add_quote(ctx, quote, author):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 

  add_quote_to_db(quote, author)

  await ctx.respond(f"{quote} - {author} - Added")

# /mantrip
@bot.slash_command(name="mantrip",
                description="Days remaining til ManTrip™.",
                guild_ids=[692123814989004862])
async def mantrip(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel
  
  today = datetime.now().date()
  mantrip = date(2024, 1, 12)
  days_til = mantrip - today
  days_til = days_til.days

  await ctx.respond(f"There's {days_til} day(s) left until ManTrip 2024!")

# /chuggys_temp
@bot.slash_command(name="chuggys_temp",
                  description="Get the tempature in Chuggy's backyard.",
                  guild_ids=[692123814989004862])
async def chuggys_temp(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 

  temp = get_chuggys_temp()

  await ctx.respond(f"The current temperature in Chuggy's backyard is {temp}F.")

#endregion Slash Commands

#region Test Code

# OpenAI chat
@bot.event
async def on_message(message):
  # Only respond to messages from other users, not from the bot itself
  if message.author == client.user:
    return
  
  # Check if the bot is mentioned in the message
  if client.user in message.mentions:
 
    # Use the OpenAI API to generate a response to the message
    response = openai.Completion.create(
    engine="text-davinci-002",
    prompt=f"{message.content}",
    max_tokens=2048,
    temperature=0.2,
    )

  # Send the response as a message
  await message.channel.send(response.choices[0].text)

#endregion Test Code

#region Bot Events

@bot.event
async def on_message(message):
  channel = message.channel
  author = message.author.id
  author_name = message.author.mention
  messageContent = message.content.lower()
  if "clemson" in messageContent or "clempson" in messageContent:
    emoji = '\N{PILE OF POO}'
    await message.add_reaction(emoji)
    #await channel.send("Fuck clempson.")
  elif "jeff" in messageContent or '<@804804163904340029>' in messageContent:
    emoji = 'mynameisjeff:1096781925114466405'
    await message.add_reaction(emoji)
  elif "berry" in messageContent or '<@462087982523088908>' in messageContent:
    emoji = 'berry:1096783181228814438'
    await message.add_reaction(emoji)
  elif "chuggy" in messageContent or '<@284719233601110016>' in messageContent:
    emoji = 'chuggy:1148715141651763270'
    await message.add_reaction(emoji)

#endregion Bot Events

#region Core Execution

try:
    bot.run(token)
except:
    print('Token err')

#endregion Core Execution



