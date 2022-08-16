import os, discord, asyncio, challonge, requests
from socket import timeout
from urllib.error import HTTPError
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
user = os.getenv('CHALLONGE_USER')
api_key = os.getenv('CHALLONGE_KEY')
challonge.set_credentials(user, api_key)

bot = commands.Bot(command_prefix = '.')

tournaments = challonge.tournaments.index()
latest_tourney = tournaments[len(tournaments) - 1]
ch_subdomain = "088fd351cc405bd64d56171a"
matches = challonge.matches.index(latest_tourney['url'])


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    
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
    
    
    
@bot.command()
@commands.has_role('T.O.')
async def dqplayer(ctx):
    pass

@bot.command()
@commands.has_any_role('Catch Hands Player', 'T.O.')
async def matchscore(ctx):
    def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel
        
    await ctx.send("What was the final score? Please use the following format: '3-2'")
    try:
        score = await bot.wait_for('message', check=check, timeout=30)
        challonge.matches.update(latest_tourney['url'], 265591700, scores_csv=str(score.content))
        await ctx.send("Match updated.")
    
    except asyncio.TimeoutError:
        await ctx.send("Timeout occurred. Please use the command again.")
    except requests.exceptions.HTTPError:
        await ctx.send("That URL extension does not exist. Please use this command again.")
    except discord.ext.commands.errors.MissingRole:
        await ctx.send("You must be a T.O. in order to use this command.")
    # except challonge.api.ChallongeException:
    #     await ctx.send("Your tournament must have at least 2 active participants to be started.")
 
@bot.command()
@commands.has_any_role('T.O.', 'Catch Hands Player')
async def jointournament(ctx):
    def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel
    
    await ctx.send('''Please enter the name or url extension of the tournament you want to join exactly as it appears.\n
                    Examples:\nFor Catch Hands Weekly #7, please type Catch Hands Weekly #7 or CHW7\nFor Crazy Hand Proving Grounds #5,
                    please type Crazy Hands Proving Grounds #5 or CHPG5\nFor Crazy Orders #2, please type Crazy Orders #2 or CO2''')
    
    try:
        tourney_to_join = await bot.wait_for('message', check=check, timeout=30)
        if(tourney_to_join == latest_tourney['name'] or tourney_to_join == latest_tourney['url']):
            await ctx.send("success")

    
    except asyncio.TimeoutError:
        await ctx.send("Timeout occurred. Please use the command again.")
    except requests.exceptions.HTTPError:
        await ctx.send("That URL extension does not exist. Please use this command again.")
    except discord.ext.commands.errors.MissingRole:
        await ctx.send("You must be a T.O. in order to use this command.")
    except challonge.api.ChallongeException:
        await ctx.send("Your tournament must have at least 2 active participants to be started.")

@bot.command()
@commands.has_any_role('T.O.', 'Catch Hands Player')
async def signup(ctx):
    await updateLatestTourney()
    await ctx.send("Here is the sign-up link to the latest tournament: " + str(latest_tourney['sign_up_url']))
    

        
        
async def updateLatestTourney():
    global tournaments
    global latest_tourney
    
    tournaments = challonge.tournaments.index(subdomain=ch_subdomain)
    latest_tourney = tournaments[len(tournaments) - 1]
    
    
#helper functions while creating bot
@bot.command()
async def listtourneystats(ctx):
    for tourney in tournaments:
        for k, v in tourney.items():
            await ctx.send(k + " ---> " + str(v))
        
        
@bot.command()
async def listtourneys(ctx):
    try:
        await updateLatestTourney()
        for tourney in tournaments:
            #skip for loop if tourney id is 5504945
            if tourney['id'] == 5504945:
                continue
            await ctx.send('id' + ' ---> ' + str(tourney['id']))
            await ctx.send('name' + ' ---> ' + tourney['name'])
            await ctx.send('url' + ' ---> ' + tourney['url'])
            await ctx.send('sign-up' + ' ---> ' + str(tourney['open_signup']))
            await ctx.send('sign up url' + ' ---> ' + str(tourney['sign_up_url']))
            #await ctx.send('full sign up url' + ' ---> ' + tourney['full_challonge_url'])
    except IndexError:
        await ctx.send("This account has created no tournaments.")
        
            
@bot.command()
async def latesttourney(ctx):
    await updateLatestTourney
    await ctx.send('name: ' + latest_tourney['name'])
    await ctx.send('url: ' + latest_tourney['url'])
    await ctx.send('sign-up' + ' ---> ' + str(latest_tourney['open_signup']))
    await ctx.send('sign up url' + ' ---> ' + str(latest_tourney['sign_up_url']))
    
@bot.command()
async def listmatches(ctx):
    for match in matches:
        for k, v in match.items():
            await ctx.send(str(k) + ' ---> ' + str(v) + '\n')
        
# General method shell code
@bot.command()
@commands.has_any_role('T.O.', 'Catch Hands Player')
async def join(ctx):
    def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel
        
    await ctx.send("Message")
    
    try:
        variable = await bot.wait_for('message', check=check, timeout=30)
    
    except asyncio.TimeoutError:
        await ctx.send("Timeout occurred. Please use the command again.")
    except requests.exceptions.HTTPError:
        await ctx.send("That URL extension does not exist. Please use this command again.")
    except discord.ext.commands.errors.MissingRole:
        await ctx.send("You must be a T.O. in order to use this command.")
    except challonge.api.ChallongeException:
        await ctx.send("Your tournament must have at least 2 active participants to be started.")


#If error here, make sure to save all files
bot.run(DISCORD_TOKEN)