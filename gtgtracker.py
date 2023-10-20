'''Written by Cael Shoop.'''

import os
import json
import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()
JSON_FOLDER = 'json\\'
JSON_EXT = '.json'


def main():
    '''Main function'''
    class GTGClient(discord.Client):
        '''Custom client class for GuessTheGame bot'''
        def __init__(self, intents):
            self.text_channel = 0
            self.is_first_call = True
            super(GTGClient, self).__init__(intents=intents)


        class PlayerClass:
            '''Player template for storing player info'''
            def __init__(self, name, win_count, score_today,
                         completed_today = False, succeeded_today = False):
                self.name = name
                self.win_count = win_count
                self.score_today = score_today
                self.completed_today = completed_today
                self.succeeded_today = succeeded_today
                self.players = []


        async def on_ready(self):
            '''Client on_ready event'''
            await tree.sync()
            self.read_json_file()
            if not midnight_call.is_running():
                midnight_call.start()
            print(f'{self.user} has connected to Discord!')


        async def on_message(self, message):
            '''Client on_message event'''
            # message is from this bot
            if message.author == self.user:
                return

            # someone posts their GTG results
            channel = self.get_channel(int(self.text_channel))
            if '#GuessTheGame' in message.content:
                user = discord.utils.get(self.users, name=message.author.name)
                # there are no registered players
                if not self.players:
                    await channel.send(f'{user.mention}, there are no registered players! '
                                'Please register and resend your results to be the first.')
                    return

                # player is not registered
                found = False
                for player_it in self.players:
                    if message.author.name == player_it.name:
                        found = True
                if not found:
                    await channel.send(f'{message.author.name}, you are not registered! '
                                                'Please register and resend your results.')

                unplayed = ''
                player = self.players[0]
                found = False
                for player_it in self.players:
                    if message.author.name == player_it.name:
                        found = True
                        player = player_it
                    elif not player_it.completed:
                        unplayed_user = discord.utils.get(self.users, name=player_it.name)
                        unplayed += f'{unplayed_user.mention} '
                if not found:
                    print('Unregistered player posted a result')
                    await channel.send(f'Unregistered user {user.mention} attempted to post '
                                'a result. Please register with "/register" and try again.')
                    return
                print(f'Received GTG message from {message.author}')

                # player has already sent results
                if player.completed:
                    await channel.send(f'{player.name}, you have already submitted your '
                                        'results today.')
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
                print(f'Player {player.name} got a score of {player.score_today}')

                self.write_json_file()

                if player.success:
                    await message.add_reaction('👍')
                    if player.wins == 1:
                        if player.score == 1:
                            await channel.send(f'{player.name} (1 win) guessed the game in '
                                                '1 guess!\n')
                        else:
                            await channel.send(f'{player.name} (1 win) guessed the game in '
                                               f'{player.score} guesses!\n')
                    else:
                        if player.score == 1:
                            await channel.send(f'{player.name} ({player.wins} wins) guessed '
                                                'the game in 1 guess!\n')
                        else:
                            await channel.send(f'{player.name} ({player.wins} wins) guessed '
                                               f'the game in {player.score} guesses!\n')
                else:
                    await message.add_reaction('👎')
                    if player.wins == 1:
                        await channel.send(f'{player.name} (1 win) did not successfully '
                                            'guess the game.\n')
                    else:
                        await channel.send(f'{player.name} ({player.wins} wins) did not '
                                            'successfully guess the game.\n')

                if unplayed == '':
                    for score in self.tally_scores():
                        await channel.send(score)
                else:
                    unplayed += 'Guess The Game!'
                    await channel.send(unplayed)
            else:
                print(f'Ignored message from {message.author}')


        async def track_command(self, interaction):
            '''Command to track a text channel'''
            if interaction.channel.id != int(self.text_channel):
                self.text_channel = f'{interaction.channel.id}\n'
                print(f'Now tracking channel {self.text_channel}', end='')
                self.write_json_file()
                os.putenv('TEXT_CHANNEL', self.text_channel)
                await interaction.response.send_message('Now tracking this channel.')
            else:
                print('Tried to change channel tracking to current channel')
                await interaction.response.send_message('Already tracking this channel.')


        async def register_command(self, interaction):
            '''Command to register a player'''
            for player in self.players:
                if interaction.user.name.strip() == player.name.strip():
                    print(f'User {interaction.user.name.strip()} attempted to '
                           're-register for tracking')
                    await interaction.response.send_message('You are already registered '
                                                            'for GuessTheGame tracking!')
                    return

            print(f'Registering user {interaction.user.name.strip()} for tracking')
            player_obj = self.PlayerClass(interaction.user.name.strip(), 0, 0)
            self.players.append(player_obj)
            self.write_json_file()
            await interaction.response.send_message('You have been registered '
                                                    'for GuessTheGame tracking.')


        async def deregister_command(self, interaction):
            '''Command to deregister a player'''
            removed = False
            players_copy = self.players.copy()
            for player in players_copy:
                if player.name == interaction.user.name.strip():
                    self.players.remove(player)
                    self.write_json_file()
                    print(f'Deregistered user {player.name}')
                    await interaction.response.send_message('You have been '
                                            'deregistered for GuessTheGame tracking.')
                    removed = True
            if not removed:
                print(f'Unregistered user {interaction.user.name.strip()} attempted to deregister')
                await interaction.response.send_message('You were already '
                                            'unregistered for GuessTheGame tracking.')


        async def midnight_call(self):
            '''
            Midnight call task that is run at start and every 20 hours after that.
            My server restarts at 4am which, paired with it ignoring the first time it runs,
            means the midnight call occurs at midnight.
            '''
            if not self.players:
                return
            if self.is_first_call:
                self.is_first_call = False
                return

            channel = client.get_channel(int(self.text_channel))
            shamed = ''
            for player in self.players:
                if not player.completed:
                    user = discord.utils.get(client.users, name=player.name)
                    shamed += f'{user.mention} '
            if shamed != '':
                await channel.send(f'SHAME ON {shamed} FOR NOT ATTEMPTING TO GUESS THE GAME!')
                self.tally_scores()

            everyone = ''
            for player in self.players:
                player.completed = False
                user = discord.utils.get(client.users, name=player.name)
                everyone += f'{user.mention} '
            await channel.send(f'{everyone} it\'s time to Guess The Game!')


        def read_json_file(self):
            '''Reads player information from the json file and puts it in the players list'''
            # TODO: confirm self.guild.id functionality
            file_path = JSON_FOLDER + str(self.guild.id) + JSON_EXT
            if not os.path.exists(file_path):
                return
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                for player_name, player_data in data.items():
                    if player_name == 'text_channel':
                        self.text_channel = player_data
                    else:
                        print(f'Loading data for {player_name}')
                        load_player = self.PlayerClass(player_name,
                                                       player_data['win_count'],
                                                       player_data['score'],
                                                       player_data['completed_today'],
                                                       player_data['succeeded_today'])
                        self.players.append(load_player)
                        print(f'Loaded player {load_player.name} - '
                              f'win count: {load_player.win_count}, '
                              f'score today: {load_player.score_today}, '
                              f'completed today: {load_player.completed_today}, '
                              f'succeeded today: {load_player.succeeded_today}')

                print(f'Successfully loaded {file_path}')


        def write_json_file(self):
            '''Writes player information from the players list to the json file'''
            # TODO: confirm self.guild.id functionality
            file_name = JSON_FOLDER + str(self.guild.id) + JSON_EXT
            with open(file_name, 'w+', encoding='utf-8') as file:
                data = {}
                data['text_channel'] = self.text_channel
                for player in self.players:
                    data[player.name] = {'win_count': player.win_count,
                                         'score_today': player.score_today,
                                         'completed_today': player.completed_today,
                                         'succeeded_today': player.succeeded_today}
                    print(f'{player.name} json data: {data[player.name]}')
                json_data = json.dumps(data)
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
                print(f'{place_counter}. {player.name} ({player.wins} wins) with score '
                      f'of {player.score}')
                if player in winners:
                    player.wins += 1
                    if player.wins == 1:
                        if player.score == 1:
                            results.append(f'1. {player.name} (1 win) wins by '
                                            'guessing the game in ONE GUESS! NICE ONE!\n')
                        else:
                            results.append(f'1. {player.name} (1 win) wins by '
                                           f'guessing the game in {player.score} guesses!\n')
                    else:
                        if player.score == 1:
                            results.append(f'1. {player.name} ({player.wins} wins) '
                                            'wins by guessing the game in ONE GUESS! NICE ONE!\n')
                        else:
                            results.append(f'1. {player.name} ({player.wins} wins) wins '
                                           f'by guessing the game in {player.score} guesses!\n')
                elif player.success:
                    if player.wins == 1:
                        results.append(f'{place_counter}. {player.name} (1 win) '
                                       f'guessed the game in {player.score} guesses.\n')
                    else:
                        results.append(f'{place_counter}. {player.name} ({player.wins} wins) '
                                       f'guessed the game in {player.score} guesses.\n')
                else:
                    if player.wins == 1:
                        results.append(f'{player.name} (1 win) did not successfully '
                                        'guess the game.\n')
                    else:
                        results.append(f'{player.name} ({player.wins} wins) did not '
                                        'successfully guess the game.\n')
                place_counter += 1
                player.score = 0
                player.completed = False
                player.success = False

            self.write_json_file()

            return results



    discord_token = os.getenv('DISCORD_TOKEN')

    intents = discord.Intents.default()
    intents.message_content = True

    client = GTGClient(intents=intents)
    tree = app_commands.CommandTree(client)
    client.run(discord_token)

    @tree.command(name='track', description='Track this text channel.')
    async def track_command(interaction):
        client.track_command(interaction)

    @tree.command(name='register', description='Register for GuessTheGame tracking.')
    async def register_command(interaction):
        client.register_command(interaction)

    @tree.command(name='deregister', description='Deregister for GuessTheGame tracking.')
    async def deregister_command(interaction):
        client.deregister_command(interaction)

    @tasks.loop(hours=20)
    async def midnight_call():
        client.midnight_call()


if __name__ == '__main__':
    main()
