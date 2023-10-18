# GTGTracker
Discord bot to track our wins on https://guessthe.game.


### This bot can only work on one server at a time due to how it saves players and their wins/scores.
I run it on my personal server which restarts daily at 4am, hence the 20 hour delay before running the midnight function.


### You need a .env file in the directory!
.env requires:

* DISCORD_TOKEN (must be set manually)
* TEXT_CHANNEL (can be set with /track in the desired text channel)
* SERVER_ID (must be set manually)


### Slash commands
Currently supported slash commands are:

* /track (sets the TEXT_CHANNEL in the .env to that channel's ID)
* /register (registers a player)
* /deregister (deregisters a player. WARNING: their wins will be permanently lost)
