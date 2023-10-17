# Written by Cael Shoop

import os
import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

PLAYER_DELIMITER = ','
NAME_DELIMITER = '_^'
SCORE_DELIMITER = '%$'
DEBUG = False

def replaceFileLines(substr, newValue):
    newFileLines = []
    with open('.env', 'r') as file:
        for line in file.readlines():
            if substr in line:
                line = f'{substr}={newValue}'
                print(f'Replacing {substr} value with {newValue}')
            newFileLines.append(line)
    return newFileLines


def writeFile(newFileLines):
    with open('.env', 'w') as file:
        for line in newFileLines:
            file.write(line)


def generatePlayersString(PLAYERS):
    playersString = ''
    for player in PLAYERS:
        playersString += f'{player.name}{NAME_DELIMITER}{player.wins}{SCORE_DELIMITER}{player.score}{PLAYER_DELIMITER}'
    return playersString


def getScore(player):
    return player.score


def tallyScores(PLAYERS):
    if not PLAYERS:
        print('No players to score')
        return
    
    print('Tallying scores')
    winners = []
    results = []
    
    PLAYERS.sort(key=getScore)
    player = PLAYERS[0]
    winners.append(player)
    for iPlayer in PLAYERS[1:]:
        if iPlayer.score == player.score:
            winners.append(iPlayer)
        else:
            break

    for winner in winners:
        winner.wins += 1

    placeCounter = 1
    for player in PLAYERS:
        print(f'{placeCounter}. {player.name} ({player.wins}) with score of {player.score}')
        if player in winners:
            results.append(f'{placeCounter}. {player.name} ({player.wins}) wins by guessing the game in {player.score} guesses!\n')
        elif player.success:
            placeCounter += 1
            results.append(f'{placeCounter}. {player.name} ({player.wins}) guessed the game in {player.score} guesses.\n')
        else:
            placeCounter += 1
            results.append(f'{placeCounter}. {player.name} ({player.wins}) did not successfully guess the game.\n')

    for player in PLAYERS:
        player.score = 0
        writeFile(replaceFileLines('PLAYERS', generatePlayersString(PLAYERS)))

    return results


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL = os.getenv('TEXT_CHANNEL')
PLAYERS = []
class PLAYER_CLASS:
    completed = False
    success = False
    def __init__(self, name, wins, score):
        self.name = str(name)
        self.wins = int(wins)
        self.score = int(score)


for player in os.getenv('PLAYERS').split(PLAYER_DELIMITER):
    if player != ',' and player != '':
        player = player.split(NAME_DELIMITER)
        name = player[0]
        scores = player[1].split(SCORE_DELIMITER)
        wins = scores[0]
        score = scores[1]
        print(f'Loading player {name} with {wins} wins and score of {score}')
        playerObj = PLAYER_CLASS(name, wins, score)
        PLAYERS.append(playerObj)


intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# Slash Commands
@tree.command(name='track', description='Track this text channel.')
async def track_command(interaction):
    CHANNEL = f'{interaction.channel.id}\n'
    print(f'Now tracking channel {CHANNEL}', end='')
    writeFile(replaceFileLines('TEXT_CHANNEL', CHANNEL))
    os.putenv('TEXT_CHANNEL', CHANNEL)
    await interaction.response.send_message('Now tracking this channel.')

@tree.command(name='register', description='Register for GuessTheGame tracking.')
async def register_command(interaction):
    for player in PLAYERS:
        if interaction.user.name.strip() == player.name.strip():
            print(f'User {interaction.user.name.strip()} attempted to re-register for tracking')
            await interaction.response.send_message('You are already registered for GuessTheGame tracking!')
            return
        
    print(f'Registering user {interaction.user.name.strip()} for tracking')
    playerObj = PLAYER_CLASS(interaction.user.name.strip(), 0, 0)
    PLAYERS.append(playerObj)
    playersString = ''
    for player in PLAYERS:
        playersString += f'{player.name}{NAME_DELIMITER}0{SCORE_DELIMITER}0{PLAYER_DELIMITER}'
    writeFile(replaceFileLines('PLAYERS', playersString))
    os.putenv('PLAYERS', playersString)
    await interaction.response.send_message('You have been registered for GuessTheGame tracking.')

@tree.command(name='deregister', description='Deregister for GuessTheGame tracking. WARNING: YOUR WINS WILL BE PERMANANTLY LOST!')
async def deregister_command(interaction):
    removed = False
    for player in PLAYERS:
        if player.name == interaction.user.name.strip():
            PLAYERS.remove(player)
            playersString = ''
            for player in PLAYERS:
                playersString += f'{player.name}{NAME_DELIMITER}0{SCORE_DELIMITER}0{PLAYER_DELIMITER}'
            writeFile(replaceFileLines('PLAYERS', playersString))
            os.putenv('PLAYERS', playersString)
            print(f'Deregistered user {player.name}')
            await interaction.response.send_message('You have been deregistered for GuessTheGame tracking.')
            removed = True
    if not removed:
        print(f'Unregistered user {interaction.user.name.strip()} attempted to deregister')
        await interaction.response.send_message('You were already unregistered for GuessTheGame tracking.')


#@tasks.loop(hours=20)
@tasks.loop(seconds=15)
async def midnight_call():
    if not PLAYERS:
        return

    channel = client.get_channel(int(CHANNEL))
    shamed = ''
    for player in PLAYERS:
        if not player.completed:
            user = discord.utils.get(client.users, name=player.name)
            shamed += f'{user.mention} '
    if shamed != '':
        await channel.send(f'SHAME ON {shamed} FOR NOT ATTEMPTING TO GUESS THE GAME!')
        tallyScores(PLAYERS)

    everyone = ''
    for player in PLAYERS:
        player.completed = False
        user = discord.utils.get(client.users, name=player.name)
        everyone += f'{user.mention} '
    await channel.send(f'{everyone} it\'s time to Guess The Game!')


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    await tree.sync()
    if not midnight_call.is_running():
        midnight_call.start()
    if DEBUG:
        channel = client.get_channel(int(CHANNEL))
        await channel.send(f'{client.user} is now online')


@client.event
async def on_message(message):
    # message is from this bot
    if message.author == client.user:
        return

    # someone posts their GTG results
    channel = client.get_channel(int(CHANNEL))
    if '#GuessTheGame' in message.content:
        user = discord.utils.get(client.users, name=message.author.name)
        # there are no registered players
        if not PLAYERS:
            await channel.send(f'{user.mention}, there are no registered players! Please register and resend your results to be the first.')
            return

        # player is not registered
        found = False
        for iPlayer in PLAYERS:
            if message.author.name == iPlayer.name:
                found = True
        if not found:
            await channel.send(f'{message.author.name}, you are not registered! Please register and resend your results.')

        unplayed = ''
        player = PLAYERS[0]
        found = False
        for iPlayer in PLAYERS:
            if message.author.name == iPlayer.name:
                iPlayer.completed = True
                found = True
                player = iPlayer
            elif not iPlayer.completed:
                unplayedUser = discord.utils.get(client.users, name=iPlayer.name)
                unplayed += f'{unplayedUser.mention} '
        if not found:
            print('Unregistered player posted a result')
            await channel.send(f'Unregistered user {user.mention} attempted to post a result. Please register with "/register" and try again.')
            return
        print(f'Received GTG message from {message.author}')

        result = message.content.splitlines()[2].replace(' ', '')[1:]
        print('Result line: ' + result)
        player.score = 0
        for char in result:
            if char == '🟥':
                player.score += 1
            elif char == '🟩':
                player.score += 1
                player.success = True
                break
        print(f'Player {player.name} got a score of {player.score}')

        writeFile(replaceFileLines('PLAYERS', generatePlayersString(PLAYERS)))

        await message.add_reaction('👍')
        print('Added reaction to message')

        if unplayed == '':
            for score in tallyScores(PLAYERS):
                await channel.send(score)
        else:
            unplayed += 'Guess The Game!'
            await channel.send(unplayed)
            pass
    else:
        print(f'Ignored message from {message.author}')


# Run client
client.run(TOKEN)
