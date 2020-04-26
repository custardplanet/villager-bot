from irc import IRC


class VillagerInfo:

    def __init__(self, config):
        self.config = config
        irc = IRC()
        irc.connect(config['server'], config['port'], [config['channel']], config['nick'], config['oauth'])
        self.irc = irc

    def say_info(self, command):
        tokens = command.split()
        if len(tokens) < 2:
            self.irc.send(self.config['channel'], 'Usage: !villager <villager name>')
            return

        self.irc.send(self.config['channel'], message)

    def run_forever(self):
        while True:
            events = self.irc.read_events()

            for event in events:
                if (event['code'] == 'PRIVMSG' and
                    event['message'].startswith('!villager')):
                    self.say_info(event['message'])
