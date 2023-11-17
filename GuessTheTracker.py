'''Written by Cael Shoop.'''

import os
import json
import discord
import datetime
from typing import Literal
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv


load_dotenv()


def get_time():
    ct = str(datetime.datetime.now())
    hour = int(ct[11:13])
    minute = int(ct[14:16])
    return hour, minute


def main():
    '''Main function'''
    class GuessTheClient(discord.Client):
        '''Custom client class for GuessTheGame bot'''

        FILE_PATH = 'info.json'

        def __init__(self, intents):
            super(GuessTheClient, self).__init__(intents=intents)
            self.gtg_text_channel = 0
            self.gta_text_channel = 0
            self.server_id = 0
            self.players = []
            self.scored_today = False
            self.tree = app_commands.CommandTree(self)


        class GuessThe:
            '''GuessThe class for storing game info'''
            def __init__(self):
                self.winCount = 0
                self.guesses = 0
                self.registered = False
                self.completedToday = False
                self.succeededToday = False

        class Player:
            '''Player class for storing player info'''
            def __init__(self, name):
                self.name = name
                self.gtgame = client.GuessThe()
                self.gtaudio = client.GuessThe()


        async def setup_hook(self):
            await self.tree.sync()


        def read_json_file(self):
            '''Reads player information from the json file and puts it in the players list'''
            if not os.path.exists(self.FILE_PATH):
                print(f'{self.FILE_PATH} does not exist')
                return
            with open(self.FILE_PATH, 'r', encoding='utf-8') as file:
                print(f'Reading {self.FILE_PATH}')
                data = json.load(file)
                for firstField, secondField in data.items():
                    if firstField == 'text_channels':
                        self.gtg_text_channel = secondField['gtg_text_channel']
                        self.gta_text_channel = secondField['gta_text_channel']
                        print(f'Got GTG text channel id of {self.gtg_text_channel}')
                        print(f'Got GTA text channel id of {self.gta_text_channel}')
                    else:
                        print(f'Loading data for {firstField}')
                        load_player = self.Player(firstField)
                        load_player.gtgame.winCount = secondField['gtgame']['winCount']
                        load_player.gtgame.guesses = secondField['gtgame']['guesses']
                        load_player.gtgame.registered = secondField['gtgame']['registered']
                        load_player.gtgame.completedToday = secondField['gtgame']['completedToday']
                        load_player.gtgame.succeededToday = secondField['gtgame']['succeededToday']
                        load_player.gtaudio.winCount = secondField['gtaudio']['winCount']
                        load_player.gtaudio.guesses = secondField['gtaudio']['guesses']
                        load_player.gtaudio.registered = secondField['gtaudio']['registered']
                        load_player.gtaudio.completedToday = secondField['gtaudio']['completedToday']
                        load_player.gtaudio.succeededToday = secondField['gtaudio']['succeededToday']
                        self.players.append(load_player)
                        print(f'Loaded player {load_player.name} - '
                              f'gtg/gta win count: {load_player.gtgame.winCount}/{load_player.gtaudio.winCount}, '
                              f'gtg/gta guesses today: {load_player.gtgame.guesses}/{load_player.gtaudio.guesses}, '
                              f'gtg/gta registered: {load_player.gtgame.registered}/{load_player.gtaudio.registered}, '
                              f'gtg/gta completed today: {load_player.gtgame.completedToday}/{load_player.gtaudio.completedToday}, '
                              f'gtg/gta succeeded today: {load_player.gtgame.succeededToday}/{load_player.gtaudio.succeededToday}')

                print(f'Successfully loaded {self.FILE_PATH}')


        def write_json_file(self):
            '''Writes player information from the players list to the json file'''
            data = {}
            data['text_channels'] = {'gtg_text_channel': self.gtg_text_channel,
                                     'gta_text_channel': self.gta_text_channel}
            for player in self.players:
                data[player.name] = {
                    'gtgame': {'winCount': player.gtgame.winCount,
                               'guesses': player.gtgame.guesses,
                               'registered': player.gtgame.registered,
                               'completedToday': player.gtgame.completedToday,
                               'succeededToday': player.gtgame.succeededToday},
                    'gtaudio': {'winCount': player.gtaudio.winCount,
                               'guesses': player.gtaudio.guesses,
                               'registered': player.gtaudio.registered,
                               'completedToday': player.gtaudio.completedToday,
                               'succeededToday': player.gtaudio.succeededToday}
                }
            json_data = json.dumps(data)
            print(f'Writing {self.FILE_PATH}')
            with open(self.FILE_PATH, 'w+', encoding='utf-8') as file:
                file.write(json_data)


        async def process(self, name, message: discord.Message, channel: discord.TextChannel, guessThe: GuessThe, gt: str):
            # player has already sent results
            if guessThe.completedToday:
                print(f'{name} tried to resubmit results')
                await channel.send(f'{name}, you have already submitted your '
                                    'results today.')
                return

            result = message.content.splitlines()[2].replace(' ', '')[1:]
            print('Result line: ' + result)
            guessThe.completedToday = True
            guessThe.succeededToday = False
            guessThe.guesses = 0
            for char in result:
                if char == '🟥':
                    guessThe.guesses += 1
                elif char == '🟨':
                    guessThe.guesses += 1
                elif char == '🟩':
                    guessThe.guesses += 1
                    guessThe.succeededToday = True
                    break
            print(f'Player {name} got a score of {guessThe.guesses}')

            client.write_json_file()

            for player in client.players:
                if gt == 'gtgame' and not player.gtgame.completedToday:
                    return
                if gt == 'gtaudio' and not player.gtaudio.completedToday:
                    return

            if channel.id == int(client.gtg_text_channel):
                scoreboard = ''
                scoreboardList = client.tally_gtg_scores()
                for line in scoreboardList:
                    scoreboard += line
                await channel.send(scoreboard)
            elif channel.id == int(client.gta_text_channel):
                scoreboard = ''
                scoreboardList = client.tally_gta_scores()
                for line in scoreboardList:
                    scoreboard += line
                await channel.send(scoreboard)
            else:
                print(f'Text channel with id {channel.id} doesn\'t match a saved id')


        def tally_gtg_scores(self):
            '''Sorts players and returns a list of strings to send as Discord messages'''
            if not self.players:
                print('No players to score')
                return

            print('Tallying scores')
            winners = [] # list of winners - the one/those with the lowest score
            results = [] # list of strings - the scoreboard to print out
            results.append('\nGUESSING COMPLETE!\n\n**SCOREBOARD:**\n')

            # sort the players
            self.players.sort(key=player.gtgame.guesses)
            if self.players[0].gtgame.succeededToday:
                # if the player(s) with the lowest score successfully
                # guessed the game, they are the first winner
                first_winner = self.players[0]
                winners.append(first_winner)
                # for the rest of the players, check if they're tied
                for player_it in self.players[1:]:
                    if player_it.gtgame.guesses == first_winner.gtgame.guesses:
                        winners.append(player_it)
                    else:
                        break

            place_counter = 1
            prev_guesses = 0
            for player in self.players:
                print(f'{place_counter}. {player.name} ({player.gtgame.winCount} wins) with {player.gtgame.guesses} guesses')
                if player in winners:
                    player.gtgame.winCount += 1
                    if player.gtgame.winCount == 1:
                        if player.gtgame.guesses == 1:
                            results.append(f'1. {player.name} (1 win) wins by guessing the game in one guess! Nice!\n')
                        else:
                            results.append(f'1. {player.name} (1 win) wins by guessing the game in {player.gtgame.guesses} guesses!\n')
                    else:
                        if player.gtgame.guesses == 1:
                            results.append(f'1. {player.name} ({player.gtgame.winCount} wins) wins by guessing the game in one guess! Nice!\n')
                        else:
                            results.append(f'1. {player.name} ({player.gtgame.winCount} wins) wins by guessing the game in {player.gtgame.guesses} guesses!\n')
                elif player.gtgame.succeededToday:
                    if player.gtgame.winCount == 1:
                        results.append(f'{place_counter}. {player.name} (1 win) guessed the game in {player.gtgame.guesses} guesses.\n')
                    else:
                        results.append(f'{place_counter}. {player.name} ({player.gtgame.winCount} wins) guessed the game in {player.gtgame.guesses} guesses.\n')
                else:
                    if player.gtgame.winCount == 1:
                        results.append(f'{player.name} (1 win) did not successfully guess the game.\n')
                    else:
                        results.append(f'{player.name} ({player.gtgame.winCount} wins) did not successfully guess the game.\n')
                if prev_guesses != player.gtgame.guesses:
                    place_counter += 1
                prev_guesses = player.gtgame.guesses

            self.write_json_file()

            return results


        def tally_gta_scores(self):
            '''Sorts players and returns a list of strings to send as Discord messages'''
            if not self.players:
                print('No players to score')
                return

            print('Tallying scores')
            winners = [] # list of winners - the one/those with the lowest score
            results = [] # list of strings - the scoreboard to print out
            results.append('\nGUESSING COMPLETE!\n\n**SCOREBOARD:**\n')

            # sort the players
            self.players.sort(key=player.gtaudio.guesses)
            if self.players[0].gtaudio.succeededToday:
                # if the player(s) with the lowest score successfully
                # guessed the game, they are the first winner
                first_winner = self.players[0]
                winners.append(first_winner)
                # for the rest of the players, check if they're tied
                for player_it in self.players[1:]:
                    if player_it.gtaudio.guesses == first_winner.gtaudio.guesses:
                        winners.append(player_it)
                    else:
                        break

            place_counter = 1
            prev_guesses = 0
            for player in self.players:
                print(f'{place_counter}. {player.name} ({player.gtaudio.winCount} wins) with {player.gtaudio.guesses} guesses')
                if player in winners:
                    player.gtaudio.winCount += 1
                    if player.gtaudio.winCount == 1:
                        if player.gtaudio.guesses == 1:
                            results.append(f'1. {player.name} (1 win) wins by guessing the audio in one guess! Nice!\n')
                        else:
                            results.append(f'1. {player.name} (1 win) wins by guessing the audio in {player.gtaudio.guesses} guesses!\n')
                    else:
                        if player.gtaudio.guesses == 1:
                            results.append(f'1. {player.name} ({player.gtaudio.winCount} wins) wins by guessing the audio in one guess! Nice!\n')
                        else:
                            results.append(f'1. {player.name} ({player.gtaudio.winCount} wins) wins by guessing the audio in {player.gtaudio.guesses} guesses!\n')
                elif player.gtaudio.succeededToday:
                    if player.gtaudio.winCount == 1:
                        results.append(f'{place_counter}. {player.name} (1 win) guessed the audio in {player.gtaudio.guesses} guesses.\n')
                    else:
                        results.append(f'{place_counter}. {player.name} ({player.gtaudio.winCount} wins) guessed the audio in {player.gtaudio.guesses} guesses.\n')
                else:
                    if player.gtaudio.winCount == 1:
                        results.append(f'{player.name} (1 win) did not successfully guess the audio.\n')
                    else:
                        results.append(f'{player.name} ({player.gtaudio.winCount} wins) did not successfully guess the audio.\n')
                if prev_guesses != player.gtaudio.guesses:
                    place_counter += 1
                prev_guesses = player.gtaudio.guesses

            self.write_json_file()

            return results



    discord_token = os.getenv('DISCORD_TOKEN')

    intents = discord.Intents.all()

    client = GuessTheClient(intents=intents)

    @client.event
    async def on_ready():
        '''Client on_ready event'''
        client.read_json_file()
        if not midnight_call.is_running():
            midnight_call.start()
        print(f'{client.user} has connected to Discord!')


    @client.event
    async def on_message(message):
        '''Client on_message event'''
        # message is from this bot
        if message.author == client.user:
            return

        player = client.players[0]
        if '#GuessTheGame' in message.content:
            channel = client.get_channel(int(client.gtg_text_channel))
        elif '#GuessTheAudio' in message.content:
            channel = client.get_channel(int(client.gta_text_channel))

        # someone posts their GTG results
        if '#GuessTheGame' in message.content or '#GuessTheGame' in message.content:
            user = discord.utils.get(client.users, name=message.author.name)
            # there are no registered players
            if not client.players:
                await channel.send(f'{user.mention}, there are no registered players! '
                            'Please register and resend your results to be the first.')
                return

            # player is not registered
            found = False
            for player_it in client.players:
                if message.author.name == player_it.name:
                    found = True
            if not found:
                await channel.send(f'{message.author.name}, you are not registered! '
                                            'Please register and resend your results.')

            found = False
            for player_it in client.players:
                if message.author.name == player_it.name:
                    found = True
                    player = player_it
            if not found:
                print('Unregistered player posted a result')
                await channel.send(f'Unregistered user {user.mention} attempted to post '
                            'a result. Please register with "/register" and try again.')
                return

        if '#GuessTheGame' in message.content:
            print(f'Received GuessTheGame message from {message.author}')

            guessThe = player.gtgame
            await client.process(player.name, message, channel, guessThe, 'gtgame')

            if guessThe.succeededToday:
                await message.add_reaction('👍')
                if guessThe.guesses == 1:
                    await channel.send(f'{player.name} guessed the game in 1 guess! Nice one!\n')
                else:
                    await channel.send(f'{player.name} guessed the game in {guessThe.guesses} guesses!\n')
            else:
                await message.add_reaction('👎')
                await channel.send(f'{player.name} did not successfully guess the game.\n')
        elif '#GuessTheAudio' in message.content:
            print(f'Received GuessTheAudio message from {message.author}')

            guessThe = player.gtaudio
            await client.process(player.name, message, channel, guessThe, 'gtaudio')

            if guessThe.succeededToday:
                await message.add_reaction('👍')
                if guessThe.guesses == 1:
                    await channel.send(f'{player.name} guessed the audio in 1 guess! Nice one!\n')
                else:
                    await channel.send(f'{player.name} guessed the audio in {guessThe.guesses} guesses!\n')
            else:
                await message.add_reaction('👎')
                await channel.send(f'{player.name} did not successfully guess the audio.\n')
        else:
            print(f'Ignored message from {message.author}')


    @client.tree.command(name='track', description='Track this text channel for GuessTheGame or GuessTheAudio.')
    @app_commands.describe(guess_the='Choose the GuessThe you want tracked to this channel')
    async def track_command(interaction, guess_the: Literal['GuessTheGame', 'GuessTheAudio', 'All']):
        '''Command to track a text channel'''
        response = ''
        client.server_id = interaction.guild.id
        if guess_the == 'GuessTheGame' or guess_the == 'All':
            if interaction.channel.id != int(client.gtg_text_channel):
                client.gtg_text_channel = f'{interaction.channel.id}'
                print(f'Now tracking channel {client.gtg_text_channel}')
                client.write_json_file()
                response += 'Now tracking this channel for GuessTheGame.\n'
            else:
                print('Tried to change channel tracking to current channel')
                response += 'Already tracking this channel for GuessTheGame.\n'
        if guess_the == 'GuessTheAudio' or guess_the == 'All':
            if interaction.channel.id != int(client.gta_text_channel):
                client.gta_text_channel = f'{interaction.channel.id}'
                print(f'Now tracking channel {client.gta_text_channel}')
                client.write_json_file()
                response += 'Now tracking this channel for GuessTheAudio.\n'
            else:
                print('Tried to change channel tracking to current channel')
                response += 'Already tracking this channel for GuessTheAudio.\n'
        await interaction.response.send_message(response)


    @client.tree.command(name='register', description='Register for GuessTheGame or GuessTheAudio tracking.')
    @app_commands.describe(guess_the='Choose the GuessThe you want to register for')
    async def register_command(interaction, guess_the: Literal['GuessTheGame', 'GuessTheAudio', 'All']):
        '''Command to register a player'''
        response = ''
        if guess_the == 'GuessTheGame' or guess_the == 'All':
            playerFound = False
            for player in client.players:
                if interaction.user.name.strip() == player.name.strip():
                    if player.gtgame.registered:
                        print(f'User {interaction.user.name.strip()} attempted to re-register for tracking GTG')
                        response += 'You are already registered for GuessTheGame tracking!\n'
                    else:
                        print(f'Registering user {interaction.user.name.strip()} for tracking GTG')
                        player.gtgame.registered = True
                        client.write_json_file()
                        response += 'You have been registered for GuessTheGame tracking.\n'
                    playerFound = True
            if not playerFound:
                print(f'Registering user {interaction.user.name.strip()} for tracking GTG')
                player_obj = client.Player(interaction.user.name.strip())
                player_obj.gtgame.registered = True
                client.players.append(player_obj)
                client.write_json_file()
                response += 'You have been registered for GuessTheGame tracking.\n'
        if guess_the == 'GuessTheAudio' or guess_the == 'All':
            playerFound = False
            for player in client.players:
                if interaction.user.name.strip() == player.name.strip():
                    if player.gtaudio.registered:
                        print(f'User {interaction.user.name.strip()} attempted to re-register for tracking GTA')
                        response += 'You are already registered for GuessTheAudio tracking!\n'
                    else:
                        print(f'Registering user {interaction.user.name.strip()} for tracking GTA')
                        player.gtaudio.registered = True
                        client.write_json_file()
                        response += 'You have been registered for GuessTheAudio tracking.\n'
                    playerFound = True
            if not playerFound:
                print(f'Creating player object and registering user {interaction.user.name.strip()} for tracking GTA')
                player_obj = client.Player(interaction.user.name.strip())
                player_obj.gtaudio.registered = True
                client.players.append(player_obj)
                client.write_json_file()
                response += 'You have been registered for GuessTheAudio tracking.\n'
        await interaction.response.send_message(response)


    @client.tree.command(name='deregister', description='Deregister for GuessThe tracking.')
    @app_commands.describe(guess_the='Choose the GuessThe you want to deregister from')
    async def deregister_command(interaction, guess_the: Literal['GuessTheGame', 'GuessTheAudio', 'All']):
        '''Command to deregister a player'''
        players_copy = client.players.copy()
        if guess_the == 'GuessTheGame' or guess_the == 'All':
            for player in players_copy:
                if player.name == interaction.user.name.strip():
                    if player.gtaudio.registered:
                        player.gtgame.registered = False
                    else:
                        client.players.remove(player)
                    client.write_json_file()
                    print(f'Deregistered user {player.name} from GTG')
                    await interaction.response.send_message('You have been deregistered for GuessTheGame tracking.')
                    return
            print(f'Unregistered user {interaction.user.name.strip()} attempted to deregister from GTG')
            await interaction.response.send_message('You were already unregistered for GuessTheGame tracking.')
        if guess_the == 'GuessTheAudio' or guess_the == 'All':
            for player in players_copy:
                if player.name == interaction.user.name.strip():
                    if player.gtgame.registered:
                        player.gtaudio.registered = False
                    else:
                        client.players.remove(player)
                    client.write_json_file()
                    print(f'Deregistered user {player.name} from GTA')
                    await interaction.response.send_message('You have been deregistered for GuessTheAudio tracking.')
                    return
            print(f'Unregistered user {interaction.user.name.strip()} attempted to deregister from GTA')
            await interaction.response.send_message('You were already unregistered for GuessTheAudio tracking.')


    @tasks.loop(seconds = 1)
    async def midnight_call():
        '''Midnight call loop task that is run every minute with a midnight check.'''

        hours, minutes = get_time()
        if client.scored_today and hours == 0 and minutes == 1:
            client.scored_today = False
        if hours != 0 or minutes != 0 or client.scored_today:
            return
        client.scored_today = True

        print('It is midnight, sending daily scoreboard and then mentioning registered players')

        if not client.players:
            return

        gtg_channel = client.get_channel(int(client.gtg_text_channel))
        gta_channel = client.get_channel(int(client.gta_text_channel))
        gtg_shamed = ''
        gta_shamed = ''
        for player in client.players:
            if not player.gtgame.completedToday:
                print(f'{client.users}')
                user = discord.utils.get(client.users, name=player.name)
                if user:
                    gtg_shamed += f'{user.mention} '
                else:
                    print(f'Failed to mention user {player.name}')
            if not player.gtaudio.completedToday:
                print(f'{client.users}')
                user = discord.utils.get(client.users, name=player.name)
                if user:
                    gta_shamed += f'{user.mention} '
                else:
                    print(f'Failed to mention user {player.name}')
        if gtg_shamed != '':
            await gtg_channel.send(f'SHAME ON {gtg_shamed} FOR NOT ATTEMPTING TO GUESS THE GAME!')
            for score in client.tally_gtg_scores():
                await gtg_channel.send(score)
        if gta_shamed != '':
            await gta_channel.send(f'SHAME ON {gta_shamed} FOR NOT ATTEMPTING TO GUESS THE GAME!')
            for score in client.tally_gta_scores():
                await gta_channel.send(score)

        gtg_everyone = ''
        gta_everyone = ''
        for player in client.players:
            player.gtgame.guesses = 0
            player.gtaudio.guesses = 0
            player.gtgame.completedToday = False
            player.gtaudio.completedToday = False
            player.gtgame.succeededToday = False
            player.gtaudio.succeededToday = False
            print(f'{client.users}')
            user = discord.utils.get(client.users, name=player.name)
            if user:
                if player.gtgame.registered:
                    gtg_everyone += f'{user.mention} '
                if player.gtaudio.registered:
                    gta_everyone += f'{user.mention} '
            else:
                print(f'Failed to mention user {player.name}')
        await gtg_channel.send(f'{gtg_everyone}\nIt\'s time to Guess The Game!')
        await gta_channel.send(f'{gta_everyone}\nIt\'s time to Guess The Audio!')


    client.run(discord_token)


if __name__ == '__main__':
    main()
