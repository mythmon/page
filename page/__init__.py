import json


config = {
    'command': 'notify-send %m',
    'heartbeat': False,
    'timeout': 15,
}

with open('config.json') as cf:
    config.update(json.load(cf))
