from brewtils.models import System, Command, Instance, Parameter, Request, PatchOperation, \
    LoggingConfig, Event, Queue, Job, IntervalTrigger, DateTrigger, CronTrigger, RequestTemplate


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


def default_assert_equal(obj1, obj2, **kwargs):
    allowed_classes = kwargs['allowed_classes']
    if not isinstance(allowed_classes, tuple):
        allowed_classes = tuple([allowed_classes])

    type_name = kwargs['type_name']
    deep_fields = kwargs.get('deep_fields', [])
    deep_field_names = [f for f, _ in deep_fields]

    message = ' was not an instance of %s got: ' % str(allowed_classes)
    types_str = 'Object1: ' + str(type(obj1)) + ' Object2: ' + str(type(obj2))
    assert isinstance(obj1, allowed_classes), 'obj1' + message + str(type(obj1))
    assert isinstance(obj2, allowed_classes), 'obj2' + message + str(type(obj2))

    assert type(obj1) is type(obj2), 'object are not the same types ' + types_str
    for key in obj1.__dict__.keys():
        if key in deep_field_names:
            continue

        assert hasattr(obj1, key), "%s1 does not have an attribute '%s'" % (type_name, key)
        assert hasattr(obj2, key), "%s1 does not have an attribute '%s'" % (type_name, key)
        message = (
                "%s: %s was not the same (%s, %s)" %
                (type_name, key, getattr(obj1, key), getattr(obj2, key))
        )
        assert getattr(obj1, key) == getattr(obj2, key), message

    if kwargs.get('deep'):
        for field, comparer in deep_fields:
            assert hasattr(obj1, field), "%s1 does not have an attribute '%s'" % (type_name, field)
            assert hasattr(obj2, field), "%s1 does not have an attribute '%s'" % (type_name, field)
            comparer(getattr(obj1, field), getattr(obj2, field), deep=True)


def assert_patch_equal(patch1, patch2, deep=False):
    default_assert_equal(
        patch1, patch2,
        allowed_classes=PatchOperation,
        deep=deep,
        type_name='patch'
    )


def assert_logging_config_equal(logging_config1, logging_config2, deep=False):
    default_assert_equal(
        logging_config1,
        logging_config2,
        type_name='logging_config',
        allowed_classes=LoggingConfig,
        deep=deep
    )


def assert_event_equal(event1, event2, deep=False):
    default_assert_equal(
        event1, event2, deep=deep, allowed_classes=Event, type_name='event'
    )


def assert_queue_equal(queue1, queue2, deep=False):
    default_assert_equal(
        queue1, queue2, deep=deep, allowed_classes=Queue, type_name='queue'
    )


def assert_job_equal(job1, job2, deep=False):
    default_assert_equal(
        job1,
        job2,
        allowed_classes=Job,
        type_name='job',
        deep=deep,
        deep_fields=[
            ('trigger', assert_trigger_equal),
            ('request_template', assert_request_template_equal)
        ]
    )


def assert_request_template_equal(rt1, rt2, deep=False):
    default_assert_equal(
        rt1,
        rt2,
        allowed_classes=RequestTemplate,
        type_name='request_template',
        deep=deep
    )


def assert_trigger_equal(trigger1, trigger2, deep=False):
    default_assert_equal(
        trigger1,
        trigger2,
        allowed_classes=(CronTrigger, DateTrigger, IntervalTrigger),
        type_name='trigger',
        deep=deep
    )
