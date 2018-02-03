Brewtils
=========

Brewtils is the Python library for interfacing with Beergarden systems. It provides simple ways to query information, access systems, generate requests, and more.

## Installation
Brewtils lives on PyPI. You can install it via:

    pip install brewtils

If you already have a requirements definition file you can add brewtils like this:

    brewtils

And then install with pip as normal.

## Usage

There are three major ways to use `brewtils`. A brief summary of each is given below so you can determine which best fits your use-case.


### Remote Plugin Decorators

The `decorators` module helps you create your own remote plugin. Suppose you have the following class:

```python
Class MyClient(object):

    def do_something(self):
        print("Hello, World!")
        return "Hello, World!"

    def echo_message(self, message):
        print(message)
        return message
```

There are two steps for making this class into a Beergarden plugin. First, you'll need to decorate your class and methods:

```python
from brewtils.decorators import system, parameter, command 

@system
Class MyClient(object):

    @command
    def do_something(self):
        print("Hello, World!")
        return "Hello, World!"

    @parameter(key="message", description="The message to echo", type="String")
    def echo_message(self, message):
        print(message)
        return message
```

The `@system` tells us that the `MyClient` class is going to be a Beergarden plugin.

The `@command` tells us that `do_something` is going to be a command.

The `@parameter` tells us information about the parameters to the `echo_message` method.

Now that we've decorated the client definition we just need to point the remote plugin at a Beergarden and start it. We can do that like this:

```python
from brewtils.plugin import RemotePlugin

#...MyClient definition...

def main():
    client = MyClient()
    plugin = RemotePlugin(client, name="My Client", version="0.0.1", bg_host='127.0.0.1', bg_port=2337)
    plugin.run()

if __name__ == "__main__":
    main()
```

Assuming you have a Beergarden running on port 2337 on localhost, running this will register and start your plugin.


### System Client

The `SystemClient` is designed to help you interact with registered Systems as if they were native Python objects.  Suppose the following System has been registered with Beergarden:

    System:
      Name: foo
      Version: 0.0.1
      Commands:
        do_something1
          Params:
            key1
            key2

        do_something2
          Params:
            key3
            key4

That is, we have a System named "foo" with two possible commands: `do_something1` and `do_something2`, each of which takes 2 parameters (key1-4).

Now suppose we want to exercise `do_something1` and inspect the result. The `SystemClient` makes this trivial:

```python
from brewtils.rest.system_client import SystemClient

foo_client = SystemClient('localhost', 2337, 'foo')

request = foo_client.do_something1(key1="k1", key2="k2")

print(request.status) # 'SUCCESS'
print(request.output) # do_something1 output
```
When you call `do_something1` on the `SystemClient` object it will make a REST call to Beergarden to generate a Request. It will then block until that request has completed, at which point the returned object can be queried the same way as any other Request object.

If the system you are using has multiple instances, you can specify the default instance to use:

```python
foo_client = SystemClient('localhost', 2337, 'foo', default_instance="01")

foo_client.do_something1(key1="k1", key2="k2") # Will set instance_name to '01'
```

If you want to operate on multiple instances of the same system, you can specify the instance name each time:

```python
foo_client = SystemClient('localhost', 2337, 'foo')
request = foo_client.do_something1(key1="k1", key2="k2", _instance_name="01") # Will set instance_name to '01'
```

Notice the leading `_` in the `_instance_name` keyword argument. This is necessary to distinguish command arguments (things to pass to `do_something1`) from Beergarden arguments. In general, you should try to avoid naming parameters with a leading underscore to avoid name collisions.

### Easy Client

The `EasyClient` is intended to make it easy to directly query Beergarden. Suppose the same `foo` System as above has been registered in Beergarden. We can use the `EasyClient` to gather information:

```python
from brewtils.rest.easy_client import EasyClient

client = EasyClient('localhost', 2337)

foo_system = client.find_unique_system(name='foo', version='0.0.1')

for command in foo_system.commands:
  print(command.name)
```

The `EasyClient` is full of helpful commands so feel free to explore all the methods that are exposed.
