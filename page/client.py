import json
import re

from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ClientFactory

from page.parser import parse_message, bytes_to_int
from page.utils import clean_formatting


with open('config.json') as cf:
    config = json.load(cf)


class RelayProtocol(Protocol):

    def __init__(self, *args, **kwargs):
        self._buffer = ''
        reactor.addSystemEventTrigger('before', 'shutdown', self.end)

    # Twisted methods.

    def connectionMade(self):
        self.transport.write('init password={password},compression=off\n'
                             .format(**config))
        # self.transport.write('(buffer_list) hdata buffer:gui_buffers(*) '
        #                      'number,full_name\n')
        self.transport.write('sync\n')

    def dataReceived(self, data):
        self._buffer += data

        # If there are less than 4 bytes, we can't parse expected length
        # yet, so just chill.
        if len(self._buffer) < 4:
            return

        expected_len = bytes_to_int(self._buffer[:4])

        if len(self._buffer) >= expected_len:
            # Pop the message from the buffer
            to_parse = self._buffer[:expected_len]
            self._buffer = self._buffer[expected_len:]

            # Parse it
            msg_id, message = parse_message(to_parse)

            # process it
            if msg_id.startswith('_'):
                msg_id = 'sys' + msg_id

            if msg_id is None:
                msg_id = 'misc'

            try:
                getattr(self, 'msg_' + msg_id)(message)
            except AttributeError:
                print 'Unknown message id: "%s"' % msg_id

    # Helper methods

    def end(self):
        self.transport.write('quit\n')
        self.transport.loseConnection()

    def _should_notify(self, line):
        displayed = line['displayed'] == '\x01'
        highlight = line['highlight'] == '\x01'
        message = 'irc_privmsg' in line['tags_array']
        private = 'notify_private' in line['tags_array']

        return displayed and message and (highlight or private)

    # Weechat messages

    def msg_sys_buffer_line_added(self, message):
        """When a message is received, notify if appropriate."""

        # All lines from all objects, if they match the notify critera.
        lines = sum((obj['values'] for obj in message), [])
        lines = filter(self._should_notify, lines)

        for line in lines:
            print clean_formatting('{prefix}: {message}'.format(**line))

    def msg_sys_buffer_opened(self, message):
        """When a buffer is added, sync it."""

        _, pointer = message[0]['values'][0]['_pointers'][0]
        self.transport.write('sync %s *\n' % pointer)

    def msg_sys_buffer_closing(self, message):
        """When a buffer is removed, desync it."""

        _, pointer = message[0]['values'][0]['_pointers'][0]
        self.transport.write('desync %s *\n' % pointer)

    # Unused Weechat messages

    def msg_sys_nicklist(self, message):
        pass

    def msg_sys_buffer_localvar_added(self, message):
        pass

    def msg_sys_buffer_localvar_removed(self, message):
        pass

    def msg_sys_buffer_localvar_changed(self, message):
        pass

    def msg_sys_buffer_title_changed(self, message):
        pass

    def msg_sys_buffer_renamed(self, message):
        pass


class RelayFactory(ClientFactory):

    def buildProtocol(self, addr):
        return RelayProtocol()


def main():
    reactor.connectTCP(config['host'], config['port'], RelayFactory())
    reactor.run()


if __name__ == '__main__':
    main()
