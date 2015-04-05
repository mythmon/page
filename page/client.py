import sys
from datetime import datetime, timedelta

from twisted.internet import reactor, task
from twisted.internet.protocol import Protocol, ReconnectingClientFactory
from twisted.protocols.policies import TimeoutMixin
from twisted.python import log

from page import config
from page.notify import notify
from page.parser import parse_message, bytes_to_int
from page.utils import clean_formatting


class RelayProtocol(Protocol, TimeoutMixin):

    def __init__(self):
        self._buffer = ''
        self.version = ''
        self.weechat_buffers = {}
        self.setTimeout(config['timeout'])
        reactor.addSystemEventTrigger('before', 'shutdown', self.end)

    # Twisted methods.

    def connectionMade(self):
        self.transport.write('init password={password},compression=off\n'
                             .format(**config))
        self.transport.write('(buffer_list) hdata buffer:gui_buffers(*) '
                             'name\n')
        self.transport.write('sync\n')
        self.transport.write('info version\n')
        if config['heartbeat']:
            self._heartbeat = task.LoopingCall(self._send_heartbeat)
            self._heartbeat.start(config['timeout'] / 3)

    def dataReceived(self, data):
        self._buffer += data

        # If there are less than 4 bytes, we can't parse expected length
        # yet, so just chill.
        while len(self._buffer) >= 4:
            # if there are enough bytes, pop a message from the buffer.
            expected_len = bytes_to_int(self._buffer[:4])
            if len(self._buffer) >= expected_len:
                self._pop_message()
            else:
                break

    # Helper methods

    def _pop_message(self):
        expected_len = bytes_to_int(self._buffer[:4])

        # Pop the message from the buffer
        to_parse = self._buffer[:expected_len]
        self._buffer = self._buffer[expected_len:]

        # Parse it
        msg_id, message = parse_message(to_parse)

        # process it
        if msg_id is None:
            msg_id = 'misc'

        if msg_id.startswith('_'):
            msg_id = 'sys' + msg_id

        msg_id = 'msg_' + msg_id

        try:
            getattr(self, msg_id)(message)
        except AttributeError as e:
            log.err('Unknown message id: "%s". %s' % (msg_id, e))

    def end(self):
        self.transport.write('quit\n')
        self.transport.loseConnection()

    def _should_notify(self, line):
        displayed = line['displayed'] == '\x01'
        highlight = line['highlight'] == '\x01'
        message = 'irc_privmsg' in line['tags_array']
        private = 'notify_private' in line['tags_array']

        return displayed and message and (highlight or private)

    def _send_heartbeat(self):
        if self.version >= '0.4.2':
            self.transport.write('ping\n')
        else:
            self.transport.write('test\n')

    # Weechat messages

    def msg_buffer_list(self, msg):
        self.weechat_buffers.update({
            b['_pointers'][0][1]: b['name']
            for b in msg[0]['values']
        })

    def msg_sys_buffer_line_added(self, msg):
        """When a message is received, notify if appropriate."""

        # All lines, if they match the notify critera.

        for line in (l for l in msg[0]['values'] if self._should_notify(l)):
            buf_name = self.weechat_buffers[line['buffer']]
            notify(clean_formatting('{buf_name} - {prefix} - {message}'
                                    .format(buf_name=buf_name, **line)))

    def msg_sys_buffer_opened(self, msg):
        """When a buffer is added, sync it."""

        val = msg[0]['values'][0]

        _, pointer = val['_pointers'][0]
        self.transport.write('sync %s *\n' % pointer)

        if 'name' in val:
            name = val['name']
        else:
            name = val['local_variables']['name']

        self.weechat_buffers[pointer] = name

    def msg_sys_buffer_closing(self, msg):
        """When a buffer is removed, desync it."""

        _, pointer = msg[0]['values'][0]['_pointers'][0]
        self.transport.write('desync %s *\n' % pointer)
        del self.weechat_buffers[pointer]

    def msg_misc(self, msg):
        if msg[0]:
            msg_type = msg[0][0]
            # Not sure what other types of message this can have.
            if msg_type == 'version':
                # Split off -dev -rc -etc.
                self.version = msg[0][1].split('-')[0]
                return
            elif msg[0] == 'A' and msg[1] == 123456:
                # Likely a response to "test". Treat like a heartbeat.
                self.msg_sys_pong(msg)
                return
        log.err('Got unknown msg_misc: "%r"' % (msg, ))

    def msg_sys_pong(self, msg):
        self.resetTimeout()

    # Unused Weechat messages

    def msg_sys_nicklist(self, msg):
        pass

    def msg_sys_nicklist_diff(self, msg):
        pass

    def msg_sys_buffer_localvar_added(self, msg):
        pass

    def msg_sys_buffer_localvar_removed(self, msg):
        pass

    def msg_sys_buffer_localvar_changed(self, msg):
        pass

    def msg_sys_buffer_title_changed(self, msg):
        pass

    def msg_sys_buffer_renamed(self, msg):
        pass

    def msg_sys_buffer_moved(self, msg):
        pass

    def msg_sys_buffer_unmerged(self, msg):
        pass

    def msg_sys_buffer_type_changed(self, msg):
        pass


class RelayFactory(ReconnectingClientFactory):

    maxDelay = 60
    maxRetries = 30
    noisy = True

    def buildProtocol(self, addr):
        self.resetDelay()
        notify('Page - Connected')
        return RelayProtocol()

    def clientConnectionLost(self, connector, reason):
        notify('Page - Lost connection. Will retry.')
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        notify('Page - Connection failed. Will retry.')
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)


def main():
    log.startLogging(sys.stdout)
    reactor.connectTCP(config['host'], config['port'], RelayFactory())
    reactor.run()


if __name__ == '__main__':
    main()
