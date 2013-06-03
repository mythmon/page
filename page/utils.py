import re

from twisted.python import log


def clean_formatting(message):
    """Remove formatting codes from a Weechat message."""

    # I have no idea why they use \x19, but at least they are consistent.
    clean = re.sub(r'\x19F\d\d', '', message)
    clean = re.sub(r'\x1C', '', clean)

    # I'm not sure if all the format codes are \x19F, so yell if
    # something was missed.
    if '\x19' in clean:
        log.err('Unknown format character in "%r".' % clean)
    if '\x1c' in clean:
        log.err('Unknown format character in "%r".' % clean)

    return clean
