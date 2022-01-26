# bot.py
import enum
import os
import re
import pytz
import datetime
import asyncio

import discord
import sqlite3 as sl
from dotenv import load_dotenv

import collections
import datetime as DT
import pytz

tzones = collections.defaultdict(set)
abbrevs = collections.defaultdict(set)

for name in pytz.all_timezones:
    tzone = pytz.timezone(name)
    for utcoffset, dstoffset, tzabbrev in getattr(
            tzone, '_transition_info', [[None, None, DT.datetime.now(tzone).tzname()]]):
        tzones[tzabbrev].add(name)
        abbrevs[name].add(tzabbrev)

con = sl.connect('bot.db')
con.cursor().execute('''CREATE TABLE IF NOT EXISTS timezone_pref(
    guild_id VARCHAR(255),
    user_id VARCHAR(255),
    timezone VARCHAR(63),
    PRIMARY KEY(guild_id, user_id)
)''')
con.cursor().execute('''CREATE TABLE IF NOT EXISTS availability(
    guild_id VARCHAR(255),
    user_id VARCHAR(255),
    day INT,
    start INT,
    end INT
)''')
con.commit()

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
ID = os.getenv('APP_ID')

client = discord.Client()

import requests

@client.event
async def on_ready():
    global commands
    commands = {
        "help": {
            "callback": help,
            "description": "See help message",
            "help": "Really?"
        },
        "add_availability": {
            "callback": add_availability,
            "description": "Add availability",
            "help": 
                (
                    "Use this to set your own availability.\n\n"
                    "Each call should specify days of week, time and timezone. For example:\n"
                    f"`@{client.user.display_name} add_availability MF 11-15 GMT-05:00`\n"
                    "will add to the ledger that you are available on Mondays and Fridays, between 11am and 3pm in ET (GMT-5)\n\n"
                    "Keep in mind days start at 0 and end at 24, i.e.:\n"
                    f"`@{client.user.display_name} add_availability M 0-5 GMT-05:00`\n"
                    "means you are available at midnight, until 5am (in the given timezone)\n"
                    f"`@{client.user.display_name} add_availability M 22-24 GMT-05:00`\n"
                    "means you are available 10pm to midnight (in the given timezone)\n"
                    "unfortunately, there's no easy way to describe you're available 10pm to 2am - either use a different timezone or call add_availability twice."
                )
        },
        "remove_availability": {
            "callback": remove_availability,
            "description": "Remove availability",
            "help":
                (
                    "Use this to set your own availability.\n\n"
                    "Each call should specify days of week, time and timezone. For example:\n"
                    f"`@{client.user.display_name} remove_availability MF 11-15 GMT-05:00`\n"
                    "will remove any availability in the ledger on Mondays and Fridays, between 11am and 3pm in ET (GMT-5)\n\n"
                    "Keep in mind days start at 0 and end at 24, i.e.:\n"
                    f"`@{client.user.display_name} remove_availability M 0-5 GMT-05:00`\n"
                    "will remove availability between midnight and 5am (in the given timezone)\n"
                    f"`@{client.user.display_name} remove_availability M 22-24 GMT-05:00`\n"
                    "will remove availability between 10pm and midnight (in the given timezone)\n"
                    "unfortunately, there's no easy way to remove availability between 10pm and 2am - either use a different timezone or call remove_availability twice.\n"
                    "However, you can quickly remove your availability on a day by calling:\n"
                    f"`@{client.user.display_name} remove_availability M 0-24 GMT-05:00` (or any timezone that you'd like)"
                )
        },
        "my_availability": {
            "callback": my_availability,
            "description": "Check your own availability",
            "help":
                (
                    "Use this to check your own availability.\n\n"
                    "Called with no arguments, it will show availability in GMT:\n"
                    f"`@{client.user.display_name} my_availability`\n"
                    "```\n"
                    "Here's the availability I have down for you (in GMT):\n"
                    "M: 16-20\n"
                    "F: 16-20\n"
                    "```\n\n"
                    "Called with an argument, it will show availability in the provided timezone:\n"
                    f"`@{client.user.display_name} my_availability GMT-05:00`\n"
                    "```\n"
                    "Here's the availability I have down for you (in GMT-05:00):\n"
                    "M: 11-15\n"
                    "F: 11-15\n"
                    "```\n\n"
                )
        },
        "group_availability": {
            "callback": group_availability,
            "description": "Check when people are available",
            "help":
                (
                    "Use this to get a summary of people's availability.\n\n"
                    "Called with no arguments, it will show availability in GMT:\n"
                    f"`@{client.user.display_name} group_availability`\n"
                    "```\n"
                    "Here's members' general availability (in GMT):\n"
                    "Monday:\n"
                    "    15-17: UserA\n"
                    "    17-20: UserA, UserB\n"
                    "Friday:\n"
                    "    15-17: UserA\n"
                    "    17-20: UserA, UserB\n"
                    "```\n\n"
                    "Called with an argument, it will show availability in the provided timezone:\n"
                    f"`@{client.user.display_name} group_availability GMT-05:00`\n"
                    "```\n"
                    "Here's members' general availability (in GMT+05:00):\n"
                    "Monday:\n"
                    "    20-22: UserA\n"
                    "    22-24: UserA, UserB\n"
                    "Tuesday:\n"
                    "    0-1: UserA,UserB\n"
                    "Friday:\n"
                    "    20-22: UserA\n"
                    "    22-24: UserA, UserB\n"
                    "Saturday:\n"
                    "    0-1: UserA, UserB\n"
                    "```\n\n"
                )
        },
        "set_timezone": {
            "callback": set_timezone,
            "description": "Set your default timezone",
            "help": "WIP"
        },
    }
    
    for guild in client.guilds:
        print(
            f'{client.user} is connected to the following guild:\n'
            f'{guild.name}(id: {guild.id})'
        )

        url = f"https://discord.com/api/v8/applications/{ID}/guilds/{guild.id}/commands"
        for name, command in commands.items():
            json = {
                "name": name,
                "type": 1,
                "description": command["description"]
            }

            # For authorization, you can use either your bot token
            headers = {
                "Authorization": f"Bot {TOKEN}"
            }

            r = requests.post(url, headers=headers, json=json)
            print(r.content)
            await asyncio.sleep(1)

def availabilityFromDB(records):
    availability = [[], [], [], [], [], [], []]
    for row in records:
        availability[row[2]].append([row[3],row[4]])
    return availability

def availabilityFromInput(days, start, end):
    availability = [[], [], [], [], [], [], []]
    for day in days:
        availability[day].append([start, end])
    return availability

def mergeAvailabilities(lhs, rhs):
    return flattenAvailability([l + r for l,r in zip(lhs,rhs)])

def flattenAvailability(availability):
    newAvailability = [[], [], [], [], [], [], []]
    for day, spans in enumerate(availability):
        newSpans = []
        sortedSpans = list(sorted(spans, key=lambda s: s[0]))
        i = 0
        while i < len(sortedSpans):
            j = i
            while j < len(sortedSpans) - 1 and sortedSpans[j][1] >= sortedSpans[j+1][0]:
                j = j + 1
            newSpans.append([sortedSpans[i][0], sortedSpans[j][1]])
            i = j + 1
        newAvailability[day] = newSpans
    return newAvailability

def removeAvailability(availability, availabilityToRemove):
    newAvailability = [[], [], [], [], [], [], []]
    for day, spans in enumerate(availability):
        newSpans = []
        sortedSpans = list(sorted(spans, key=lambda s: s[0]))
        sortedUnavailableSpans = list(sorted(availabilityToRemove[day], key=lambda s: s[0]))
        i = 0
        j = 0
        while i < len(sortedSpans) and j < len(sortedUnavailableSpans):
            if sortedSpans[i][1] < sortedUnavailableSpans[j][0]:
                # Entirely before next block
                newSpans.append([sortedSpans[i][0], sortedSpans[i][1]])
                i = i + 1
                continue

            if sortedSpans[i][0] > sortedUnavailableSpans[j][1]:
                # Entirely after next block
                j = j + 1
                continue
            
            if sortedSpans[i][0] < sortedUnavailableSpans[j][0]:
                # Starts before block
                if sortedSpans[i][1] < sortedUnavailableSpans[j][1]:
                    # Ends within block
                    newSpans.append([sortedSpans[i][0], sortedUnavailableSpans[j][0]])
                else:
                    # Ends after block - this should handle more blocks but eh
                    # TODO or something, there's no way to block out more than one range right now
                    newSpans.append([sortedSpans[i][0], sortedUnavailableSpans[j][0]])
                    newSpans.append([sortedUnavailableSpans[j][1], sortedSpans[i][1]])
                i = i + 1
                continue
            
            if sortedSpans[i][1] > sortedUnavailableSpans[j][1]:
                # Starts within block, ends after block
                newSpans.append([sortedUnavailableSpans[j][1], sortedSpans[i][1]])
                i = i + 1
                continue
            
            # Entirely within block - no action.
            i = i + 1
        if j >= len(sortedUnavailableSpans) and i < len(sortedSpans):
            newSpans = newSpans + sortedSpans[i:]
        newAvailability[day] = newSpans
    return newAvailability

def toGMTAvailability(availability, offsetHours):
    gmtAvailability = [[], [], [], [], [], [], []]
    for day, spans in enumerate(availability):
        for span in spans:
            start = span[0] - offsetHours
            end = span[1] - offsetHours
            inDay = True
            if start < 0:
                previousStart = 24 + start
                previousEnd = 24
                start = 0
                if end <= 0:
                    previousEnd = 24 + start
                    inDay = False
                previousDay = day - 1
                if previousDay < 0:
                    previousDay = len(availability) - 1
                gmtAvailability[previousDay].append([previousStart,previousEnd])
            if end > 24:
                nextStart = 0
                nextEnd = end - 24
                end = 24
                if start > 23:
                    nextStart = start - 24
                    inDay = False
                nextDay = day + 1
                if nextDay >= len(availability):
                    nextDay = 0
                gmtAvailability[nextDay].append([nextStart, nextEnd])
            if inDay:
                gmtAvailability[day].append([start, end])
    return gmtAvailability

def offsetFromTimezoneString(string):
    if string not in tzones:
        return None
    
    for tz in tzones[string]:
        timezone = pytz.timezone(tz)
        return int(round(datetime.datetime.now(timezone).utcoffset().total_seconds()/60/60))

def getTimezonePreference(guild_id, user_id):
    with con:
            hasPreference = (con.execute(f"SELECT COUNT(1) FROM timezone_pref WHERE guild_id='{guild_id}' AND user_id='{user_id}'").fetchone()[0] != 0)
            if not hasPreference:
                return (f"You don't have a default timezone yet! You can specify one using set_timezone. For example:\n"
                        "`{client.user.mention} set_timezone EST` will set your default timezone to EST")
            
            timezone = con.execute(f"SELECT timezone FROM timezone_pref WHERE guild_id='{guild_id}' AND user_id='{user_id}'").fetchone()[0]
            return (timezone, offsetFromTimezoneString(timezone))

def parse_availability(message, messageComponents):
    if len(messageComponents) < 2 or len(messageComponents) > 3:
        return (f"Sorry, {message.author.mention}, I didn't get that. When managing availability,"
                " make sure you only specify days of week and time (with optional timezone offset), like so:\n"
                f"{client.user.mention} add_availability MF 11-15 EST")
    for char in messageComponents[0]:
        if char not in "MTWRFSN":
            return (f"Sorry, {message.author.mention}, I didn't get that. {messageComponents[0]}"
                    " is an invalid day of week specifier. Make sure you only use the following:\n"
                    "M - Monday\n"
                    "T - Tuesday\n"
                    "W - Wednesday\n"
                    "R - Thursday\n"
                    "F - Friday\n"
                    "S - Saturday\n"
                    "N - Sunday\n")
    m = re.match("^(\d+)-(\d+)$", messageComponents[1])
    if not m:
        return (f"Sorry, {message.author.mention}, I didn't get that. {messageComponents[1]}"
                " is an invalid time specifier. Make sure you use military time and specify "
                "start and end time, like so:\n"
                f"{client.user.mention} add_availability MF 11-15 EST")
    start = int(m.groups()[0])
    end = int(m.groups()[1])
    if start > end or start < 0 or start > 24 or end < 0 or end > 24:
        return (f"Sorry, {message.author.mention}, I didn't get that. {messageComponents[1]}"
                " is an invalid time specifier. Make sure you use military time and specify "
                "start and end time, like so:\n"
                f"{client.user.mention} add_availability MF 11-15 GMT-05:00\n"
                "If you want to terminate time at midnight, use 24 instead of 0:\n"
                f"{client.user.mention} add_availability S 20-24 GMT-05:00\n")

    offsetHours = None
    if len(messageComponents) == 3:
        offsetHours = offsetFromTimezoneString(messageComponents[2])
        if offsetHours is None:
            return (f"Sorry, {message.author.mention}, I didn't get that. {messageComponents[2]}"
                    " is an invalid timezone specifier. Make sure you specify GMT offset, like so:\n"
                    f"{client.user.mention} add_availability MF 11-15 GMT+02:00\n"
                    f"{client.user.mention} add_availability MF 11-15 GMT-05:00")
    else:
        _, offsetHours = getTimezonePreference(message.guild.id, message.author.id)
    
    inputAvailability = availabilityFromInput(['MTWRFSN'.index(char) for char in messageComponents[0]], start, end)
    return toGMTAvailability(inputAvailability, offsetHours)

async def add_availability(message, messageComponents):
    res = parse_availability(message, messageComponents)
    if type(res) == str:
        return res
    gmtAvailability = res
    
    with con:
        availability = con.execute(f"SELECT * FROM availability WHERE guild_id='{message.guild.id}' AND user_id='{message.author.id}'")
        dbAvailability = availabilityFromDB(availability)
        resolvedAvailability = flattenAvailability(mergeAvailabilities(dbAvailability, gmtAvailability))
        con.execute(f"DELETE FROM availability WHERE guild_id='{message.guild.id}' AND user_id='{message.author.id}'")
        for day, spans in enumerate(resolvedAvailability):
            if len(spans) != 0:
                for span in spans:
                    con.execute(f"INSERT INTO availability VALUES ('{message.guild.id}','{message.author.id}',{day},{span[0]},{span[1]})")
    return f"{message.author.mention} - updated your availability, thanks!"

async def remove_availability(message, messageComponents):
    res = parse_availability(message, messageComponents)
    if type(res) == str:
        return res
    gmtAvailability = res
    
    with con:
        availability = con.execute(f"SELECT * FROM availability WHERE guild_id='{message.guild.id}' AND user_id='{message.author.id}'")
        dbAvailability = availabilityFromDB(availability)
        resolvedAvailability = removeAvailability(dbAvailability, gmtAvailability)
        con.execute(f"DELETE FROM availability WHERE guild_id='{message.guild.id}' AND user_id='{message.author.id}'")
        for day, spans in enumerate(resolvedAvailability):
            if len(spans) != 0:
                for span in spans:
                    con.execute(f"INSERT INTO availability VALUES ('{message.guild.id}','{message.author.id}',{day},{span[0]},{span[1]})")
    return f"{message.author.mention} - updated your availability, thanks!"

async def my_availability(message, messageComponents):
    cur = con.cursor()
    numAvailability = cur.execute(f"SELECT COUNT(1) FROM availability WHERE guild_id='{message.guild.id}' AND user_id='{message.author.id}'").fetchone()[0]
    if numAvailability == 0:
        return (f"Hi {message.author.mention}! I don\'t have any availability noted for you yet... Set it like so:\n"
                f"{client.user.mention} add_availability MF 11-15 GMT-05:00")
    
    availability = cur.execute(f"SELECT * FROM availability WHERE guild_id='{message.guild.id}' AND user_id='{message.author.id}' ORDER BY day")
    
    response = ""
    timezone, _ = getTimezonePreference(message.guild.id, message.author.id)
    offsetHours = offsetFromTimezoneString(timezone)
    if len(messageComponents) == 1:
        requestedOffset = offsetFromTimezoneString(messageComponents[0])
        if offsetHours is None:
            response = response + f"Sorry, I didn't get the timezone specifier {messageComponents[0]}. Using {timezone}...\n"
        else:
            offsetHours = requestedOffset
            timezone = messageComponents[0]

    response = response + f'Hi {message.author.mention}! Here\'s the availability I have down for you (in {timezone}):'
    availability = availabilityFromDB(availability)
    timezoneAvailability = flattenAvailability(toGMTAvailability(availability, -offsetHours)) if offsetHours != 0 else availability
    for day, spans in enumerate(timezoneAvailability):
        if len(spans) != 0:
            response = response + f"\n{'MTWRFSN'[day]}: " + ", ".join([f"{span[0]}-{span[1]}" for span in spans])
    return response

async def getGuildMembersById(guild, ids):
    result = {}
    for id in ids:
        result[id] = await guild.fetch_member(id)
    return result

async def group_availability(message, messageComponents):
    response = ""
    timezone, _ = getTimezonePreference(message.guild.id, message.author.id)
    offsetHours = offsetFromTimezoneString(timezone)
    if len(messageComponents) == 1:
        requestedOffset = offsetFromTimezoneString(messageComponents[0])
        if offsetHours is None:
            response = response + f"Sorry, I didn't get the timezone specifier {messageComponents[0]}. Using {timezone}...\n"
        else:
            offsetHours = requestedOffset
            timezone = messageComponents[0]

    cur = con.cursor()
    allAvailability = cur.execute(f"SELECT * FROM availability WHERE guild_id='{message.guild.id}' ORDER BY user_id")
    userAvailability = {}
    for row in allAvailability:
        userAvailability.setdefault(row[1], []).append(row)
    
    for user in userAvailability.keys():
        availability = availabilityFromDB(userAvailability[user])
        if offsetHours != 0:
            availability = toGMTAvailability(availability, -offsetHours)
        userAvailability[user] = availability

    dailyAvailability = [[], [], [], [], [], [], []]
    for i in range(len(dailyAvailability)):
        for _ in range(24):
            dailyAvailability[i].append(set())
        
        for user_id in userAvailability.keys():
            for spans in userAvailability[user_id][i]:
                for j in range(spans[0], spans[1]):
                    dailyAvailability[i][j].add(user_id)
    
    response = f"Here's members' general availability (in {timezone}):"
    for i, day in enumerate(dailyAvailability):
        groupStart = None
        groupMembers = set()
        availableGroups = []
        for j, available in enumerate(day):
            if len(available) != 0 and groupStart == None:
                groupStart = j
                groupMembers = available
            elif groupMembers != available:
                if groupStart != None:
                    names = [member.display_name for member in (await getGuildMembersById(message.guild, groupMembers)).values()]
                    membersString = ", ".join(names)
                    availableGroups.append(f"{groupStart}-{j}: {membersString}")
                
                if len(available) != 0:
                    groupStart = j
                    groupMembers = available
                else:
                    groupStart = None
                    groupMembers = set()
        
        if groupStart != None:
            names = [member.display_name for member in (await getGuildMembersById(message.guild, groupMembers)).values()]
            membersString = ", ".join(names)
            availableGroups.append(f"{groupStart}-{24}: {membersString}")

        if len(availableGroups) != 0:
            day = ["Mon", "Tues", "Wednes", "Thurs", "Fri", "Satur", "Sun"][i] + "day" # don't judge me
            response = response + "\n" + day + ":\n\t" + "\n\t".join(availableGroups)

    return response

async def help(message, messageComponents):
    response = f"Hey {message.author.mention}!"
    if len(messageComponents) == 1:
        command = messageComponents[0]
        if commands.get(command) is None:
            response = response + f" Hm, sorry, I don't recognize the command {command}."
        else:
            response = response + f" Here's what I found for {command}:\n"
            response = response + commands.get(command)["help"]
            return response

    response = response + '\nHere\'s a list of things you can do:'
    for name, command in commands.items():
        response = response + f"\n{client.user.mention} {name} - {command['description']}"
    return response

async def set_timezone(message, messageComponents):
    if len(messageComponents) != 1:
        return (f"Sorry {message.author.mention}, I didn't get that. Try to specify a timezone, e.g.:\n"
                f"`@{client.user.display_name} set_timezone PST`")
    timezone = messageComponents[0]
    offset = offsetFromTimezoneString(timezone)
    if offset is None:
        return f"Sorry {message.author.mention}, I didn't get the timezone specifier {timezone} - not changing preference."

    with con:
        con.execute(f"INSERT INTO timezone_pref VALUES ('{message.guild.id}','{message.author.id}','{timezone}') ON CONFLICT(guild_id, user_id) DO UPDATE SET timezone='{timezone}'")
    return (f"OK, {message.author.mention} - setting your default timezone to {timezone}. "
            "All future actions with the bot will assume that timezone, if one is not provided")

async def unknown_command(message, messageComponents):
    return f'Hey {message.author.mention}! I didn\'t get that - use "{client.user.mention} help" to see what you can do...'

@client.event
async def on_message(message):
    if message.author.bot:
        return False

    if "@here" in message.content or "@everyone" in message.content or message.type == "REPLY":
        return False

    if client.user.id in [m.id for m in message.mentions]:
        print(f'Got message: {message.content} @{message.mentions}')
        messageComponents = list(filter(lambda x: not not x, re.split('\s+', re.sub(r'(?is)\s*<@!?\d+>\s*', ' ', message.content))))
        command = messageComponents[0]
        if command in commands:
            command_callback = commands[command]["callback"]
        else:
            command_callback = unknown_command
        
        await message.channel.send(await command_callback(message, messageComponents[1:]))
        

client.run(TOKEN)