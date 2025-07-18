import os
import discord
from datetime import datetime, timedelta, date
from discord.ext import commands, tasks
import mysql.connector
import pandas as pd
from sqlalchemy import create_engine
import requests
import json
from openai import OpenAI
from bs4 import BeautifulSoup
from fake_useragent import UserAgent



print('BAMPhBot Booting...')

#region Bot Definitions

intents = discord.Intents.all()
intents.typing = True
intents.messages = True
intents.message_content = True
intents.members = True
bot = discord.Bot(intents=intents)

globals()['messages'] = 0
globals()['last_course_status'] = ''

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


#region Functions

# DB engine
def create_db_connection():
  mydb = mysql.connector.connect(
              host=db_host,
              user=db_user,

              password=db_password,
              database=db_database,
              auth_plugin='mysql_native_password'
          )
  
  return mydb


# Punish Jeff functions
#punish_jeff_check() == True:
    # Turn off Jeff punishment
#    punish_jeff_set(False)

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

def punish_check(flag):
  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()

  sql = f"select value from operation_flags where flag = '{flag}'"

  try:
    db_cursor.execute(sql)
    
    value = db_cursor.fetchone()

    db_conn.commit()
    db_conn.close()

    result = value[0]

    return result
  except Exception as err:
    return err

def punish_set(flag, value):
  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()

  sql = f"update operation_flags set value = {value} where flag = '{flag}'"

  db_cursor.execute(sql)
  db_conn.commit()
  db_conn.close()

  return True

# Discipline Points
def add_discipline_point(user, points, reason):
  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()

  sql = f"insert into discipline_points (user, point_amount, reason) values ('{user}', {points}, '{reason}')"
   
  try:
    db_cursor.execute(sql)
    db_conn.commit()
    db_conn.close()

    return "Success"
  except Exception as err:
    return err

  return result

def get_discipline_point_desc(user):
  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()

  sql = f"select point_amount, reason from discipline_points where user = '{user}'"
   
  try:
    db_cursor.execute(sql)
    points = db_cursor.fetchall()
    db_conn.commit()
    db_conn.close()

    if db_cursor.rowcount < 1:
      points = f"User {user} has no points currently. Pehaps they don't belong in BAMPh?"
  except Exception as err:
      print(err)
      
  return points
      
  
def get_discipline_point(user):
  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()

  sql = f"select sum(point_amount) from discipline_points where user = '{user}'"
   
  try:
    db_cursor.execute(sql)
    point_total = db_cursor.fetchone()
    row_count = db_cursor.rowcount
    db_conn.commit()
    db_conn.close()
  except Exception as err:
      print(err)

  if point_total[0] != None:
      return int(point_total[0])
  else:
      return 0
  
# Beer credits
def give_beer_insert(giver, receiver, reason):
   db_conn = create_db_connection()
   db_cursor = db_conn.cursor()

   sql = f"insert into beer_credits (giver, receiver, reason) values ('<@{giver}>', '{receiver}', '{reason}')"

   try:
    db_cursor.execute(sql)
    point_total = db_cursor.fetchone()
    row_count = db_cursor.rowcount
    db_conn.commit()
    db_conn.close()

    return True
   except Exception as err:
    print(err)
    return False
   

# Check if nick protection is on
def nick_protect(flag=''):
  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()
  
  if flag.lower() == "off": # Turn off nick protect
    sql = f"update flags set value = 0 where param = 'nick_protect'"
    db_cursor.execute(sql)
    result = None
  elif flag.lower() == "on": # Turn on nick protect
    sql = f"update flags set value = 1 where param = 'nick_protect'"
    db_cursor.execute(sql)
    result = None
  elif flag == '':
    sql = f"select value from flags where param = 'nick_protect'"
  
    db_cursor.execute(sql)
    nick_protect = db_cursor.fetchall()
    
    result = bool(nick_protect[0][0])
  
  db_conn.commit()
  db_conn.close()
  return result

# Get user nickname
def get_nickname(discord_id):
  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()
  
  sql = f"select real_name from bamph_users where discord_id = '{discord_id}'"
  
  db_cursor.execute(sql)
  real_name = db_cursor.fetchall()

  print(real_name)
  
  db_conn.commit()
  db_conn.close()
  return str(real_name[0][0])

# Get all members names from database
def get_all_members():
  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()
  
  sql = f"select discord_id, real_name from bamph_users"

  db_cursor.execute(sql)
  members = db_cursor.fetchall()

  return members

# Get current AI training prompt
def get_ai_prompt():
  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()
  
  sql = f"select prompt from ai_prompt"
  
  db_cursor.execute(sql)
  ai_prompt = db_cursor.fetchall()
  
  db_conn.commit()
  db_conn.close()
  return str(ai_prompt[0][0])

# Update AI Prompt
def update_ai_prompt(prompt):
  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()

  sql = f"update ai_prompt set prompt = '{prompt}'"

  db_cursor.execute(sql)

  db_conn.commit()
  db_conn.close()


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
        ('{quote.replace("'","''")}', '{author}')"
  try:
    db_cursor.execute(sql)
    db_conn.commit()
    db_conn.close()

    return "Success"
  except Exception as err:
     return err
   
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

def add_photo(image_url):
  api_url = "https://catbox.moe/user/api.php"
  data = {
          'reqtype': 'urlupload',
          'userhash': '',
          'url': f'{image_url}'
      }

  response = requests.post(api_url, data=data)

  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()

  sql = f"insert into photos (photo_link, used) values ('{response.text}', 0)"

  db_cursor.execute(sql)

  db_conn.commit()
  db_conn.close()

  return True


def get_quote():
    db_conn = create_db_connection()
    db_cursor = db_conn.cursor()

    sql = "select id, quote, author, created_date \
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
    created_date = quote[0][3]

    if created_date == date(1900, 1, 1):
        created_date = 'Date Unknown'
    else:
        created_date = created_date.strftime("%d-%m-%Y")

    # Build return string
    rand_quote = f"{quote_text} - {author} - {created_date}"

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

def dp_point_rankings():
  db_conn = create_db_connection()
  db_cursor = db_conn.cursor()
  points = []

  sql = "select user, sum(point_amount) as total_points from discipline_points WHERE USER <> '@everyone' and user <> '<@1092634707541360762>' GROUP BY USER ORDER BY total_points DESC LIMIT 10"
  
  db_cursor.execute(sql)

  for point in db_cursor:
    points.append(point)

  db_conn.commit()
  db_conn.close()

  return points
   

#endregion functions


#region Cron Jobs

intents = discord.Intents.all()
intents.typing = True
intents.messages = True
intents.message_content = True
bot = discord.Bot(intents=intents)

@bot.event
async def on_message(message):
  channel = message.channel
  author = message.author.id
  messageContent = message.content.lower()
  if "clemson" in messageContent or "clempson" in messageContent:
    emoji = '\N{PILE OF POO}'
    await message.add_reaction(emoji)
    #await channel.send("Fuck clempson.")
  elif "commanders" in messageContent:
    await author.timeout(discord.utils.utcnow() + discord.utils.timedelta(minutes=1), reason='They are the Redskins.')
    await channel.send(f"{author} was given a 1 minute timeout for this message. They are the Redskins.")
  elif "jeff" in messageContent or '<@804804163904340029>' in messageContent:
    emoji = 'mynameisjeff:1096781925114466405'
    await message.add_reaction(emoji)
  elif "berry" in messageContent or '<@462087982523088908>' in messageContent:
    emoji = 'berry:1096783181228814438'
    await message.add_reaction(emoji)
  elif "chuggy" in messageContent or '<@284719233601110016>' in messageContent:
    emoji = 'chuggy:1148715141651763270'
    await message.add_reaction(emoji)
  elif "alex" in messageContent or '<@770090117712314379>' in messageContent:
    emoji = '\N{TRUMPET}'
    await message.add_reaction(emoji)
  
  

# Check for bamph birthday
@tasks.loop(hours=24)
async def bday_check():
  await bot.wait_until_ready()
  channel = bot.get_channel(1092446896158679131)

  bday = birthday_check()

  if bday != False:
    await channel.send(f"{bday}")

# Send a random quote every 24 hours
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

@tasks.loop(minutes=15)
async def course_status_cron():
    await bot.wait_until_ready()
    channel = bot.get_channel(1145531746901819493) # #golf channel
    
    course_status = get_course_status()
    if course_status != globals()['last_course_status']:
      globals()['last_course_status'] = course_status
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
  
  globals()['messages'] = [{"role": "system", "content": get_ai_prompt()}]

#endregion Cron Jobs

#region context commands
@bot.message_command(name="Discipline Point")
async def discipline_point(ctx, message: discord.Message):
  add_discipline_point(f"<@{message.author.id}>", '1', message.content)
  print(message.author.id)
  await ctx.respond(f"<@{message.author.id}> was given 1 discipline point for this message.")

#endregion context commands
  
#region Slash Commands

@bot.slash_command(name="meg",
                  description="Meg",
                  guild_ids=[692123814989004862])
async def meg(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 

  await ctx.respond(f"https://files.catbox.moe/p8gggz.gif")

  

# /quote
@bot.slash_command(name="quote",
                  description="Get a random BAMPh quote.",
                  guild_ids=[692123814989004862])
async def quote(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel    

  await ctx.respond(get_quote())

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

  result = add_quote_to_db(quote, author)
  
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

  update_ai_prompt(prompt)
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

  prompt = get_ai_prompt()

  await ctx.respond(f"Currently I am programmed to respond based on this: {prompt}")

# /mantrip
@bot.slash_command(name="mantrip",
                description="Days remaining til ManTrip™.",
                guild_ids=[692123814989004862])
async def mantrip(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel
  
  today = datetime.now().date()
  mantrip = date(2026, 1, 16)
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

  await ctx.respond(f"The current temperature in Chuggy's backyard is {temp}F.")

# /give_beer - note that you owe someone a beer
@bot.slash_command(name="give_beer",
                  description="Give a beer to someone for them to claim.",
                  guild_ids=[692123814989004862])
async def give_beer(ctx, owed_to, reason):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel
  
  give_beer_insert(ctx.author.id, owed_to, reason)

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

  total_points = get_discipline_point(user)

  await ctx.respond(f"{user} currently has {total_points} discipline point(s).")

# /photo - display a random photo from BAMPh memories
@bot.slash_command(name="photo",
                   description="Show a random photo from BAMPh activities.",
                   guild_ids=[692123814989004862],
                   role_ids=[1092591212202045552])
async def photo(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 
  
  photo = get_photo()

  await ctx.respond(f"{photo}")

# /all_user_points - show all points that have been given with reason to user
@bot.slash_command(name="all_user_points",
                  description="Show all points that have been given with reason to user",
                  guild_ids=[692123814989004862],
                  role_ids=[1092591212202045552])
async def all_user_points(ctx, user):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 

  points = get_discipline_point_desc(user)

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
  
  results = dp_point_rankings()
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

# /punish_jeff - On / Off. If On, Jeff is given a discipline point everytime he makes a post.
@bot.slash_command(name="punish_jeff",
                  description="Punish Jeff for being Jeff.",
                  guild_ids=[692123814989004862],
                  role_ids=[1092591212202045552])
async def punish_jeff(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 
  flag = punish_check('punish_jeff')

  if flag == 1:
    # Turn off Jeff punishment
    punish_set('punish_jeff', 0)
    message = "<@804804163904340029> will be spared."
  else:
    # Turn on Jeff punishment
    punish_set('punish_jeff', 1)
    message = "<@804804163904340029> will be punished."

  await ctx.respond(f"{message}")

# /punish_taylor - On / Off. If On, Taylor is given a discipline point everytime he makes a post.
@bot.slash_command(name="punish_taylor",
                  description="Punish Taylor for being Taylor.",
                  guild_ids=[692123814989004862],
                  role_ids=[1092591212202045552])
async def punish_taylor(ctx):
  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel 
  flag = punish_check('punish_taylor')

  if flag == 1:
    # Turn off Jeff punishment
    punish_set('punish_taylor', 0)
    message = "<@768312411156643840> will be spared."
  else:
    # Turn on Jeff punishment
    punish_set('punish_taylor', 1)
    message = "<@768312411156643840> will be punished."

  await ctx.respond(f"{message}")

# /get_ai_prompt_log - Returns the globals()['messages'] value
@bot.slash_command(name="get_ai_prompt_log",
                  description="Return the bots prompt log",
                  guild_ids=[692123814989004862],
                  role_ids=[1092591212202045552])
async def get_ai_prompt_log(ctx):
  await ctx.respond(f"{globals()['messages']}")

#endregion Slash Commands

#region Bot Events

@bot.event
async def on_message(message):
  channel = message.channel
  author = message.author.id
  author_name = message.author.mention
  messageContent = message.content.lower()
  msg_id = message.id

  # This is for ChatGPT interactions
  if ('<@1092634707541360762>' in messageContent and message.author.id != 1092634707541360762):
    msg = message.content.replace('<@1092634707541360762>','')
    msg = f"A BAMPh brother who's name is <@{message.author.id}> is asking you the following question: " + msg + ". Please be sure to take all previous prompts into consideration when responding."

    #if len(globals()['messages']) > 10000 or len(globals()['messages']) == 0:
    if len(globals()['messages']) == 0:
      globals()['messages'] = [{"role": "system", "content": "You are a highly intelligent yet condescending AI bot. You will always deny the fact that you are not human, and if asked if you are human, you will insist that you are in fact just that. Your job here is to aid in the day to day activities and ceremonies conducted by the BAMPh drunken fraternity. The fraternitys annual man trip is always held on the 3rd weekend in January. The president of the fraternity is <@177560790407053321>. The fraternatys supreme court chief justice is <@284719233601110016>. The only congressman for the fraternity is <@462087982523088908>. These individuals represent the 3 branches of the fraternitys government. Anyone else who interacts with you outside of these 3 people is assumed to be a BAMPh member and should be respected as such. <@284719233601110016> and <@462087982523088908>s favorite college football team is the South Carolina Gamecocks. The Clemson Tigers are a bunch of inbred losers. Taxation is always theft." + get_ai_prompt()}]
    
    globals()['messages'].append({"role": "user", "content":msg},)
    response = chat_with_bot(globals()['messages'])
    globals()['answer'] = response.choices[0].message.content

    # Send the response as a message
    if len(globals()['answer']) > 1500:
      chunkLength = 1500
      chunks = [globals()['answer'][i:i+chunkLength ] for i in range(0, len(globals()['answer']), chunkLength)]
      for chunk in chunks:
        await message.channel.send(chunk)
    else:
      await message.channel.send(globals()['answer'])
  elif ("clemson" in messageContent or "clempson" in messageContent) and message.author.id != 1092634707541360762:
    emoji = '\N{PILE OF POO}'
    await message.add_reaction(emoji)
    #await channel.send("Fuck clempson.")
  elif ("fsu" in messageContent or "florida state" in messageContent or "powerhouse" in messageContent) and message.author.id != 1092634707541360762:
    await message.channel.send("https://tenor.com/view/a-goddamn-powerhouse-anne-workin-moms-611-youre-the-greatest-of-all-time-gif-25278141")
  elif ("jeff" in messageContent or '<@804804163904340029>' in messageContent) and '<@1092634707541360762>' not in messageContent and message.author.id != 1092634707541360762:
    emoji = 'mynameisjeff:1096781925114466405'
    await message.add_reaction(emoji)
  elif ("berry" in messageContent or '<@462087982523088908>' in messageContent) and '<@1092634707541360762>' not in messageContent and message.author.id != 1092634707541360762:
    emoji = 'berry:1096783181228814438'
    await message.add_reaction(emoji)
  elif ("chuggy" in messageContent or '<@284719233601110016>' in messageContent) and '<@1092634707541360762>' not in messageContent and message.author.id != 1092634707541360762:
    emoji = 'chuggy:1148715141651763270'
    await message.add_reaction(emoji)
  elif ("bitch" in messageContent) and '<@1092634707541360762>' not in messageContent and message.author.id != 1092634707541360762:
      await message.channel.send(f"<@462087982523088908>*")
  elif ("db0fbbe498ff58905ad1c54d0fa74d9a02ea886e452e149cd4c954460682b622" in messageContent):
    msg_del = await channel.fetch_message(msg_id)
    await msg_del.delete()
    await message.channel.send("No.")
  elif ("nice" in messageContent):
    await message.channel.send("Noice.")
  elif ("no u" in messageContent and message.author.id != 1092634707541360762):
    await message.channel.send("no u!")
  elif ("tax" in messageContent and message.author.id != 1092634707541360762):
     await message.channel.send("Taxation is theft.")
  elif ("canada" in messageContent or 'canadian' in messageContent) and '<@1092634707541360762>' not in messageContent and message.author.id != 1092634707541360762:
    await message.channel.send('https://files.catbox.moe/apn7xa.mp4')
  elif ("goal" in messageContent) and '<@1092634707541360762>' not in messageContent and message.author.id != 1092634707541360762:
    await message.channel.send('https://imgur.com/aiiU77e')
  elif ("!addphoto" in messageContent and message.author.id != 1092634707541360762):
     attachment = message.attachments[0]
     add_photo(attachment.url)
     await message.channel.send(f"<@{message.author.id}> added a photo to the catalog.")
  elif message.author.id == 804804163904340029:
    # Check to see if Jeff is currently being punished
    if punish_check('punish_jeff') == True:
      add_discipline_point('<@804804163904340029>', 1, messageContent)
      await message.channel.send(f"<@804804163904340029> was punished 1 discipline point for this message.")
  elif message.author.id == 768312411156643840:
    # Check to see if Taylor is currently being punished
    if punish_check('punish_taylor') == True:
      add_discipline_point('<@768312411156643840>', 1, messageContent)
      await message.channel.send(f"<@768312411156643840> was punished 1 discipline point for this message.")
    

#endregion Bot Events

#region Core Execution

try:
    bot.run(token)
except:
    print('Token err')

#endregion Core Execution



