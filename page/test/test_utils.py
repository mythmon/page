from page import utils

from nose.tools import eq_


def test_clean_formatting():
    # One format
    eq_(utils.clean_formatting('Hey \x19F12you!'), 'Hey you!')
    # Two format
    eq_(utils.clean_formatting('\x19F20Hey \x19F12you!'), 'Hey you!')


def test_unknown_formatting():
    try:
        utils.clean_formatting('\x19A01Wat')
        assert False, 'should have thrown an error'
    except NotImplementedError:
        # good
        pass
