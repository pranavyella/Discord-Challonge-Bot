import os, discord, asyncio, challonge, requests, sqlite3
from socket import timeout
from urllib.error import HTTPError
from dotenv import load_dotenv
from discord.ext import commands


load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
user = os.getenv('CHALLONGE_USER')
api_key = os.getenv('CHALLONGE_KEY')
challonge.set_credentials(user, api_key)

bot = commands.Bot(command_prefix = '.', intents=discord.Intents.all())

tournaments = challonge.tournaments.index()
latest_tourney = tournaments[len(tournaments) - 1]
ch_subdomain = "088fd351cc405bd64d56171a"
matches = challonge.matches.index(latest_tourney['url'])


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    conn = sqlite3.connect('discord_to_challonge.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS discord_to_challonge (
            discord_id TEXT,
            discord_name TEXT,
            challonge_id TEXT
        )
    ''')
    conn.commit()
    conn.close()


    
@bot.command()
@commands.has_role('T.O.')
async def createtournament(ctx):

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel
    
    await ctx.channel.send("What is the name of your tournament?")
    
    try:
        tourney_name = await bot.wait_for('message', check=check, timeout=30)
        
        await ctx.channel.send("What is the url extension of the tournament? \nFor example, the url of Catch Hands Weekly #7 might be CHW7")
        url_name = await bot.wait_for('message', check=check, timeout=30)

        challonge.tournaments.create(str(tourney_name.content), str(url_name.content), tournament_type='double elimination', subdomain=ch_subdomain, open_signup=True, game_name='Super Smash Bros. Ultimate')
        
        await updateLatestTourney()
        await ctx.channel.send("Tournament created. Here is the bracket link: " + latest_tourney['full_challonge_url'])
        await ctx.channel.send("Here is the sign up link: " + str(latest_tourney['sign_up_url']))
        
    except asyncio.TimeoutError:
        await ctx.send("Timeout occurred. Please use the command again.")
    except (requests.exceptions.HTTPError, challonge.api.ChallongeException):
        await ctx.send("That URL extension is already taken. Please use the command again.")
    except discord.ext.commands.errors.MissingRole:
        await ctx.send("You must be a T.O. in order to use this command.")
        
  

@bot.command()
@commands.has_role('T.O.')
async def deletetournament(ctx):
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel
    
    await ctx.channel.send("What is the URL extension of your tournament?\nFor example, the URL extension of crazyhand.challonge.com/CHW100 is CHW100")
    
    
    try:
        url_name = await bot.wait_for('message', check=check, timeout=30)       

        challonge.tournaments.destroy( + "-" + str(url_name.content))
        await ctx.channel.send("Tournament deleted.")
        await updateLatestTourney()
        
    except asyncio.TimeoutError:
        await ctx.send("Timeout occurred. Please use the command again.")
    except requests.exceptions.HTTPError:
        await ctx.send("That URL extension does not exist. Please use the command again.")
    except discord.ext.commands.errors.MissingRole:
        await ctx.send("You must be a T.O. in order to use this command.")


async def tourney_loop():
    channel_names = ['lobby-1', 'lobby-2', 'lobby-3', 'lobby-4', 'lobby-5']
    for i in range(0, 5):
        guild = bot.get_guild(881993436962392872)
        await guild.create_text_channel(channel_names[i])

    while latest_tourney['state'] != 'complete':
        channel_idx = 0
        all_matches_completed = True
        #go through the list of matches and start a thread with the two players in an ongoing match in the next available channel
        for match in matches:
            
            if match['state'] == 'open':
                all_matches_completed = False
                user1 = match['player1_id']
                user2 = match['player2_id']

                #find the discord id of the two players
                conn = sqlite3.connect('discord_to_challonge.db')
                cursor = conn.cursor()
                cursor.execute('SELECT discord_id FROM discord_to_challonge WHERE challonge_id = ?', (user1,))
                user1_discord_id = cursor.fetchone()
                cursor.execute('SELECT discord_id FROM discord_to_challonge WHERE challonge_id = ?', (user2,))
                user2_discord_id = cursor.fetchone()
                conn.close()
                
                #start a thread with the two players in the next available channel
                guild = bot.get_guild(881993436962392872)
                channel = guild.get_channel(channel_names[channel_idx])
                thread = await channel.create_thread(name="Match between " + user1_discord_id + " and " + user2_discord_id)
                await thread.send("@{} @{}".format(user1_discord_id, user2_discord_id)) #pings both users in the created thread

                match['state'] = 'pending'

                channel_idx += 1
                if channel_idx == 5:
                    channel_idx = 0
                
        if all_matches_completed:
            break


@bot.command()
@commands.has_role('T.O.')
async def starttournament(ctx):
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel
    
    await ctx.channel.send("Are you sure you want to start " + latest_tourney['name'] + '? (Y/N)')
    
    try:
        
        yes_or_no = await bot.wait_for('message', check=check, timeout=30)  
        
        if yes_or_no == 'Y'.lower() or yes_or_no == 'Yes'.lower():
            challonge.tournaments.start(ch_subdomain + "-" + latest_tourney['url'])
            await ctx.send(latest_tourney['name'] + ' has started!')

            tourney_loop()
            await ctx.send(latest_tourney['name'] + ' has ended!')
        else: 
            await ctx.send(latest_tourney['name'] + ' will not be started.')
            
    except asyncio.TimeoutError:
        await ctx.send("Timeout occurred. Please use the command again.")
    except requests.exceptions.HTTPError:
        await ctx.send("That URL extension does not exist. Please use this command again.")
    except discord.ext.commands.errors.MissingRole:
        await ctx.send("You must be a T.O. in order to use this command.")
    except challonge.api.ChallongeException:
        await ctx.send("Your tournament must have at least 2 active participants to be started.")
    

# Function to check if a user is already registered in the database
def get_participant_id(user_id):
    conn = sqlite3.connect('discord_to_challonge.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM discord_to_challonge WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None
 
@bot.command()
@commands.has_role('T.O.')
async def dqplayer(ctx):
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel
    
    await ctx.channel.send("Are you sure you want to dq? (Y/N)")
    
    try:
        
        yes_or_no = await bot.wait_for('message', check=check, timeout=30)  
        
        if yes_or_no == 'Y'.lower() or yes_or_no == 'Yes'.lower():
            conn = sqlite3.connect('discord_to_challonge.db')
            cursor = conn.cursor()
            cursor.execute('SELECT challonge_id from discord_to_challonge WHERE user_id = ?', (user.id,))
            result = cursor.fetchone()
            conn.close()
            challonge.participants.destroy(ch_subdomain + "-" + latest_tourney['url'], result[0])
            await ctx.send("Player has been DQ'd.")
        else:
            await ctx.send("Player has not been DQ'd.")
        
    except asyncio.TimeoutError:
        await ctx.send("Timeout occurred. Please use the command again.")
    except requests.exceptions.HTTPError:
        await ctx.send("That URL extension does not exist. Please use this command again.")
    except discord.ext.commands.errors.MissingRole:
        await ctx.send("You must be a T.O. in order to use this command.")
    except challonge.api.ChallongeException:
        await ctx.send("Your tournament must have at least 2 active participants to be started.")

@bot.command()
@commands.has_any_role('Catch Hands Player', 'T.O.')
async def matchscore(ctx):
    def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel
        
    await ctx.send("What was the final score? Please use the following format: '3-2'")
    try:
        score = await bot.wait_for('message', check=check, timeout=30)
        challonge.matches.update(latest_tourney['url'], 265591700, scores_csv=str(score.content), state='complete')
        await ctx.send("Match updated.")
    
    except asyncio.TimeoutError:
        await ctx.send("Timeout occurred. Please use the command again.")
    except requests.exceptions.HTTPError:
        await ctx.send("That URL extension does not exist. Please use this command again.")
    except discord.ext.commands.errors.MissingRole:
        await ctx.send("You must be a T.O. in order to use this command.")



# Function to check if a user is already registered in the database
def is_user_registered(user_id):
    conn = sqlite3.connect('discord_to_challonge.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM discord_to_challonge WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

@bot.command()
@commands.has_any_role('T.O.', 'Catch Hands Player')
async def signup(ctx):
    await updateLatestTourney()
    user = ctx.author
    await ctx.send("Check your DMs for the sign-up link.")
    await user.send("Here is the sign-up link to the latest tournament: " + str(latest_tourney['sign_up_url']))
    await user.send("Please sign up first using the link above and then type anything to continue.")
    
    #wait for the user to respond with anything in DMs
    def check(msg):
        return msg.author == ctx.author and msg.channel == user.dm_channel
    await bot.wait_for('message', check=check, timeout=120)

    if not is_user_registered(user.id):
        participants = challonge.participants.index(ch_subdomain + "-" + latest_tourney['url'])

        for participant in participants:
            if not is_user_registered(participant['id']):
                await user.send(f"Is this your challonge account? {participant['name']} (Y/N)")
                def check(msg):
                    return msg.author == ctx.author and msg.channel == user.dm_channel
                
                yes_or_no = await bot.wait_for('message', check=check, timeout=60)
                if yes_or_no.content.lower() in ['y', 'yes']:

                    conn = sqlite3.connect('discord_to_challonge.db')
                    cursor = conn.cursor()
                    cursor.execute('INSERT OR REPLACE INTO discord_to_challonge (user_id, challonge_id) VALUES (?, ?)',
                        (user.id, participant['id']))
                    conn.commit()
                    conn.close()

                    await user.send("You are now registered in the database.")                  
                else:
                    await user.send("An error has occurred. Please use the signup command in CH again.")
    else:
        await user.send("You are already registered in the database.")

    

@bot.command()
@commands.has_any_role('T.O.')
async def printdatabase(ctx):
    conn = sqlite3.connect('discord_to_challonge.db')
    cursor = conn.cursor()

    cursor.execute('SELECT user_id, challonge_id FROM discord_to_challonge')
    rows = cursor.fetchall()

    if len(rows) == 0:
        await ctx.send('The database is empty.')
    else:
        for row in rows:
            await ctx.send(f'User ID: {row[0]}, Challonge ID: {row[1]}')

    conn.close()
        
async def updateLatestTourney():
    global tournaments
    global latest_tourney
    
    tournaments = challonge.tournaments.index(subdomain=ch_subdomain)
    latest_tourney = tournaments[len(tournaments) - 1]
    

#If error here, make sure to save all files
bot.run(DISCORD_TOKEN)
