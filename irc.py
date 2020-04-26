import socket
import sys
 
 
class IRC:
 
    irc = socket.socket()
  
    def __init__(self):  
        self.irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
 
    def send(self, chan, msg):
        self.irc.send(("PRIVMSG #" + chan + " :" + msg + "\r\n").encode())
 
    def connect(self, server, port, channels, nick, oauth):
        print("Connecting to", server)
        self.irc.connect((server, port))
        self.irc.send(("PASS " + oauth + "\r\n").encode())
        self.irc.send(("NICK " + nick + "\r\n").encode())               
        for channel in channels: 
            self.irc.send(("JOIN #" + channel + "\r\n").encode())
        self.irc.send(("CAP REQ :twitch.tv/tags\r\n").encode())
        self.irc.send(("CAP REQ :twitch.tv/commands\r\n").encode())

    def parse_line(self, line):
        print('Debug:', line)

        event = {
            'tags': '',
            'code': '',
            'message': ''
        }

        if line.startswith('@'):
            tags = line[1:].split(' ')[0]
            event['tags'] = dict([tag.split('=') for tag in tags.split(';')])
            line = line.split(' ', 1)
            line = line[1]

        if line.startswith(':'):
            parts = line[1:].split(' :', 1)
            args = parts[0].split(' ')

            if len(args) > 1:
                event['code'] = args[1]
                event['channel'] = args[2].strip()
                if len(parts) == 2:
                    event['message'] = parts[1].strip()
        #TODO: is this necessary?
        else:
            print('do we ever get here?')
            parts = line.split(' :')
            event['code'] = parts[0]
            event['message'] = parts[1]
 
        if event['code'] == 'PING':                      
            print("PONG :" + event['message'] + "\r\n")
            self.irc.send(("PONG :" + event['message'] + "\r\n").encode()) 
 
        print(event)
        print()
        return event

    def read_events(self):
        lines = ''

        while True:
            message = self.irc.recv(2048)
            message = message.decode()
            print(message)

            lines += message
            if lines.endswith('\r\n'):
                break

        lines = filter(None, lines.split('\r\n'))
        events = [self.parse_line(line) for line in lines]
        return events
