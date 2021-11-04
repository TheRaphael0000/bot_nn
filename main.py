#!/usr/bin/env python

try:
    import systemd.daemon
except ModuleNotFoundError:
    print("Can't find systemd")

import os
import re
from threading import Thread, Lock
import time

import discord
from dotenv import load_dotenv

from region import name_to_region
import neighbours


LOOP_FREQUENCY = 120

MSG_HELP = f"""
Ce bot permet d'en savoir plus sur votre région et vos voisins.

GitHub  : http://github.com/TheRaphael0000/bot_nn
"""


class BotRegion(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents)

        self.all_regions = {}
        self.mutex = Lock()

        try:
            systemd.daemon.notify("READY=1")
        except NameError:
            pass

    async def on_ready(self):
        thread = Thread(target=self.threading_loop, daemon=True)
        thread.start()

    def threading_loop(self):
        while True:
            self.update_regions()
            time.sleep(LOOP_FREQUENCY)

    def update_regions(self):
        self.all_regions = []

        self.mutex.acquire()
        members = self.guilds[0].members
        for member in members:
            display_name = member.display_name
            region = name_to_region(display_name)
            if not region:
                continue

            self.all_regions.append(region)
        self.mutex.release()

        print(len(self.all_regions))

    async def on_message(self, message):
        if message.author == self.user:
            return

        display_name = str(message.author.display_name)
        content = re.split(r"\s+", message.content)
        command, *args = content
        answer = []

        if command == "/voisins" or command == "/nn" or command == "/voisin":
            answer = neighbours.execute(self.mutex, self.all_regions, display_name, args)
            await message.reply("\n".join(answer))


def main():
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    bot = BotRegion()
    try:
        bot.run(token)
    finally:
        bot.close()


if __name__ == "__main__":
    main()
