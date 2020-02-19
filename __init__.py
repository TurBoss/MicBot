# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.

import asyncio
import json
import logging
import websockets

from adapt.intent import IntentBuilder
from mycroft import MycroftSkill, intent_handler


logging.basicConfig()


class MicBotSkill(MycroftSkill):
    def __init__(self):
        """ The __init__ method is called when the Skill is first constructed.
        It is often used to declare variables or perform setup actions, however
        it cannot utilise MycroftSkill methods as the class does not yet exist.
        """
        super(MicBotSkill, self).__init__()

        self.users = set()
        self.state = {"value": 0}

        self.learning = True

    def state_event(self):
        return json.dumps({"type": "state", **self.state})

    def users_event(self):
        return json.dumps({"type": "users", "count": len(self.users)})

    async def notify_state(self):
        if self.users:  # asyncio.wait doesn't accept an empty list
            message = self.state_event()
            await asyncio.wait([user.send(message) for user in self.users])

    async def notify_users(self):
        if self.users:  # asyncio.wait doesn't accept an empty list
            message = self.users_event()
            await asyncio.wait([user.send(message) for user in self.users])

    async def register(self, websocket):
        self.users.add(websocket)
        await self.notify_users()

    async def unregister(self, websocket):
        self.users.remove(websocket)
        await self.notify_users()

    async def counter(self, websocket, path):
        # register(websocket) sends user_event() to websocket
        await self.register(websocket)
        try:
            await websocket.send(self.state_event())
            async for message in websocket:
                data = json.loads(message)
                if data["action"] == "minus":
                    self.state["value"] -= 1
                    await self.notify_state()
                elif data["action"] == "plus":
                    self.state["value"] += 1
                    await self.notify_state()
                else:
                    logging.error("unsupported event: {}", data)
        finally:
            await self.unregister(websocket)

    def initialize(self):
        """ Perform any final setup needed for the skill here.
        This function is invoked after the skill is fully constructed and
        registered with the system. Intents will be registered and Skill
        settings will be available."""
        my_setting = self.settings.get('my_setting')

        loop = asyncio.new_event_loop()

        start_server = websockets.serve(self.counter, "0.0.0.0", 8765, loop=loop)
        loop.run_until_complete(start_server)
        loop.run_forever()

    @intent_handler(IntentBuilder('ThankYouIntent').require('ThankYouKeyword'))
    def handle_thank_you_intent(self, message):
        """ This is an Adapt intent handler, it is triggered by a keyword."""
        self.speak_dialog("welcome")

    @intent_handler('HowAreYou.intent')
    def handle_how_are_you_intent(self, message):
        """ This is a Padatious intent handler.
        It is triggered using a list of sample phrases."""
        self.speak_dialog("how.are.you")

    @intent_handler(IntentBuilder('HelloWorldIntent')
                    .require('HelloWorldKeyword'))
    def handle_hello_world_intent(self, message):
        """ Skills can log useful information. These will appear in the CLI and
        the skills.log file."""
        self.log.info("There are five types of log messages: "
                      "info, debug, warning, error, and exception.")
        self.speak_dialog("hello.world")

    def stop(self):
        pass


def create_skill():
    return MicBotSkill()
