import re

from twisted.python import log


def clean_formatting(message):
    """Remove formatting codes from a Weechat message."""

    # I have no idea why they use \x19, but at least they are consistent.
    clean = re.sub(r'\x19F\d\d', '', message)
    clean = re.sub(r'\x1C', '', clean)
    clean = re.sub(r'\x1A', '', clean) # Used to indicate start of bold formating. Possibly replace with <bold>?
    clean = re.sub(r'\x1B', '', clean) # Used to indicate end of bold formating. Possibly replace with </bold>?
    clean = re.sub(r'\x01', '', clean)

    # I'm not sure if all the format codes are \x19F, so yell if
    # something was missed.
    if '\x19' in clean:
        log.err('Unknown format character in "%r".' % clean)
    if '\x1c' in clean:
        log.err('Unknown format character in "%r".' % clean)
    if '\x1a' in clean:
        log.err('Unknown format character in "%r".' % clean)
    if '\x1b' in clean:
        log.err('Unknown format character in "%r".' % clean)
    if '\x01' in clean:
        log.err('Unknown format character in "%r".' % clean)


    return clean
