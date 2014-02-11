"""
Functions to display notifications to the user.
"""
import os
import shlex

from twisted.internet import utils
from twisted.python import log

from page import config


def _check(prog):
    def cb((stdout, stderr, exit_code)):
        if exit_code == 0:
            log.msg('Succesfully sent notification')
        else:
            log.err('Error code %s when calling %s' % (exit_code, prog))

        if stdout:
            log.msg('stdout: ' + stdout)
        if stderr:
            log.err('stderr: ' + stderr)

    return cb


def notify(message):
    log.msg(message)
    args = shlex.split(config['command'])
    bin = args.pop(0)
    args[args.index('%m')] = message

    log.msg(bin, args)
    exit_code = utils.getProcessOutputAndValue(bin, args, os.environ)
    exit_code.addBoth(_check(bin))

    return exit_code
