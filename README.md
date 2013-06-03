Page is a small program to report to you the status of Weechat by
connecting to it via the relay protocol

Right now it connects, subscribes (`sync`s) to all buffers, and sends notifications of highlights and private messages.

How do?
=======

```sh
git clone git://github.com/mythmon/page.git
cd page
virtualenv .
. bin/activate
pip install -r requirements.txt
vim config.json
PYTHONPATH=. python page/client.py
```

config.json
-----------

```json
{
  "host": "example.com",
  "port": 7001,
  "password": "secrets"
}
```
