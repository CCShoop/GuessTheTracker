# Written by Cael Shoop

import os
import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

PLAYER_DELIMITER = ','
NAME_DELIMITER = '_^'
SCORE_DELIMITER = '%$'
SCORED = False

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


def tallyScores(PLAYERS):
    print('Tallying scores')
    winners = []
    winner = PLAYERS[0]

    for player in PLAYERS:
        if player.completed and player.score < winner.score:
            winner = player
    winners.append(winner)
    for player in PLAYERS:
        if player.completed and player.name != winner.name and player.score == winner.score:
            winners.append(player)

    for winner in winners:
        winner.wins += 1
    for player in PLAYERS:
        player.score = 0
        writeFile(replaceFileLines('PLAYERS', generatePlayersString(PLAYERS)))
    SCORED = True


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL = os.getenv('TEXT_CHANNEL')
PLAYERS = []
class PLAYER_CLASS:
    completed = False
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
        playersString += f'{player.name},'
    writeFile(replaceFileLines('PLAYERS', playersString))
    os.putenv('PLAYERS', playersString)
    await interaction.response.send_message('You have been registered for GuessTheGame tracking.')

@tree.command(name='deregister', description='Deregister for GuessTheGame tracking. WARNING: YOUR WINS WILL BE PERMANANTLY LOST!')
async def deregister_command(interaction):
    channel = client.get_channel(int(CHANNEL))
    for player in PLAYERS:
        if player.name == interaction.user.name.strip():
            PLAYERS.remove(player)
            print(f'Deregistered user {player.name}')
            await channel.send(f'You have been deregistered for GuessTheGame tracking.')
            return
    print(f'Unregistered user {interaction.user.name.strip()} attempted to deregister')
    await channel.send(f'You were already unregistered for GuessTheGame tracking.')


@tasks.loop(hours=20)
async def midnight_call():
    if not SCORED:
        shamed = ''
        for player in PLAYERS:
            if not player.completed:
                user = discord.utils.get(client.users, name=player.name)
                shamed += f'{user.mention} '
        channel = client.get_channel(int(CHANNEL))
        await channel.send(f'SHAME ON {shamed} FOR NOT ATTEMPTING TO GUESS THE GAME!')
        tallyScores(PLAYERS)
        SCORED = False
    everyone = ''
    for player in PLAYERS:
        player.completed = False
        user = discord.utils.get(client.users, name=player.name)
        everyone += f'{user.mention} '
    channel = client.get_channel(int(CHANNEL))
    await channel.send(f'{everyone} it\'s time to Guess The Game!')


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    await tree.sync()


@client.event
async def on_message(message):
    # message is from this bot
    if message.author == client.user:
        return

    # someone posts their GTG results
    if '#GuessTheGame' in message.content:
        unplayed = ''
        player = PLAYERS[0]
        found = False
        for iPlayer in PLAYERS:
            if message.author.name == iPlayer.name:
                iPlayer.completed = True
                found = True
                player = iPlayer
            elif not iPlayer.completed:
                user = discord.utils.get(client.users, name=iPlayer.name)
                unplayed += f'{user.mention} '
        if not found:
            print('Unregistered player posted a result')
            channel = client.get_channel(int(CHANNEL))
            user = discord.utils.get(client.users, name=message.author.name)
            await channel.send(f'Unregistered user {user.mention} attempted to post a result. Please register with "/register" and try again.')
            return
        print(f'Received GTG message from {message.author}')

        result = message.content.splitlines()[2].replace(' ', '')[1:]
        print('Result line: ' + result)
        for char in result:
            if char == '🟥':
                player.score += 1
            elif char == '🟩':
                break
        print(f'Player {player.name} got a score of {player.score}')

        writeFile(replaceFileLines('PLAYERS', generatePlayersString(PLAYERS)))

        await message.add_reaction('👍')
        print('Added reaction to message')

        if unplayed == '':
            tallyScores(PLAYERS)
        else:
            unplayed += 'Guess The Game!'
            channel = client.get_channel(int(CHANNEL))
            await channel.send(unplayed)
            pass
    else:
        print(f'Ignored message from {message.author}')


# Run client
client.run(TOKEN)
