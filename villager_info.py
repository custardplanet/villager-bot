import requests
import sqlite3
import logging
import datetime
import json
import difflib
from logging.handlers import TimedRotatingFileHandler

from irc import IRC


class VillagerInfo:

    def __init__(self, config):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        handler = TimedRotatingFileHandler(filename='logs/villager_info.log', when='midnight')
        handler.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(handler)
        logger.addHandler(ch)
        self.logger = logger

        self.config = config

        with open('final_villager_info.json') as f:
            villagers = json.load(f)

        self.villagers = villagers[0]
        self.cooldowns = {}

    def connect(self):
        conn = sqlite3.connect(self.config['db'])
        cursor = conn.cursor()

        cursor.execute('CREATE TABLE IF NOT EXISTS channels (username text)')
        cursor.execute('SELECT username FROM channels')
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        channels = [row[0] for row in rows]
        channels = set(channels)
        channels.add('isabellesays')

        irc = IRC()
        irc.connect(self.config['server'],
                    self.config['port'],
                    channels,
                    self.config['nick'],
                    self.config['oauth'])
        self.irc = irc

    def say_bday(self, channel, command, sent_time):
        sent_time = datetime.datetime.fromtimestamp(sent_time / 1000)

        tokens = command.split(None, 1);
        if len(tokens) < 2:
            self.irc.privmsg(channel, 'Usage: !vbday <birthday>\n '
                                      'for example: !vbday January 5th')
            return

        samebday = list()
        for i in self.villagers:
            if i['birthday'] == tokens[1]:
                samebday.append(i['name'])

        if len(samebday) == 0:
            self.irc.privmsg(channel, "I'm sorry, no villagers have that brithday")
        elif len(samebday) == 1:
            self.irc.privmsg(channel, "You share a birthday with the villagers " + samebday[0] + ".")
        elif len(samebday) == 2:
            self.irc.privmsg(channel,
                             "You share a birthday with the villagers " + samebday[0] + ", and " + samebday[1] + ".")

    def say_info(self, channel, command, sent_time):
        sent_time = datetime.datetime.fromtimestamp(sent_time / 1000)

        tokens = command.split(None, 1)
        if len(tokens) < 2:
            self.irc.privmsg(channel,
                             'Usage: !villager <villager name>')
            return

        villager_name = tokens[1].lower().replace(' ', '_')

        if villager_name not in self.villagers:
            message = 'Couldn\'t find the specified villager :('

            villagers = self.villagers.keys()
            match = difflib.get_close_matches(villager_name, villagers, n=1)
            if match:
                message += f" did you mean {self.villagers[match[0]]['name']}?"

            self.irc.privmsg(channel, message)
            response_time = datetime.datetime.now() - sent_time
            self.logger.info(f'{channel} - {response_time.total_seconds()} - {tokens[1]} - {villager_name} - NOT FOUND')
            return

        if channel not in self.cooldowns:
            cooldown = datetime.datetime.now() + datetime.timedelta(seconds=5)
            self.cooldowns[channel] = {villager_name: cooldown}
        elif channel in self.cooldowns and villager_name in self.cooldowns[channel]:
            if self.cooldowns[channel][villager_name] > datetime.datetime.now():
                self.logger.info(f'{channel} - ON COOLDOWN - {villager_name}')
                return
            else:
                del self.cooldowns[channel][villager_name]
        elif channel in self.cooldowns and villager_name not in self.cooldowns[channel]:
            cooldown = datetime.datetime.now() + datetime.timedelta(seconds=5)
            self.cooldowns[channel][villager_name] = cooldown

        # clean up cooldowns
        if channel in self.cooldowns:
            for villager in list(self.cooldowns[channel]):
                if self.cooldowns[channel][villager] <= datetime.datetime.now():
                    del self.cooldowns[channel][villager]

        info = self.villagers[villager_name]
        message = f"{info['name']} is a {info['personality'].lower()} {info['species'].lower()}, {info['phrase']}! More info: {info['link']}"
        self.irc.privmsg(channel, message)
        response_time = datetime.datetime.now() - sent_time
        self.logger.info(f'{channel} - {response_time.total_seconds()} - {info["name"]}')

    def handle_add(self, username):
        conn = sqlite3.connect(self.config['db'])
        cursor = conn.cursor()

        cursor.execute('SELECT username FROM channels')
        rows = cursor.fetchall()
        channels = [row[0] for row in rows]

        if username in channels:
            self.irc.privmsg('isabellesays', f'I am already in your channel, {username}')
            self.logger.info(f'{username} - ALREADY JOINED')
            return

        cursor.execute('INSERT INTO channels VALUES (?)', (username,))
        conn.commit()

        cursor.close()
        conn.close()

        self.irc.send(f'JOIN #{username}')
        self.irc.privmsg('isabellesays', f'I have joined your channel, {username}')
        self.logger.info(f'{username} - JOINED')

    def handle_remove(self, username):
        conn = sqlite3.connect(self.config['db'])
        cursor = conn.cursor()

        cursor.execute('DELETE FROM channels WHERE username = (?)', (username,))
        conn.commit()

        cursor.close()
        conn.close()

        self.irc.send(f'PART #{username}')
        self.irc.privmsg('isabellesays', f'I have left your channel, @{username}')
        self.logger.info(f'{username} - LEFT')

    def handle_help(self):
        self.irc.privmsg('isabellesays', 'Please see the panels below for usage details!')
        self.logger.info(f'HELPED')

    def run_forever(self):
        self.connect()

        while True:
            try:
                events = self.irc.read_events()
            except RuntimeError:
                self.connect()
                continue

            for event in events:
                if (event['code'] == 'PRIVMSG' and
                        event['message'].startswith('!villager')):
                    self.say_info(event['channel'][1:],
                                  event['message'],
                                  int(event['tags']['tmi-sent-ts']))

                elif (event['code'] == 'PRIVMSG' and
                      event['channel'][1:] == 'isabellesays' and
                      event['message'].startswith('!help')):
                    self.handle_help()

                elif (event['code'] == 'PRIVMSG' and
                      event['channel'][1:] == 'isabellesays' and
                      event['message'].startswith('!join')):
                    self.handle_add(event['tags']['display-name'].lower())

                elif (event['code'] == 'PRIVMSG' and
                      event['channel'][1:] == 'isabellesays' and
                      event['message'].startswith('!leave')):
                    self.handle_remove(event['tags']['display-name'].lower())

                elif (event['code'] == 'PRIVMSG' and
                      event['channel'][1:] == 'isabellesays' and
                      event['message'].startswith('!vbday')):
                    self.say_bday(event['channel'][1:],
                                  event['message'],
                                  int(event['tags']['tmi-sent-ts']))
