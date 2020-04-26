import requests
from irc import IRC


class VillagerInfo:

    def __init__(self, config):
        self.config = config
        irc = IRC()
        irc.connect(config['server'],
            config['port'],
            config['channels'],
            config['nick'],
            config['oauth'])
        self.irc = irc

    def say_info(self, channel, command):
        tokens = command.split()
        if len(tokens) < 2:
            self.irc.send(channel,
                'Usage: !villager <villager name>')
            return

        villager_name = tokens[1]
        headers = {'X-API-KEY': self.config['nookipedia_api_key']}
        url = f'https://nookipedia.com/api/villager/{villager_name}/'

        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            self.irc.send(channel, 'Couldn\'t find the specified villager :(')
            return

        info = r.json()
        message = f"{info['name']} is a {info['personality'].lower()} {info['species'].lower()}, {info['phrase']}! More info: {info['link']}"
        self.irc.send(channel, message)

    def run_forever(self):
        while True:
            events = self.irc.read_events()

            for event in events:
                if (event['code'] == 'PRIVMSG' and
                    event['message'].startswith('!villager')):
                    self.say_info(event['channel'][1:], event['message'])

