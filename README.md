Page is a small program to report to you the status of Weechat by
connecting to it via the relay protocol

Right now all it does is connect, get a list of buffers, and then quit
cleanly.

Eventually it should do things like watch for highlights and certain
kinds of messages and show notifications.

How do?
-------

```sh
git clone git@github.com:mythmon/page.git
cd page
virtualenv .
. bin/activate
pip install requirements.txt
PYTHONPATH=. python page/client.py
```
