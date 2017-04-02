======
Pugger
======
About
-----
Pugger is a bot for organizing and running pickup games through Discord. It is currently in development and is written in python with the `discord.py`_ API wrapper.

--------
Commands
--------
The following commands are currently supported::

    !pug new
    !pug delete <pug_id>
    !pug join <pug_id> [<role>...]
    !pug leave <pug_id>
    !pug leave <pug_id> <role>...
    !pug list <pug_id> [<role>...]

Note that if only one pug currently exists in a channel pug_id is optional. Calling leave without specifying any roles will remove you from the pug entirely whereas calling it with one or more roles listed will only remove you from those roles regardless if you have already left them or if they even exist. Join with no role specified will join you to No Role if it exists or the only role available if only one is specified.

------------
Requirements
------------
- Python 3.4.2+
- `discord.py`_ Library and it's requirements
- `basehash`_ Library

Installing through pip should handle installing required libraries

.. _discord.py: https://github.com/Rapptz/discord.py
.. _basehash: http://bnlucas.github.io/python-basehash/