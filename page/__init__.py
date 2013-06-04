import json


config = {
    'command': 'notify-send %m'
}

with open('config.json') as cf:
    config.update(json.load(cf))
