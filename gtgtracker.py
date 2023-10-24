'''Written by Cael Shoop.'''

import os
import json
import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv


load_dotenv()

def main():
    '''Main function'''
    class GTGClient(discord.Client):
        '''Custom client class for GuessTheGame bot'''

        FILE_PATH = 'info.json'

        def __init__(self, intents):
            super(GTGClient, self).__init__(intents=intents)
            self.text_channel = 0
            self.server_id = 0
            self.players = []
            self.tree = app_commands.CommandTree(self)


        class PlayerClass:
            '''Player template for storing player info'''
            def __init__(self, name, win_count, score_today,
                         completed_today = False, succeeded_today = False):
                self.name = name
                self.win_count = win_count
                self.score_today = score_today
                self.completed_today = completed_today
                self.succeeded_today = succeeded_today


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
                for first_field, second_field in data.items():
                    if first_field == 'text_channel':
                        self.text_channel = second_field
                        print(f'Got text channel id of {self.text_channel}')
                    else:
                        print(f'Loading data for {first_field}')
                        load_player = self.PlayerClass(first_field,
                                                       second_field['win_count'],
                                                       second_field['score_today'],
                                                       second_field['completed_today'],
                                                       second_field['succeeded_today'])
                        self.players.append(load_player)
                        print(f'Loaded player {load_player.name} - '
                              f'win count: {load_player.win_count}, '
                              f'score today: {load_player.score_today}, '
                              f'completed today: {load_player.completed_today}, '
                              f'succeeded today: {load_player.succeeded_today}')

                print(f'Successfully loaded {self.FILE_PATH}')


        def write_json_file(self):
            '''Writes player information from the players list to the json file'''
            data = {}
            data['text_channel'] = self.text_channel
            for player in self.players:
                data[player.name] = {'win_count': player.win_count,
                                        'score_today': player.score_today,
                                        'completed_today': player.completed_today,
                                        'succeeded_today': player.succeeded_today}
                print(f'{player.name} json data: {data[player.name]}')
            json_data = json.dumps(data)
            print(f'Writing {self.FILE_PATH}')
            with open(self.FILE_PATH, 'w+', encoding='utf-8') as file:
                file.write(json_data)


        def get_score(self, player):
            '''Returns the player's score for sorting purposes'''
            return player.score_today


        def tally_scores(self):
            '''Sorts players and returns a list of strings to send as Discord messages'''
            if not self.players:
                print('No players to score')
                return

            print('Tallying scores')
            winners = [] # list of winners - the one/those with the lowest score
            results = [] # list of strings - the scoreboard to print out
            results.append('\nGUESSING COMPLETE!\n\n**SCOREBOARD:**\n')

            # sort the players
            self.players.sort(key=self.get_score)
            if self.players[0].succeeded_today:
                # if the player(s) with the lowest score successfully
                # guessed the game, they are the first winner
                first_winner = self.players[0]
                winners.append(first_winner)
                # for the rest of the players, check if they're tied
                for player_it in self.players[1:]:
                    if player_it.score_today == first_winner.score:
                        winners.append(player_it)
                    else:
                        break

            place_counter = 1
            for player in self.players:
                print(f'{place_counter}. {player.name} ({player.win_count} wins) with score '
                      f'of {player.score_today}')
                if player in winners:
                    player.win_count += 1
                    if player.win_count == 1:
                        if player.score_today == 1:
                            results.append(f'1. {player.name} (1 win) wins by '
                                            'guessing the game in ONE GUESS! NICE ONE!\n')
                        else:
                            results.append(f'1. {player.name} (1 win) wins by '
                                           f'guessing the game in {player.score_today} guesses!\n')
                    else:
                        if player.score_today == 1:
                            results.append(f'1. {player.name} ({player.win_count} wins) '
                                            'wins by guessing the game in ONE GUESS! NICE ONE!\n')
                        else:
                            results.append(f'1. {player.name} ({player.win_count} wins) wins '
                                           f'by guessing the game in {player.score_today} guesses!\n')
                elif player.succeeded_today:
                    if player.win_count == 1:
                        results.append(f'{place_counter}. {player.name} (1 win) '
                                       f'guessed the game in {player.score_today} guesses.\n')
                    else:
                        results.append(f'{place_counter}. {player.name} ({player.win_count} wins) '
                                       f'guessed the game in {player.score_today} guesses.\n')
                else:
                    if player.win_count == 1:
                        results.append(f'{player.name} (1 win) did not successfully '
                                        'guess the game.\n')
                    else:
                        results.append(f'{player.name} ({player.win_count} wins) did not '
                                        'successfully guess the game.\n')
                place_counter += 1
                player.score_today = 0
                player.completed_today = False
                player.succeeded_today = False

            self.write_json_file()

            return results



    discord_token = os.getenv('DISCORD_TOKEN')

    intents = discord.Intents.all()

    client = GTGClient(intents=intents)

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

        # someone posts their GTG results
        channel = client.get_channel(int(client.text_channel))
        if '#GuessTheGame' in message.content:
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

            unplayed = ''
            player = client.players[0]
            found = False
            for player_it in client.players:
                if message.author.name == player_it.name:
                    found = True
                    player = player_it
                elif not player_it.completed_today:
                    unplayed_user = discord.utils.get(client.users, name=player_it.name)
                    unplayed += f'{unplayed_user.mention} '
            if not found:
                print('Unregistered player posted a result')
                await channel.send(f'Unregistered user {user.mention} attempted to post '
                            'a result. Please register with "/register" and try again.')
                return
            print(f'Received GTG message from {message.author}')

            # player has already sent results
            if player.completed_today:
                print(f'{player.name} tried to resubmit results')
                await channel.send(f'{player.name}, you have already submitted your '
                                    'results today.')
                return

            result = message.content.splitlines()[2].replace(' ', '')[1:]
            print('Result line: ' + result)
            player.completed_today = True
            player.score_today = 0
            for char in result:
                if char == '🟥':
                    player.score_today += 1
                elif char == '🟩':
                    player.score_today += 1
                    player.succeeded_today = True
                    break
            print(f'Player {player.name} got a score of {player.score_today}')

            client.write_json_file()

            if player.succeeded_today:
                await message.add_reaction('👍')
                if player.win_count == 1:
                    if player.score_today == 1:
                        await channel.send(f'{player.name} (1 win) guessed the game in '
                                            '1 guess!\n')
                    else:
                        await channel.send(f'{player.name} (1 win) guessed the game in '
                                            f'{player.score_today} guesses!\n')
                else:
                    if player.score_today == 1:
                        await channel.send(f'{player.name} ({player.win_count} wins) guessed '
                                            'the game in 1 guess!\n')
                    else:
                        await channel.send(f'{player.name} ({player.win_count} wins) guessed '
                                            f'the game in {player.score_today} guesses!\n')
            else:
                await message.add_reaction('👎')
                if player.win_count == 1:
                    await channel.send(f'{player.name} (1 win) did not successfully '
                                        'guess the game.\n')
                else:
                    await channel.send(f'{player.name} ({player.win_count} wins) did not '
                                        'successfully guess the game.\n')

            if unplayed == '':
                for score in client.tally_scores():
                    await channel.send(score)
            else:
                unplayed += 'Guess The Game!'
                await channel.send(unplayed)
        else:
            print(f'Ignored message from {message.author}')


    @client.tree.command(name='track', description='Track this text channel.')
    async def track_command(interaction):
        '''Command to track a text channel'''
        client.server_id = interaction.guild.id
        if interaction.channel.id != int(client.text_channel):
            client.text_channel = f'{interaction.channel.id}\n'
            print(f'Now tracking channel {client.text_channel}', end='')
            client.write_json_file()
            os.putenv('TEXT_CHANNEL', client.text_channel)
            await interaction.response.send_message('Now tracking this channel.')
        else:
            print('Tried to change channel tracking to current channel')
            await interaction.response.send_message('Already tracking this channel.')


    @client.tree.command(name='register', description='Register for GuessTheGame tracking.')
    async def register_command(interaction):
        '''Command to register a player'''
        for player in client.players:
            if interaction.user.name.strip() == player.name.strip():
                print(f'User {interaction.user.name.strip()} attempted to '
                        're-register for tracking')
                await interaction.response.send_message('You are already registered '
                                                        'for GuessTheGame tracking!')
                return

        print(f'Registering user {interaction.user.name.strip()} for tracking')
        player_obj = client.PlayerClass(interaction.user.name.strip(), 0, 0)
        client.players.append(player_obj)
        client.write_json_file()
        await interaction.response.send_message('You have been registered '
                                                'for GuessTheGame tracking.')


    @client.tree.command(name='deregister', description='Deregister for GuessTheGame tracking.')
    async def deregister_command(interaction):
        '''Command to deregister a player'''
        removed = False
        players_copy = client.players.copy()
        for player in players_copy:
            if player.name == interaction.user.name.strip():
                client.players.remove(player)
                client.write_json_file()
                print(f'Deregistered user {player.name}')
                await interaction.response.send_message('You have been '
                                        'deregistered for GuessTheGame tracking.')
                removed = True
        if not removed:
            print(f'Unregistered user {interaction.user.name.strip()} attempted to deregister')
            await interaction.response.send_message('You were already '
                                        'unregistered for GuessTheGame tracking.')


    @tasks.loop(hours=24)
    async def midnight_call():
        '''Midnight call loop task that is run every 24 hours.'''
        if not client.players:
            return

        channel = client.get_channel(int(client.text_channel))
        shamed = ''
        for player in client.players:
            if not player.completed_today:
                print(f'{client.users}')
                user = discord.utils.get(client.users, name=player.name)
                if user:
                    shamed += f'{user.mention} '
                else:
                    print(f'Failed to mention user {player.name}')
        if shamed != '':
            await channel.send(f'SHAME ON {shamed} FOR NOT ATTEMPTING TO GUESS THE GAME!')
            client.tally_scores()

        everyone = ''
        for player in client.players:
            player.completed_today = False
            print(f'{client.users}')
            user = discord.utils.get(client.users, name=player.name)
            if user:
                everyone += f'{user.mention} '
            else:
                print(f'Failed to mention user {player.name}')
        await channel.send(f'{everyone}\nIt\'s time to Guess The Game!')


    client.run(discord_token)


if __name__ == '__main__':
    main()
