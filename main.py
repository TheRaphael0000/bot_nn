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

from Region import Region
from Neighbours import Neighbours


LOOP_FREQUENCY = 120

MSG_HELP = [
    "Ce bot permet d'en savoir plus sur votre région et vos voisins.",
    "",
    Neighbours.get_description(),
    "",
    "GitHub  : http://github.com/TheRaphael0000/bot_nn"
]

MSG_TRUNCATED = "..."
MSG_MAX_LENGTH = 2000 - 6 - len(MSG_TRUNCATED)


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
            region = Region(display_name)
            if region.is_empty():
                continue

            self.all_regions.append(region)
        self.mutex.release()

        print(len(self.all_regions))

    async def on_message(self, message):
        author = message.author
        if author == self.user:
            return
        display_name = author.display_name

        content = message.content
        content = re.split(r"\s+", content)
        command, *args = content

        answer = []
        if command in ["/nn", "/voisins"]:
            answer = Neighbours.execute(self.mutex, self.all_regions,
                                        display_name, args)
        if command == "/help":
            answer = MSG_HELP

        if len(answer) > 0:
            if isinstance(answer, list):
                answer = "\n".join(answer)
            if len(answer) > MSG_MAX_LENGTH:
                answer = answer[:MSG_MAX_LENGTH]
                answer += MSG_TRUNCATED
            await message.reply(f"```{answer}```")
        return


def main():
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    bot = BotRegion()
    bot.run(token)


if __name__ == "__main__":
    main()
