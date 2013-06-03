import json

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
        self.transport.write('(buffer_list) hdata buffer:gui_buffers(*) '
                             'number,full_name\n')

    def dataReceived(self, data):
        self._buffer += data

        length = bytes_to_int(self._buffer[:4])

        if len(self._buffer) >= length:
            to_parse = self._buffer[:length]
            self._buffer = self._buffer[length:]

            print 'got data (%s bytes)' % length
            msg_id, message = parse_message(to_parse)
            print 'id:', msg_id

            if msg_id == 'buffer_list':
                for v in message[0]['values']:
                    print v['number'], v['full_name']
                self.end()

    def end(self):
        self.transport.write('quit\n')
        self.transport.loseConnection()


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
