import json


config = {
    'command': 'notify-send %m',
    'heartbeat': False
}

with open('config.json') as cf:
    config.update(json.load(cf))
