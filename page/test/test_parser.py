from datetime import datetime, timedelta
from pprint import pformat

from nose.tools import eq_
from nose.plugins.skip import SkipTest

from page.parser import bytes_to_int, RelayParser


def test_bytes_to_int():
    eq_(bytes_to_int('\x00\x00\x00\x00'), 0)
    eq_(bytes_to_int('\x00\x00\x00\xFF'), 255)
    eq_(bytes_to_int('\x00\x00\x01\x00'), 256)
    eq_(bytes_to_int('\x12\x34\x56\x78'), 305419896)


def test_parser_message():
    pass


def test_parser_int4():
    eq_(RelayParser('\x02\x00\x00\x42').int4(), 0x02000042)


def test_parser_type():
    eq_(RelayParser('chr').type(), 'chr')


def test_parser_object():

    def t(i, o):
        eq_(RelayParser(i).object(), o)

    # A char
    yield t, 'chrA', 'A'

    # Integers
    yield t, 'int\x10\x10\x10\x10', 0x10101010
    yield t, 'int\x00\x00\x00\x10', 16

    # Longs
    yield t, 'lon\x03512', 512
    yield t, 'lon\x019', 9

    # Strings
    yield t, 'str\x00\x00\x00\x00', ''
    yield t, 'str\x00\x00\x00\x0DHello, World!', 'Hello, World!'
    yield t, 'str\xFF\xFF\xFF\xFF', None

    # Buffers
    yield t, 'buf\x00\x00\x00\x00', ''
    yield t, 'buf\x00\x00\x00\x0DHello, World!', 'Hello, World!'
    yield t, 'buf\xFF\xFF\xFF\xFF', None

    # Pointers
    yield t, 'ptr\x01\x00', None
    yield t, 'ptr\x091a2b3c4d5', '0x1a2b3c4d5'

    # Time. Seconds -> datetime object.
    yield t, 'tim\x0A1321993456', datetime(2011, 11, 22, 20, 24, 16)

    # Hash Table.
    yield t, 'htbchrchr' '\x00\x00\x00\x02' 'ABCD', {'A': 'B', 'C': 'D'}
    yield t, ('htbintint' '\x00\x00\x00\x02'
              '\x00\x00\x00\x01' '\x00\x00\x00\x02'
              '\x00\x00\x00\x03' '\x00\x00\x00\x04'), {1: 2, 3: 4}

    # Info. A k/v tuple made of strings.
    yield t, 'inf\x00\x00\x00\x03key\x00\x00\x00\x05value', ('key', 'value')

    # Info Lists
    yield t, 'inl' '\x00\x00\x00\x03foo' '\x00', ('foo', [])

    data = ('inl' '\x00\x00\x00\x03foo' '\x01'
            '\x01' '\x00\x00\x00\x03' 'bar' 'int' '\x00\x00\x00\x2A')
    yield t, data, ('foo', [{'bar': 42}])

    data = ('inl'
            '\x00\x00\x00\x03foo' '\x02'
            '\x01'
            '\x00\x00\x00\x03bar' 'int' '\x00\x00\x00\x01'
            '\x02'
            '\x00\x00\x00\x03baz' 'chr' 'A'
            '\x00\x00\x00\x03qux' 'lon' '\x05' '65535')
    yield t, data, ('foo', [{'bar': 1}, {'baz': 'A', 'qux': 65535}])

    # Arrays
    data = 'arrchr\x00\x00\x00\x08ABCDEFGH'
    yield t, data, ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

    data = ('arr' 'lon' '\x00\x00\x00\x03'
            '\x011' '\x0222' '\x03333')
    yield t, data, [1, 22, 333]


def test_object_hdata_parts():
    """
    H-Data is really complicated.

    This tests each of the parts, building up to a full H-Data object.
    """

    # H-Path
    data = '\x00\x00\x00\x1Bbuffer/lines/line/line_data'
    eq_(RelayParser(data).hpath(), ['buffer', 'lines', 'line', 'line_data'])

    # H-key
    data = 'foo:int'
    eq_(RelayParser(data).hkey(), ('foo', 'int'))

    # H-Keys
    data = '\x00\x00\x00\x0Anumber:int'
    eq_(RelayParser(data).hkeys(), [('number', 'int')])
    data = '\x00\x00\x00\x13number:int,name:str'
    eq_(RelayParser(data).hkeys(), [('number', 'int'), ('name', 'str')])


def test_object_hdata_full():
    # Full H-Data
    data = ('\x00\x00\x00\x06' 'buffer'  # h-path
            '\x00\x00\x00\x18' 'number:int,full_name:str'  # keys
            '\x00\x00\x00\x02'  # count
            # value 1
            '\x05' '12345'  # pointer
            '\x00\x00\x00\x01'  # number
            '\x00\x00\x00\x0C' 'core.weechat'  # full_name
            # value 2
            '\x05' '6789a'  # pointer
            '\x00\x00\x00\x02'  # number
            '\x00\x00\x00\x13' 'irc.server.freenode'  # full_name
            )

    with open('d', 'w') as d:
        d.write(data)

    expected = {
        'path': ['buffer'],
        'keys': [('number', 'int'), ('full_name', 'str')],
        'values': [
            {
                '_pointers': [('buffer', '0x12345')],
                'number': 1,
                'full_name': 'core.weechat',
            },
            {
                '_pointers': [('buffer', '0x6789a')],
                'number': 2,
                'full_name': 'irc.server.freenode',
            },
        ]
    }

    eq_(RelayParser(data).o_hda(), expected)


def test_message():

    def t(i, o):
        eq_(RelayParser(i).message()[1], o)

    data = '\x00\x00\x00\x0C' '\x00' '\xFF\xFF\xFF\xFF' 'int\x00\x00\x00\x2A'
    yield t, data, [42]
    data = '\x00\x00\x00\x10' '\x00' '\xFF\xFF\xFF\xFF' 'chrLchrOchrL'
    yield t, data, ['L', 'O', 'L']


def test_weechat_sample_data():
    """This is the output I got from Weechat's "test" method."""

    data = (
        '\x00\x00\x00\x9e' '\x00' '\xff\xff\xff\xff'
        'chrA'
        'int\x00\x01\xe2@'
        'lon\n1234567890'
        'str\x00\x00\x00\x08a string'
        'str\x00\x00\x00\x00'
        'str\xff\xff\xff\xff'
        'buf\x00\x00\x00\x06buffer'
        'buf\xff\xff\xff\xff'
        'ptr\x0c7fffd30a5778'
        'tim\n1321993456'
        'arrstr\x00\x00\x00\x02\x00\x00\x00\x03abc\x00\x00\x00\x02de'
        'arrint\x00\x00\x00\x03\x00\x00\x00{\x00\x00\x01\xc8\x00\x00\x03\x15'
    )

    eq_(RelayParser(data).message()[1],
        [
            'A',
            123456,
            1234567890,
            'a string',
            '',
            None,
            'buffer',
            None,
            '0x7fffd30a5778',
            datetime(2011, 11, 22, 20, 24, 16),
            ['abc', 'de'],
            [123, 456, 789],
        ])


def test_weechat_sample_nicklist():
    """This is a real message received from weechat."""
    with open('page/test/nicklist_hdata.bin') as hdata:
        msg = RelayParser(hdata.read()).message()

    with open('out', 'w') as f:
        f.write(pformat(msg))

def test_weechat_sample_private_message():
    """This is a real message received from weechat."""
    with open('page/test/private_hdata.bin') as hdata:
        msg = RelayParser(hdata.read()).message()

    with open('out', 'w') as f:
        f.write(pformat(msg))
