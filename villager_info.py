import requests
import sqlite3
from irc import IRC


class VillagerInfo:

    def __init__(self, config):
        self.config = config

        conn = sqlite3.connect('villagerinfo.db')
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
        irc.connect(config['server'],
            config['port'],
            channels,
            config['nick'],
            config['oauth'])
        self.irc = irc

    def say_info(self, channel, command):
        tokens = command.split()
        if len(tokens) < 2:
            self.irc.privmsg(channel,
                'Usage: !villager <villager name>')
            return

        villager_name = tokens[1]
        headers = {'X-API-KEY': self.config['nookipedia_api_key']}
        url = f'https://nookipedia.com/api/villager/{villager_name}/'

        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            self.irc.privmsg(channel, 'Couldn\'t find the specified villager :(')
            return

        info = r.json()
        message = f"{info['name']} is a {info['personality'].lower()} {info['species'].lower()}, {info['phrase']}! More info: {info['link']}"
        self.irc.privmsg(channel, message)

    def handle_add(self, username):
        conn = sqlite3.connect('villagerinfo.db')
        cursor = conn.cursor()

        cursor.execute('SELECT username FROM channels')
        rows = cursor.fetchall()
        channels = [row[0] for row in rows]

        if username in channels:
            self.irc.privmsg('isabellesays', f'I am already in your channel, {username}')
            return

        cursor.execute('INSERT INTO channels VALUES (?)', (username,))
        conn.commit()

        cursor.close()
        conn.close()

        self.irc.send(f'JOIN #{username}')
        self.irc.privmsg('isabellesays', f'I have joined your channel, {username}')

    def handle_remove(self, username):
        conn = sqlite3.connect('villagerinfo.db')
        cursor = conn.cursor()

        cursor.execute('DELETE FROM channels WHERE username = (?)', (username,))
        conn.commit()

        cursor.close()
        conn.close()

        self.irc.send(f'PART #{username}')
        self.irc.privmsg('isabellesays', f'I have left your channel, @{username}')

    def handle_help(self, channel):
        self.irc.privmsg(channel, 'Please see the panels below for usage details!')

    def run_forever(self):
        while True:
            events = self.irc.read_events()

            for event in events:
                if (event['code'] == 'PRIVMSG' and
                    event['message'].startswith('!villager')):
                    self.say_info(event['channel'][1:], event['message'])

                elif (event['code'] == 'PRIVMSG' and
                      event['channel'][1:] == 'isabellesays' and
                      event['message'].startswith('!help')):
                    self.handle_help(event['channel'][1:])

                elif (event['code'] == 'PRIVMSG' and
                      event['channel'][1:] == 'isabellesays' and
                      event['message'].startswith('!join')):
                    self.handle_add(event['tags']['display-name'].lower())

                elif (event['code'] == 'PRIVMSG' and
                      event['channel'][1:] == 'isabellesays' and
                      event['message'].startswith('!leave')):
                    self.handle_remove(event['tags']['display-name'].lower())


