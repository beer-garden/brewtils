# -*- coding: utf-8 -*-
"""Module to simplify model comparisons.

WARNING: This module was created to simplify testing. As such, it's not recommended for
production use.

ANOTHER WARNING: This module subject to change outside of the normal deprecation cycle.

Seriously, this is a 'use at your own risk' kind of thing.

"""
from functools import partial

import brewtils.test
from brewtils.models import (
    System, Command, Instance, Parameter, Request, PatchOperation,
    LoggingConfig, Event, Queue, Choices, Principal, Role, Job, IntervalTrigger,
    DateTrigger, CronTrigger, RequestTemplate
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
    """Assert that two objects are equal.

    Args:
        obj1: The first object
        obj2: The second object
        expected_type: Both objects will be checked (using isinstance) against this type
        deep_fields: A dictionary of field name to comparison function

    Returns:
        None

    Raises:
        AssertionError: A comparison assertion failed

    """
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


def _assert_wrapper(*args, **kwargs):
    """Wrapper that will translate AssertionError to a boolean.

    This is a safety measure in case these functions are used outside of a testing
    context. This isn't recommended, but naked asserts are still unacceptable in any
    packaged code. This method will translate the various comparision functions to a
    simple boolean return.

    Note that in a testing context the AssertionError is re-raised. This is because it's
    much more helpful to know the specific assertion that failed, as it could be
    something nested several levels deep.

    Args:
        *args:
        **kwargs:

    Returns:

    """
    do_raise = kwargs.pop('nested')

    try:
        _assert_equal(*args, **kwargs)
    except AssertionError:
        if do_raise or hasattr(brewtils.test, '_running_tests'):
            raise
        return False

    return True


# These are the 'simple' models - they don't have any nested models as fields
assert_instance_equal = partial(
    _assert_wrapper, expected_type=Instance, nested=False,
)
assert_choices_equal = partial(
    _assert_wrapper, expected_type=Choices, nested=False,
)
assert_patch_equal = partial(
    _assert_wrapper, expected_type=PatchOperation, nested=False,
)
assert_logging_config_equal = partial(
    _assert_wrapper, expected_type=LoggingConfig, nested=False,
)
assert_event_equal = partial(
    _assert_wrapper, expected_type=Event, nested=False,
)
assert_queue_equal = partial(
    _assert_wrapper, expected_type=Queue, nested=False,
)
assert_request_template_equal = partial(
    _assert_wrapper, expected_type=RequestTemplate, nested=False,
)
assert_trigger_equal = partial(
    _assert_wrapper,
    expected_type=(CronTrigger, DateTrigger, IntervalTrigger),
    nested=False,
)


def assert_command_equal(obj1, obj2, nested=False):

    # Command's system field only serializes the system's id
    def compare_system(sys1, sys2):
        assert sys1.id == sys2.id

    return _assert_wrapper(
        obj1, obj2,
        expected_type=Command,
        deep_fields={
            'parameters': partial(assert_parameter_equal, nested=True),
            'system': compare_system,
        },
        nested=nested,
    )


def assert_parameter_equal(obj1, obj2, nested=False):
    return _assert_wrapper(
        obj1, obj2,
        expected_type=Parameter,
        deep_fields={
            'parameters': partial(assert_parameter_equal, nested=True),
            'choices': partial(assert_choices_equal, nested=True),
        },
        nested=nested,
    )


def assert_principal_equal(obj1, obj2, nested=False):
    return _assert_wrapper(
        obj1, obj2,
        expected_type=Principal,
        deep_fields={
            'roles': partial(assert_role_equal, nested=True),
        },
        nested=nested,
    )


def assert_request_equal(obj1, obj2, nested=False):
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
        _assert_wrapper(
            req1, req2,
            expected_type=Request,
            deep_fields={
                'children': assert_all_none,
            },
            nested=True,
        )

    # Child requests will not serialize their parent since that's also a loop
    # They also don't serialize their children for performance reasons
    def compare_child(req1, req2):
        _assert_wrapper(
            req1, req2,
            expected_type=Request,
            deep_fields={
                'children': assert_all_none,
                'parent': assert_all_none,
            },
            nested=True,
        )

    return _assert_wrapper(
        obj1, obj2,
        expected_type=Request,
        deep_fields={
            'children': compare_child,
            'parent': compare_parent,
        },
        nested=nested,
    )


def assert_role_equal(obj1, obj2, nested=False):
    return _assert_wrapper(
        obj1, obj2,
        expected_type=Role,
        deep_fields={'roles': partial(assert_role_equal, nested=True)},
        nested=nested,
    )


def assert_system_equal(obj1, obj2, nested=False):
    return _assert_wrapper(
        obj1, obj2,
        expected_type=System,
        deep_fields={
            'commands': partial(assert_command_equal, nested=True),
            'instances': partial(assert_instance_equal, nested=True),
        },
        nested=nested,
    )


def assert_job_equal(obj1, obj2, nested=False):
    return _assert_wrapper(
        obj1, obj2,
        expected_type=Job,
        deep_fields={
            'trigger': partial(assert_trigger_equal, nested=True),
            'request_template': partial(assert_request_template_equal, nested=True),
        },
        nested=nested,
    )
