#!/usr/bin/env python

import os
import re

import time
import threading

import discord
from dotenv import load_dotenv


help_msg = """/nn
GitHub : http://github.com/TheRaphael0000/bot_nn"""
N = 10
UPDATE_LOOKUP_DELTA = 120


class BotNN(discord.Client):

    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents)
        self.members_lookup = {}

    async def on_ready(self):
        x = threading.Thread(target=self.threading_loop, daemon=True)
        x.start()

    def threading_loop(self):
        while True:
            self.update_lookup()
            time.sleep(UPDATE_LOOKUP_DELTA)

    def update_lookup(self):
        members = self.guilds[0].members
        self.members_lookup = {}
        for m in members:
            if m.bot:
                continue
            dn = m.display_name
            pos = parse_name(dn)
            if not pos:
                continue
            self.members_lookup[pos] = m

        print(len(self.members_lookup))

    async def on_message(self, message):
        if message.author == self.user:
            return

        words = re.split(r"\s+", message.content)
        if words[0] == "/nn":
            name = str(message.author.display_name)
            my_pos = parse_name(name)
            if not my_pos:
                await message.reply("Affiche ta coordonnée dans ton pseudo. Example : _[018:006] TheRaphael0000_")
                return

            valid = []

            poss = list(self.members_lookup.keys())
            for pos in poss:
                d = manhattan_distance(pos, my_pos)
                if d < N and pos != my_pos:
                    valid.append((self.members_lookup[pos], d))

            valid.sort(key=lambda x: x[-1])

            if len(valid) <= 0:
                await message.reply("Tu n'as pas de voisins sur ce serveur .-.")
                return

            msg = "```Pseudo,Distance\n"
            for v, d in valid:
                msg += f"{str(v.display_name)},{d}\n"
            msg += "```"

            await message.reply(msg)


def manhattan_distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def parse_name(name):
    m = re.findall("(\d+)[,:;/-](\d+)", name)
    if len(m) < 1:
        return False
    X, Y = m[0]
    pos = max(0, int(X)), max(0, int(Y))
    return pos


def main():
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    bot = BotNN()
    try:
        bot.run(token)
    except Exception as e:
        bot.close()


if __name__ == "__main__":
    main()
