import json
import re

from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ClientFactory

from page.parser import parse_message, bytes_to_int


with open('config.json') as cf:
    config = json.load(cf)


class RelayProtocol(Protocol):

    def __init__(self, *args, **kwargs):
        self._buffer = ''

    def connectionMade(self):
        self.transport.write('init password={password},compression=off\n'
                             .format(**config))
        # self.transport.write('(buffer_list) hdata buffer:gui_buffers(*) '
        #                      'number,full_name\n')
        self.transport.write('sync\n')

    def dataReceived(self, data):
        self._buffer += data

        length = bytes_to_int(self._buffer[:4])

        if len(self._buffer) >= length:
            to_parse = self._buffer[:length]
            self._buffer = self._buffer[length:]

            msg_id, message = parse_message(to_parse)

            if msg_id == '_buffer_line_added':
                for msg in message:
                    for line in msg['values']:
                        self.process_line(line)

    def end(self):
        self.transport.write('quit\n')
        self.transport.loseConnection()

    def process_line(self, line):
        if line['highlight'] == '\x00':
            return
        if line['displayed'] == '\x00':
            return
        if 'irc_privmsg' not in line['tags_array']:
            return

        print self.clean_colors('{prefix}: {message}'.format(**line))

    def clean_colors(self, message):
        clean = re.sub(r'\x19F\d\d', '', message)

        if '\x19' in clean:
            raise NotImplemented('Unknown format character in "%r".' % clean)

        return clean


class RelayFactory(ClientFactory):

    def buildProtocol(self, addr):
        return RelayProtocol()

    def clientConnectionLost(self, connector, reason):
        #print 'Lost connection. Reason:', reason
        reactor.stop()

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason
        reactor.stop()


reactor.connectTCP(config['host'], config['port'], RelayFactory())
reactor.run()
