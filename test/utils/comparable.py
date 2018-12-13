# -*- coding: utf-8 -*-

from functools import partial

from brewtils.models import (
    System, Command, Instance, Parameter, Request, PatchOperation,
    LoggingConfig, Event, Queue, Choices, Principal, Role, Job, IntervalTrigger,
    DateTrigger, CronTrigger, RequestTemplate, StatusInfo,
)

__all__ = [
    'assert_parameter_equal',
    'assert_command_equal',
    'assert_system_equal',
    'assert_instance_equal',
    'assert_request_equal',
    'assert_patch_equal',
    'assert_logging_config_equal',
    'assert_event_equal',
    'assert_queue_equal',
    'assert_principal_equal',
    'assert_role_equal',
    'assert_job_equal',
]


def _assert_equal(obj1, obj2, expected_type=None, deep_fields=None):

    if obj1 is None and obj2 is None:
        return

    deep_fields = deep_fields or {}

    if expected_type is not None:
        assert isinstance(obj1, expected_type), "obj1 was not an %s" % expected_type
        assert isinstance(obj2, expected_type), "obj2 was not an %s" % expected_type
    assert type(obj1) is type(obj2), "obj1 and obj2 are not the same type."

    for key in obj1.__dict__.keys():
        assert hasattr(obj1, key), "obj1 does not have an attribute '%s'" % key
        assert hasattr(obj2, key), "obj2 does not have an attribute '%s'" % key

        if key not in deep_fields.keys():
            assert getattr(obj1, key) == getattr(obj2, key), \
                "%s was not the same (%s, %s)" % \
                (key, getattr(obj1, key), getattr(obj2, key))
        else:
            nested1 = getattr(obj1, key)
            nested2 = getattr(obj2, key)

            if isinstance(nested1, list) and isinstance(nested2, list):
                l1 = sorted(getattr(obj1, key))
                l2 = sorted(getattr(obj2, key))
                assert len(l1) == len(l2)

                for item1, item2 in zip(l1, l2):
                    deep_fields[key](item1, item2)
            else:
                deep_fields[key](nested1, nested2)


# These are the 'simple' models - they don't have any nested models as fields
assert_status_equal = partial(_assert_equal, expected_type=StatusInfo)
assert_choices_equal = partial(_assert_equal, expected_type=Choices)
assert_patch_equal = partial(_assert_equal, expected_type=PatchOperation)
assert_logging_config_equal = partial(_assert_equal, expected_type=LoggingConfig)
assert_event_equal = partial(_assert_equal, expected_type=Event)
assert_queue_equal = partial(_assert_equal, expected_type=Queue)
assert_request_template_equal = partial(_assert_equal, expected_type=RequestTemplate)
assert_trigger_equal = partial(_assert_equal,
                               expected_type=(CronTrigger, DateTrigger, IntervalTrigger))


def assert_instance_equal(obj1, obj2):
    _assert_equal(obj1, obj2,
                  expected_type=Instance,
                  deep_fields={'status_info': assert_status_equal})


def assert_command_equal(obj1, obj2):

    # Command's system field only serializes the system's id
    def compare_system(sys1, sys2):
        assert sys1.id == sys2.id

    _assert_equal(obj1, obj2,
                  expected_type=Command,
                  deep_fields={
                      'parameters': assert_parameter_equal,
                      'system': compare_system,
                  })


def assert_parameter_equal(obj1, obj2):
    _assert_equal(obj1, obj2,
                  expected_type=Parameter,
                  deep_fields={
                      'parameters': assert_parameter_equal,
                      'choices': assert_choices_equal,
                  })


def assert_principal_equal(obj1, obj2):
    _assert_equal(obj1, obj2,
                  expected_type=Principal,
                  deep_fields={'roles': assert_role_equal})


def assert_request_equal(obj1, obj2):
    """Assert that two requests are 'equal'.

    This is the most complicated due to how we serialize parent and children
    requests to avoid reference loops.

    Parent fields will not serialize their children. That's why compare_parent
    asserts that the children field is None.

    The requests in the children field will not serialize their parents or
    children. That's why compare_child asserts that both the parent and
    children fields are None.
    """
    def assert_all_none(*args):
        for arg in args:
            assert arg is None

    # Parent requests will not serialize their children since that's a loop
    def compare_parent(req1, req2):
        _assert_equal(req1, req2,
                      expected_type=Request,
                      deep_fields={
                          'children': assert_all_none,
                      })

    # Child requests will not serialize their parent since that's also a loop
    # They also don't serialize their children for performance reasons
    def compare_child(req1, req2):
        _assert_equal(req1, req2,
                      expected_type=Request,
                      deep_fields={
                          'children': assert_all_none,
                          'parent': assert_all_none,
                      })

    _assert_equal(obj1, obj2,
                  expected_type=Request,
                  deep_fields={
                      'children': compare_child,
                      'parent': compare_parent,
                  })


def assert_role_equal(obj1, obj2):
    _assert_equal(obj1, obj2,
                  expected_type=Role,
                  deep_fields={'roles': assert_role_equal})


def assert_system_equal(obj1, obj2):
    _assert_equal(obj1, obj2,
                  expected_type=System,
                  deep_fields={
                      'commands': assert_command_equal,
                      'instances': assert_instance_equal,
                  })


def assert_job_equal(obj1, obj2):
    _assert_equal(obj1, obj2,
                  expected_type=Job,
                  deep_fields={
                      'trigger': assert_trigger_equal,
                      'request_template': assert_request_template_equal,
                  })
