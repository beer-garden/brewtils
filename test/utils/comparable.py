from brewtils.models import System, Command, Instance, Parameter, Request, PatchOperation, \
    LoggingConfig, Event, Queue, Job


def assert_system_equal(system1, system2, deep=False):
    assert isinstance(system1, System), "system1 was not a System"
    assert isinstance(system2, System), "system2 was not a System"
    assert type(system1) is type(system2), "system1 and system2 are not the same type."

    deep_fields = ["instances", "commands"]
    for key in system1.__dict__.keys():
        if key in deep_fields:
            continue

        assert hasattr(system1, key), "System1 does not have an attribute '%s'" % key
        assert hasattr(system2, key), "System2 does not have an attribute '%s'" % key
        assert getattr(system1, key) == getattr(system2, key), (
            "%s was not the same (%s, %s)" % (key, getattr(system1, key), getattr(system2, key)))

    if deep:
        assert hasattr(system1, "instances"), "System1 does not have attribute 'instances'"
        assert hasattr(system1, "commands"), "System1 does not have attribute 'commands'"
        assert hasattr(system2, "instances"), "System1 does not have attribute 'instances'"
        assert hasattr(system2, "commands"), "System1 does not have attribute 'commands'"

        assert len(system1.commands) == len(system2.commands), ("system1 has a different number "
                                                                "of commands than system2")
        for command1, command2 in zip(sorted(system1.commands, key=lambda x: x.name),
                                      sorted(system2.commands, key=lambda x: x.name)):
            assert_command_equal(command1, command2, deep)

        for instance1, instance2 in zip(sorted(system1.instances, key=lambda x: x.name),
                                        sorted(system2.instances, key=lambda x: x.name)):
            assert_instance_equal(instance1, instance2, deep)


def assert_command_equal(command1, command2, deep=False):
    assert isinstance(command1, Command), "command1 was not a Command"
    assert isinstance(command2, Command), "command2 was not a Command"
    assert type(command1) is type(command2), "command1 and command2 are not the same type."

    deep_fields = ["parameters", "system"]
    for key in command1.__dict__.keys():
        if key in deep_fields:
            continue

        assert hasattr(command1, key), "Command1 does not have an attribute '%s'" % key
        assert hasattr(command2, key), "Command2 does not have an attribute '%s'" % key
        assert getattr(command1, key) == getattr(command2, key), (
            "%s was not the same (%s, %s)" % (key, getattr(command1, key), getattr(command2, key)))

    if deep:
        assert hasattr(command1, "parameters"), "command1 does not have attribute 'parameters'"
        assert hasattr(command2, "parameters"), "command1 does not have attribute 'parameters'"
        assert len(command1.parameters) == len(command2.parameters), (
            "command1 has a different number of parameters than command2")
        for parameter1, parameter2 in zip(sorted(command1.parameters, key=lambda p: p.key),
                                          sorted(command2.parameters, key=lambda p: p.key)):
            assert_parameter_equal(parameter1, parameter2, deep)


def assert_instance_equal(instance1, instance2, deep=False):
    assert isinstance(instance1, Instance), "instance1 was not an Instance"
    assert isinstance(instance2, Instance), "instance2 was not an Instance"
    assert type(instance1) is type(instance2), "instance1 and instance2 are not the same type."

    for key in instance1.__dict__.keys():
        assert hasattr(instance1, key), "instance1 does not have an attribute '%s'" % key
        assert hasattr(instance2, key), "instance2 does not have an attribute '%s'" % key
        assert getattr(instance1, key) == getattr(instance2, key), \
            "%s was not the same (%s, %s)" % (key, getattr(instance1, key), getattr(instance2, key))


def assert_request_equal(request1, request2, deep=False):
    assert isinstance(request1, Request), "request1 was not a Request"
    assert isinstance(request2, Request), "request2 was not a Request"
    assert type(request1) is type(request2), "request1 and request2 are not the same type."

    deep_fields = ["children", "parent"]
    for key in request1.__dict__.keys():
        if key in deep_fields:
            continue

        assert hasattr(request1, key), "request1 does not have an attribute '%s'" % key
        assert hasattr(request2, key), "request2 does not have an attribute '%s'" % key
        assert getattr(request1, key) == getattr(request2, key), \
            "%s was not the same (%s, %s)" % (key, getattr(request1, key), getattr(request2, key))

    if deep:
        assert hasattr(request1, "children"), "request1 does not have attribute 'children'"
        assert hasattr(request2, "children"), "request2 does not have attribute 'children'"
        if request1.children is not None:
            assert len(request1.children) == len(request2.children), \
                "request1 has a different number of children than request 2"
            for request1, request2 in zip(sorted(request1.children, key=lambda p: p.id),
                                          sorted(request2.children, key=lambda p: p.id)):
                assert_request_equal(request1, request2, deep)


def assert_parameter_equal(parameter1, parameter2, deep=False):
    assert isinstance(parameter1, Parameter), "parameter1 was not a Parameter"
    assert isinstance(parameter2, Parameter), "parameter2 was not a Parameter"
    assert type(parameter1) is type(parameter2), "parameter1 and parameter2 are not the same type."

    deep_fields = ["parameters", "choices"]
    for key in parameter1.__dict__.keys():
        if key in deep_fields:
            continue

        assert hasattr(parameter1, key), "parameter1 does not have an attribute '%s'" % key
        assert hasattr(parameter2, key), "parameter2 does not have an attribute '%s'" % key
        assert getattr(parameter1, key) == getattr(parameter2, key), \
            "%s was not the same (%s, %s)" % (key,
                                              getattr(parameter1, key),
                                              getattr(parameter2, key))

    if deep:
        assert hasattr(parameter1, "parameters"), "parameter1 does not have attribute 'parameters'"
        assert hasattr(parameter2, "parameters"), "parameter1 does not have attribute 'parameters'"
        assert len(parameter1.parameters) == len(parameter2.parameters), (
            "command1 has a different number of parameters than command2")
        for parameter1, parameter2 in zip(sorted(parameter1.parameters, key=lambda p: p.key),
                                          sorted(parameter2.parameters, key=lambda p: p.key)):
            assert_parameter_equal(parameter1, parameter2, deep)

        assert hasattr(parameter1, "choices"), "parameter1 does not have attribute 'choices'"
        assert hasattr(parameter2, "choices"), "parameter2 does not have attribute 'choices'"

        assert_choices_equal(parameter1.choices, parameter2.choices)


def assert_choices_equal(choices1, choices2):
    if choices1 is None and choices2 is None:
        return
    elif choices1 is None:
        assert False, "choices1 is None and choices2 is not"
    elif choices2 is None:
        assert False, "choices2 is None and choices1 is not"
    else:
        for key in choices1.__dict__.keys():
            assert hasattr(choices1, key), "choices1 does not have an attribute '%s'" % key
            assert hasattr(choices2, key), "choices2 does not have an attribute '%s'" % key
            assert getattr(choices1, key) == getattr(choices2, key), \
                "%s was not the same (%s, %s)" % (key,
                                                  getattr(choices1, key),
                                                  getattr(choices2, key))


def assert_patch_equal(patch1, patch2, deep=False):
    assert isinstance(patch1, PatchOperation), "patch1 was not an PatchOperation"
    assert isinstance(patch2, PatchOperation), "patch2 was not an PatchOperation"
    assert type(patch1) is type(patch2), "patch1 and instance2 are not the same type."

    for key in patch1.__dict__.keys():
        assert hasattr(patch1, key), "patch1 does not have an attribute '%s'" % key
        assert hasattr(patch2, key), "patch2 does not have an attribute '%s'" % key
        assert getattr(patch1, key) == getattr(patch2, key), \
            "%s was not the same (%s, %s)" % (key, getattr(patch1, key), getattr(patch2, key))


def assert_logging_config_equal(logging_config1, logging_config2, deep=False):
    assert isinstance(logging_config1, LoggingConfig), "logging_config1 was not a LoggingConfig"
    assert isinstance(logging_config2, LoggingConfig), "logging_config2 was not a LoggingConfig"
    assert type(logging_config1) is type(logging_config2), (
        "logging_config1 and logging_config2 are not the same type")

    for key in logging_config1.__dict__.keys():
        assert hasattr(logging_config1, key), "logging_config1 does not have attribute '%s'" % key
        assert hasattr(logging_config2, key), "logging_config2 does not have attribute '%s'" % key
        assert getattr(logging_config1, key) == getattr(logging_config2, key), \
            "%s was not the same (%s, %s)" % (key,
                                              getattr(logging_config1, key),
                                              getattr(logging_config2, key))


def assert_event_equal(event1, event2, deep=False):
    assert isinstance(event1, Event), "event1 was not an Event"
    assert isinstance(event2, Event), "event2 was not an Event"
    assert type(event1) is type(event2), "event1 and event2 are not the same type"

    for key in event1.__dict__.keys():
        assert hasattr(event1, key), "event1 does not have an attribute '%s'" % key
        assert hasattr(event2, key), "event2 does not have an attribute '%s'" % key
        assert getattr(event1, key) == getattr(event2, key), \
            "%s was not the same (%s, %s)" % (key, getattr(event1, key), getattr(event2, key))


def assert_queue_equal(queue1, queue2, deep=False):
    assert isinstance(queue1, Queue), "queue1 was not an Queue"
    assert isinstance(queue2, Queue), "queue2 was not an Queue"
    assert type(queue1) is type(queue2), "event1 and event2 are not the same type"

    for key in queue1.__dict__.keys():
        assert hasattr(queue1, key), "queue1 does not have an attribute '%s'" % key
        assert hasattr(queue2, key), "queue2 does not have an attribute '%s'" % key
        assert getattr(queue1, key) == getattr(queue2, key), \
            "%s was not the same (%s, %s)" % (key, getattr(queue1, key), getattr(queue2, key))


def assert_job_equal(job1, job2, deep=False):
    assert isinstance(job1, Job), "job1 was not an Job"
    assert isinstance(job2, Job), "job2 was not an Job"
    assert type(job1) is type(job2), "job1 and job2 are not the same type"

    for key in job1.__dict__.keys():
        assert hasattr(job1, key), "job1 does not have an attribute '%s'" % key
        assert hasattr(job2, key), "job2 does not have an attribute '%s'" % key
        assert getattr(job1, key) == getattr(job2, key), \
            "%s was not the same (%s, %s)" % (key, getattr(job1, key), getattr(job2, key))
