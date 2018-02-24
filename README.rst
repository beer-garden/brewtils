
========
Brewtils
========

Brewtils is the Python library for interfacing with Beergarden systems. If you are planning on
writing beer-garden plugins, this is the correct library for you. In addition to writing plugins,
it provides simple ways to query the API and is officially supported by the beer-garden team.

|gitter| |pypi| |travis| |codecov| |docs| |pyup|

.. |gitter| image:: https://img.shields.io/badge/gitter-Join%20Us!-ff69b4.svg
   :target: https://gitter.im/beer-garden-io/Lobby
   :alt: Gitter

.. |pypi| image:: https://img.shields.io/pypi/v/brewtils.svg
   :target: https://pypi.python.org/pypi/brewtils
   :alt: PyPI

.. |travis| image:: https://img.shields.io/travis/beer-garden/brewtils.svg
   :target: https://travis-ci.org/beer-garden/brewtils?branch=master
   :alt: Build Status

.. |codecov| image:: https://codecov.io/gh/beer-garden/brewtils/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/beer-garden/brewtils
   :alt: Code Coverage

.. |docs| image:: https://readthedocs.org/projects/brewtils/badge/?version=latest
   :target: https://brewtils.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

.. |pyup| image:: https://pyup.io/repos/github/beer-garden/brewtils/shield.svg
   :target: https://pyup.io/repos/github/beer-garden/brewtils/
   :alt: Pyup Updates

Features
--------
Brewtils helps you interact with beer-garden.

* Easy way to create beer-garden plugins
* Full support of the entire Beer-Garden API
* Officially supported by the beer-garden team

Installation
------------

To install brewtils, run this command in your terminal:

.. code-block:: console

    $ pip install brewtils

Or add it to your ``requirements.txt``

.. code-block:: console

    $ cat brewtils >> requirements.txt
    $ pip install -r requirements.txt


Quick Start
-----------

You can create your own beer-garden plugins without much problem at all. To start, we'll create
the obligatory hello-world plugin. Creating a plugin is as simple as:

.. code-block:: python

    from brewtils.decorators import system, parameter, command
    from brewtils.plugin import RemotePlugin

    @system
    class HelloWorld(object):

        @parameter(key="message", description="The message to echo", type="String")
        def say_hello(self, message="World!"):
            print("Hello, %s!" % message)
            return "Hello, %s!" % message

    if __name__ == "__main__":
        client = HelloWorld()
        plugin = RemotePlugin(client,
                              name="hello",
                              version="0.0.1",
                              bg_host='127.0.0.1',
                              bg_port=2337)
        plugin.run()

Assuming you have a Beer Garden running on port 2337 on localhost, running this will register and
start your plugin! You now have your first plugin running in beer-garden. Let's use another part
of the ``brewtils`` library to exercise your plugin from python.

The ``SystemClient`` is designed to help you interact with registered Systems as if they were native
Python objects.

.. code-block:: python

    from brewtils.rest.system_client import SystemClient

    hello_client = SystemClient('localhost', 2337, 'hello')

    request = hello_client.say_hello(message="from system client")

    print(request.status) # 'SUCCESS'
    print(request.output) # Hello, from system client!

In the background, the ``SystemClient`` has executed an HTTP POST with the payload required to get
beer-garden to execute your command. The ``SystemClient`` is how most people interact with
beer-garden when they are in the context of python and want to be making requests.

Of course, the rest of the API is accessible through the ``brewtils`` package. The ``EasyClient``
provides simple convenient methods to call the API and auto-serialize the responses. Suppose you
want to get a list of all the commands on all systems:

.. code-block:: python

    from brewtils.rest.easy_client import EasyClient

    client = EasyClient('localhost', 2337)

    systems = client.find_systems()

    for system in systems:
        for command in system.commands:
            print(command.name)

This is just a small taste of what is possible with the ``EasyClient``. Feel free to explore all the
methods that are exposed.

For more detailed information and better walkthroughs, checkout the full documentation!

Documentation
-------------

- Full Beer Garden documentation is available at https://beer-garden.io
- Brewtils Documentation is available at https://brewtils.readthedocs.io
