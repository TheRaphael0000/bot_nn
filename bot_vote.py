#!/usr/bin/env python
import os
import time
from datetime import datetime
import configparser
import asyncio
import aiohttp
import json

#try:
#    import systemd.daemon
#except ModuleNotFoundError:
#    print("Can't find systemd")

import discord
from discordCommands import *

help_msg = """Discord:..."""
N = 10
USE_DEFAULT_BOT_COMMANDS = False
DEBUGGING = True

# processus d'obtention d'un token (appelons-le passeport anonyme pour le grand public ?)
# commande /inscription [position]
#    position: (x, y) sur le drapeau, optionnel si dans le pseudo
# 1) le bot lit la couleur courante, choisit une couleur d'authentification aléatoire
# 2) il demande à l'utilisateur de changer la couleur de son pixel par celle-ci
#    -> msg peut inclure le temps restant avant le prochain batch de vérification
# 3) à la prochaine lecture du drapeau, le bot vérifie s'il y a match
#    -> si match: génère un token
#         (TODO: sauvegarde seulement un hash pour avoir une couche de sécurité => pas de sauvegarde du token)
#    -> si ne match pas: retry sur X lectures de drapeau suivantes (countdown dans la task)

# pour ne pas compliquer inutilement les choses:
# on utilise de l'asynchrone mais en restant single-thread, donc pas besoin de mutex ici
# les requests http sont faites via aiohttp donc ne bloquent pas le thread du bot !

# 'https://admin.fouloscopie.com/users/69e4d888-ba43-4204-bcc0-8347ec89a7bd'

#TODO: trigger a maintenance state when the flag api is down

class DTBPSBot(discord.Client):

	def __init__(self):
		intents = discord.Intents.default()
		intents.members = True
		super().__init__(intents=intents)

		self._flag = None
		self._flag_timestamp = datetime.fromtimestamp(0)
		self._flag_update_errored = False
		self._flag_update_task = None

		self.seen_ppl = set()
		self.commands_to_handle = {} # dictionary holding current commands

	# override (not guaranteed to be called first, nor once)
	async def on_ready(self):
		if DEBUGGING:
			print('bot is ready')

	async def get_author_name(self, author_id):
		async with aiohttp.ClientSession() as session:
			async with session.get(f"https://admin.fouloscopie.com/users/{author_id}") as response:
				if DEBUGGING:
					print("[owner GET response] Status:", response.status)
					print("[owner GET response] Content-type:", response.headers['content-type'])
				if response.status == 200:
					text = await response.text()
					data = json.loads(text).get('data', None) # TODO: add check that parsing worked
					if data:
						return data.get('last_name', None)
		return None

	async def _do_update_flag(self):
		async with aiohttp.ClientSession() as session:
			async with session.get('https://api-flag.fouloscopie.com/flag') as response:
				if DEBUGGING:
					print("[flag GET response] Status:", response.status)
					print("[flag GET response] Content-type:", response.headers['content-type'])
				if response.status == 200:
					self._flag_update_errored = False
					text = await response.text()
					self._flag = json.loads(text) # TODO: add check that parsing worked
				else:
					self._flag_update_errored = True
					self._flag = None # TODO: keep old one but have two timestamps (one for flag data, one for last update try)
				self._flag_timestamp = datetime.now()

	# if no flag update is currently scheduled, schedules one.
	# returns flag if update succeeded.
	async def wait_next_flag_update(self):
		# no pending update -> schedule update
		if not self._flag_update_task:
			# ensure minimum delay after last update
			elapsed = (datetime.now() - self._flag_timestamp).total_seconds()
			sleep_for = UPDATE_FLAG_MIN_DELTA - elapsed
			if sleep_for > 0:
				await asyncio.sleep(sleep_for)
			self._flag_update_task = asyncio.create_task(self._do_update_flag())
		# pending update -> await
		if self._flag_update_task:
			await self._flag_update_task
			self._flag_update_task = None
		return self._flag if not self._flag_update_errored else None

	# if maximum age is given and flag is older than maximum age,
	# the flag data gets updated first.
	# return flag data if no error happens, or None
	async def get_flag(self, maximum_age_in_seconds=None):
		should_update = False
		if self._flag_update_errored or not self._flag:
			should_update = True
		elif maximum_age_in_seconds is not None:
			age = (datetime.now() - self._flag_timestamp).total_seconds()
			if DEBUGGING:
				print("[get_flag] age:", should_update)
			if age > maximum_age_in_seconds:
				should_update = True
		if DEBUGGING:
			print("[get_flag] should_update:", should_update)
		if should_update:
			await self.wait_next_flag_update()
		return self._flag

	# from BotNN, to rework with asyncio
	# def update_lookup(self):
	#     self.mutex.acquire()
	#     members = self.guilds[0].members
	#     self.members_lookup = {}
	#     for m in members:
	#         if m.bot:
	#             continue
	#         dn = m.display_name
	#         pos = parse_name(dn)
	#         if not pos:
	#             continue
	#         self.members_lookup[pos] = m

	#     print(len(self.members_lookup))
	#     self.mutex.release()

	# override
	async def on_message(self, message):
		if message.author == self.user:
			return

		if self.user in self.commands_to_handle:
			# TODO send error ?
			print(f"This user({self.user}) already issued a command that is in process.")
		else:
			result = parse_message(message.author, message.content)
			if result:
				await result.run(self)
				self.commands_to_handle[self.user] = result

		# pour les commandes par défaut de discord.py:
		if USE_DEFAULT_BOT_COMMANDS:
			self.process_commands(message)



def main():
	config = configparser.ConfigParser()
	config.read('settings.ini')
	token = config.get('discord', 'TOKEN', fallback=None)
	if not token:
		print('il faut configurer le token discord dans le fichier settings.ini')

	bot = DTBPSBot()
	try:
		bot.run(token)
	except Exception as e:
		print(e)

if __name__ == "__main__":
	main()

