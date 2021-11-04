#!/usr/bin/env python
import os
import re
import time
from datetime import datetime
import configparser
import asyncio
import aiohttp
import json
import math
import secrets

#try:
#    import systemd.daemon
#except ModuleNotFoundError:
#    print("Can't find systemd")

import discord

help_msg = """Discord:..."""
N = 10
AUTH_TIMEOUT = 190
UPDATE_FLAG_MIN_DELTA = 60
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

    async def on_cmd_inscription(self, message, args):
        # it's a coroutine, the whole thing is here :)
        if message.author.id not in self.seen_ppl:
            await message.author.send("Salutations!")
            self.seen_ppl.add(message.author.id)

        #TODO: prevent concurrent requests...

        user_pos = None
        try:
            user_pos = (int(args[0]), int(args[1]))
        except:
            pseudo = str(message.author.display_name)
            user_pos = parse_name(pseudo)
        if not user_pos:
            await message.author.send(
"""Pour vous authentifier il me faut vos coordonnées!
- soit par argument: /inscription X Y
- soit dans votre pseudo sous la forme [018:006]
""")
            return

        # TODO: make this a function that checks if we can expect an update or not
        if self._flag_update_task or not self._flag:
            await message.author.send("Merci de patienter quelques instants..")

        flag = await self.get_flag()
        if not flag:
            await message.author.send("Ouch! J'ai du mal à accéder au site du drapeau, merci de revenir plus tard.")
            return

        idx_in_flag = flag_coords_to_index(user_pos)
        if idx_in_flag > len(flag):
            await message.author.send("Duh! Ces coordonnées ne semblent pas appartenir au drapeau. Bye!")
            return
        pixel_data = flag[idx_in_flag]
        # no need for the flag anymore, release it
        flag = None

        hex_col = pixel_data['hexColor'].upper() # TODO: check present ?

        # generate auth_color, must be different than hex_col
        auth_color = hex_col
        while auth_color == hex_col:
            auth_color = f"#{secrets.token_hex(3).upper()}"

        author_name = await self.get_author_name(pixel_data['author'])
        if not author_name:
            author_name = "(invalid)"

        await message.author.send(
f"""Pour me prouver ton unicité dirty-biologico-pixelique en tant que "{author_name}", change la couleur de ton pixel avec ce code:
```{auth_color}```Au cas où voilà le lien du drapeau: <https://fouloscopie.com/experiment/7>.
Je reviens dès j'aurai jeté un oeil au drapeau (toutes les {UPDATE_FLAG_MIN_DELTA}s) et que ton pixel aura changé !
""")

        start = datetime.now()
        while (datetime.now() - start).total_seconds() < AUTH_TIMEOUT:
            flag = await self.wait_next_flag_update()
            new_hex_col = flag[idx_in_flag]['hexColor'].upper()
            if new_hex_col == hex_col:
                continue # TODO: display "alive" message if delta was already long enough for the user to change his pixel ?
            elif new_hex_col != auth_color:
                await message.author.send("La couleur de ton pixel a changé mais pas de la bonne couleur :/ Demande annulée.")
                return
            else:
                break
        else:
            await message.author.send("Ton pixel n'a pas pu être vérifié dans le temps imparti. Demande annulée.")
            return

        # better be sure, in case above logic changes
        assert new_hex_col == auth_color

        token = secrets.token_hex(16)

        await message.author.send(
f"""Apparemment c'est bien toi. Voici ton token, ne le partage pas:
```{token} // prototype, ce token ne sera pas utilisable```Si tu le perds, refais la procédure et l'ancien deviendra invalide.
Pour l'utiliser il suffira de me le donner (ou à un autre système peut-être..) en privé lors des sessions de vote.
Tu peux maintenant recoloriser ton pixel comme bon te semble.""")

        # TODO: gen token + maintain json database

    # override
    async def on_message(self, message):
        if message.author == self.user:
            return

        words = re.split(r"\s+", message.content)
        #TODO: use a dict
        if words[0] == "/inscription":
            await self.on_cmd_inscription(message, words[1:])
        elif words[0] == "/echo":
            await message.reply(" ".join(words[1:]))

        # pour les commandes par défaut de discord.py:
        if USE_DEFAULT_BOT_COMMANDS:
            self.process_commands(message)


def parse_name(name):
    m = re.findall("(\d+)[,:;/-](\d+)", name)
    if len(m) < 1:
        return False
    X, Y = m[0]
    pos = max(0, int(X)), max(0, int(Y))
    return pos


# un peu de maths ne font pas de mal
def flag_index_to_coords(index):
    # pattern:
    #  0  1  4  6 12 15
    #  2  3  5  7 13 16
    #  8  9 10 11 14 17
    # 18 ..
    # pattern repeats at each rank X:
    # fill bottom line of size 2 * X L2R
    # fill 2 vertical lines on the right of size (X + 1) L2R T2B
    # this is +4X+2 pixels per rank.
    # computing the starting count of pixels at each rank (== first pixel index)
    # is equivalent to summing an arithmetic sequence
    # this sum equals 2X², so rank 1 starts with 2 pixels rank 2 starts with 8 pixels
    # inversing the equation we can find the rank of a pixel index:
    rank = math.floor(math.sqrt(index / 2)) # 7 gives 1, 8 gives 2 
    # then get the first pixel index
    base = 2 * rank * rank
    # now let's find our index in the inner pattern
    d = index - base
    bline_size = 2 * rank
    if d < bline_size: # pixel in bottom line
        return (d + 1, rank + 1)
    d -= bline_size
    vline_size = rank + 1
    if d < vline_size: # pixel in first vertical line
        return (bline_size + 1, d + 1)
    # pixel in second vertical line
    d -= vline_size
    return (bline_size + 1 + 1, d + 1)


# see flag_index_to_coords for details
def flag_coords_to_index(coords):
    x, y = coords
    # shift coords so that (0, 0) is the origin
    x -= 1
    y -= 1
    # check if pixel is in a bottom line of the pattern
    bline_size = 2 * y # y == rank if bottom line
    if x < bline_size:
        base = 2 * y * y
        return base + x
    # otherwise pixel is in vertical lines
    rank = math.floor(x / 2)
    base = 2 * rank * rank
    idx = base + 2 * rank + y# base + bline_size + y
    if x & 1:
        idx += rank + 1 # vline_size
    return idx


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

