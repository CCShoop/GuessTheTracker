# Written by Cael Shoop

import os
import json
import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

JSON_EXT = '.json'

def replaceFileLines(substr, newValue):
    newFileLines = []
    file = open('.env', 'r')
    for line in file.readlines():
        if substr in line:
            line = f'{substr}={newValue}'
            print(f'Replacing {substr} value with {newValue}')
        newFileLines.append(line)
    file.close()
    return newFileLines


def writeEnvFile(newFileLines):
    file = open('.env', 'w')
    for line in newFileLines:
        file.write(line)
    file.close()


def readJsonFile(PLAYERS):
    jsonFileName = str(SERVER_ID) + JSON_EXT
    file = open(jsonFileName, 'r')
    data = json.load(file)
    PLAYERS = []
    for name, playerData in data.items():
        print(f'Loading player {name}')
        newPlayer = PLAYER_CLASS(name, playerData['wins'], playerData['score'], playerData['completed'], playerData['success'])
        print(f'Loaded player {newPlayer.name} - wins: {newPlayer.wins}, score: {newPlayer.score}, completed: {newPlayer.completed}, success: {newPlayer.success}')
        PLAYERS.append(newPlayer)
    file.close()
    print(f'Successfully loaded {jsonFileName}')
    return PLAYERS


def writeJsonFile(PLAYERS):
    jsonFileName = str(SERVER_ID) + JSON_EXT
    file = open(jsonFileName, 'w+')
    data = {}
    for player in PLAYERS:
        data[player.name] = {'wins': player.wins, 'score': player.score, 'completed': player.completed, 'success': player.success}
        print(f'{player.name} json data: {data[player.name]}')
    jsonData = json.dumps(data)
    file.write(jsonData)
    file.close()


def getScore(player):
    return player.score


def tallyScores(PLAYERS):
    if not PLAYERS:
        print('No players to score')
        return
    
    print('Tallying scores')
    winners = []
    results = []
    results.append('GUESSING COMPLETE!\n')

    PLAYERS.sort(key=getScore)
    if PLAYERS[0].success:
        firstWinner = PLAYERS[0]
        winners.append(firstWinner)
        for iPlayer in PLAYERS[1:]:
            if iPlayer.score == firstWinner.score:
                winners.append(iPlayer)
            else:
                break

    placeCounter = 1
    for player in PLAYERS:
        print(f'{placeCounter}. {player.name} ({player.wins} wins) with score of {player.score}')
        if player in winners:
            player.wins += 1
            if player.wins == 1:
                if player.score == 1:
                    results.append(f'1. {player.name} (1 win) wins by guessing the game in ONE GUESS! NICE ONE!\n')
                else:
                    results.append(f'1. {player.name} (1 win) wins by guessing the game in {player.score} guesses!\n')
            else:
                if player.score == 1:
                    results.append(f'1. {player.name} ({player.wins} wins) wins by guessing the game in ONE GUESS! NICE ONE!\n')
                else:
                    results.append(f'1. {player.name} ({player.wins} wins) wins by guessing the game in {player.score} guesses!\n')
        elif player.success:
            if player.wins == 1:
                results.append(f'{placeCounter}. {player.name} (1 win) guessed the game in {player.score} guesses.\n')
            else:
                results.append(f'{placeCounter}. {player.name} ({player.wins} wins) guessed the game in {player.score} guesses.\n')
        else:
            if player.wins == 1:
                results.append(f'{player.name} (1 win) did not successfully guess the game.\n')
            else:
                results.append(f'{player.name} ({player.wins} wins) did not successfully guess the game.\n')
        placeCounter += 1
        player.score = 0
        player.completed = False
        player.success = False

    writeJsonFile(PLAYERS)

    return results


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL = os.getenv('TEXT_CHANNEL')
SERVER_ID = os.getenv('SERVER_ID')
isFirstCall = True
PLAYERS = []
class PLAYER_CLASS:
    def __init__(self, name, wins, score, completed=False, success=False):
        self.name = str(name)
        self.wins = int(wins)
        self.score = int(score)
        self.completed = completed
        self.success = success


intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# Slash Commands
@tree.command(name='track', description='Track this text channel.')
async def track_command(interaction):
    global CHANNEL
    if interaction.channel.id != int(CHANNEL):
        CHANNEL = f'{interaction.channel.id}\n'
        print(f'Now tracking channel {CHANNEL}', end='')
        writeEnvFile(replaceFileLines('TEXT_CHANNEL', CHANNEL))
        os.putenv('TEXT_CHANNEL', CHANNEL)
        await interaction.response.send_message('Now tracking this channel.')
    else:
        print(f'Tried to change channel tracking to current channel')
        await interaction.response.send_message('Already tracking this channel.')

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
    writeJsonFile(PLAYERS)
    await interaction.response.send_message('You have been registered for GuessTheGame tracking.')

@tree.command(name='deregister', description='Deregister for GuessTheGame tracking. WARNING: YOUR WINS WILL BE PERMANANTLY LOST!')
async def deregister_command(interaction):
    removed = False
    for player in PLAYERS:
        if player.name == interaction.user.name.strip():
            PLAYERS.remove(player)
            writeJsonFile(PLAYERS)
            print(f'Deregistered user {player.name}')
            await interaction.response.send_message('You have been deregistered for GuessTheGame tracking.')
            removed = True
    if not removed:
        print(f'Unregistered user {interaction.user.name.strip()} attempted to deregister')
        await interaction.response.send_message('You were already unregistered for GuessTheGame tracking.')


@tasks.loop(hours=20)
async def midnight_call():
    if not PLAYERS:
        return
    global isFirstCall
    if isFirstCall:
        isFirstCall = False
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
    global PLAYERS
    PLAYERS = readJsonFile(PLAYERS)
    if not midnight_call.is_running():
        midnight_call.start()


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

        # player has already sent results
        if player.completed:
            await channel.send(f'{player.name}, you have already submitted your results today.')
            print(f'{player.name} tried to resubmit results')
            return

        result = message.content.splitlines()[2].replace(' ', '')[1:]
        print('Result line: ' + result)
        player.completed = True
        player.score = 0
        for char in result:
            if char == '🟥':
                player.score += 1
            elif char == '🟩':
                player.score += 1
                player.success = True
                break
        print(f'Player {player.name} got a score of {player.score}')

        writeJsonFile(PLAYERS)

        if player.success:
            await message.add_reaction('👍')
            if player.wins == 1:
                if player.score == 1:
                    await channel.send(f'{player.name} (1 win) guessed the game in 1 guess!\n')
                else:
                    await channel.send(f'{player.name} (1 win) guessed the game in {player.score} guesses!\n')
            else:
                if player.score == 1:
                    await channel.send(f'{player.name} ({player.wins} wins) guessed the game in 1 guess!\n')
                else:
                    await channel.send(f'{player.name} ({player.wins} wins) guessed the game in {player.score} guesses!\n')
        else:
            await message.add_reaction('👎')
            if player.wins == 1:
                await channel.send(f'{player.name} (1 win) did not successfully guess the game.\n')
            else:
                await channel.send(f'{player.name} ({player.wins} wins) did not successfully guess the game.\n')

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
