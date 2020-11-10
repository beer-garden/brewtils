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
    Choices,
    Command,
    CronTrigger,
    DateTrigger,
    Event,
    Garden,
    Instance,
    IntervalTrigger,
    Job,
    LoggingConfig,
    Operation,
    Parameter,
    PatchOperation,
    Principal,
    Queue,
    Request,
    RequestFile,
    RequestTemplate,
    Role,
    System,
)

__all__ = [
    "assert_instance_equal",
    "assert_choices_equal",
    "assert_patch_equal",
    "assert_logging_config_equal",
    "assert_event_equal",
    "assert_queue_equal",
    "assert_request_template_equal",
    "assert_trigger_equal",
    "assert_command_equal",
    "assert_parameter_equal",
    "assert_principal_equal",
    "assert_request_equal",
    "assert_role_equal",
    "assert_system_equal",
    "assert_job_equal",
    "assert_request_file_equal",
    "assert_operation_equal",
]


def _assert(condition, message):
    """Helper to ensure AssertionError is always raised.

    If assertions are disabled (python -O) then using these assertions in production
    would result in them always returning True, which is Very Bad.

    Using this wrapper here prevents that.
    """
    if not condition:
        raise AssertionError(message)


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
        _assert(
            isinstance(obj1, expected_type),
            "type mismatch for obj1: expected '{0}' but was '{1}'".format(
                expected_type, type(obj1)
            ),
        )
        _assert(
            isinstance(obj2, expected_type),
            "type mismatch for obj2: expected '{0}' but was '{1}'".format(
                expected_type, type(obj2)
            ),
        )
    _assert(type(obj1) is type(obj2), "obj1 and obj2 are not the same type.")

    for key in obj1.__dict__.keys():
        _assert(hasattr(obj1, key), "obj1 does not have an attribute '%s'" % key)
        _assert(hasattr(obj2, key), "obj2 does not have an attribute '%s'" % key)

        if key not in deep_fields.keys():
            _assert(
                getattr(obj1, key) == getattr(obj2, key),
                "%s was not the same (%s, %s)"
                % (key, getattr(obj1, key), getattr(obj2, key)),
            )
        else:
            nested1 = getattr(obj1, key)
            nested2 = getattr(obj2, key)

            if isinstance(nested1, list) and isinstance(nested2, list):
                l1 = sorted(getattr(obj1, key), key=lambda x: str(x))
                l2 = sorted(getattr(obj2, key), key=lambda x: str(x))

                _assert(
                    len(l1) == len(l2), "Length of list field %s was different" % key
                )

                for item1, item2 in zip(l1, l2):
                    deep_fields[key](item1, item2)
            else:
                deep_fields[key](nested1, nested2)


def _assert_wrapper(obj1, obj2, do_raise=False, **kwargs):
    """Wrapper that will translate AssertionError to a boolean.

    This is a safety measure in case these functions are used outside of a testing
    context. This isn't recommended, but naked asserts are still unacceptable in any
    packaged code. This method will translate the various comparison functions to a
    simple boolean return.

    Note that in a testing context the AssertionError is re-raised. This is because it's
    much more helpful to know the specific assertion that failed, as it could be
    something nested several levels deep.

    Args:
        obj1: Passed through to _assert_equal
        obj2: Passed through to _assert_equal
        do_raise: If True, re-raise any raised AssertionError. This helps with nested
            comparisons.
        **kwargs: Passed through to _assert_equal

    Returns:
        True if the comparison was equal.
        False if:
            - The comparison was not equal and
            - do_raise is False and
            - called from outside of a testing context

    Raises:
        AssertionError:
            The comparison was not equal. Assertion will be translated to a boolean
            False if do_raise is False and called from outside of a testing context.

    """
    try:
        _assert_equal(obj1, obj2, **kwargs)
    except AssertionError:
        if do_raise or hasattr(brewtils.test, "_running_tests"):
            raise
        return False

    return True


# These are the 'simple' models - they don't have any nested models as fields
assert_instance_equal = partial(_assert_wrapper, expected_type=Instance)
assert_choices_equal = partial(_assert_wrapper, expected_type=Choices)
assert_patch_equal = partial(_assert_wrapper, expected_type=PatchOperation)
assert_logging_config_equal = partial(_assert_wrapper, expected_type=LoggingConfig)
assert_queue_equal = partial(_assert_wrapper, expected_type=Queue)
assert_request_template_equal = partial(_assert_wrapper, expected_type=RequestTemplate)
assert_trigger_equal = partial(
    _assert_wrapper, expected_type=(CronTrigger, DateTrigger, IntervalTrigger)
)
assert_request_file_equal = partial(_assert_wrapper, expected_type=RequestFile)


def assert_command_equal(obj1, obj2, do_raise=False):

    return _assert_wrapper(
        obj1,
        obj2,
        expected_type=Command,
        deep_fields={"parameters": partial(assert_parameter_equal, do_raise=True)},
        do_raise=do_raise,
    )


def assert_parameter_equal(obj1, obj2, do_raise=False):
    return _assert_wrapper(
        obj1,
        obj2,
        expected_type=Parameter,
        deep_fields={
            "parameters": partial(assert_parameter_equal, do_raise=True),
            "choices": partial(assert_choices_equal, do_raise=True),
        },
        do_raise=do_raise,
    )


def assert_event_equal(obj1, obj2, do_raise=False):

    _assert(obj1.payload_type == obj2.payload_type, "Payload types were not equal")

    comparison_func_name = "_assert_wrapper"
    if obj1.payload_type:
        comparison_func_name = "assert_%s_equal" % obj1.payload_type.lower()

    payload_compare = getattr(brewtils.test.comparable, comparison_func_name)

    return _assert_wrapper(
        obj1,
        obj2,
        expected_type=Event,
        deep_fields={"payload": partial(payload_compare, do_raise=True)},
        do_raise=do_raise,
    )


def assert_principal_equal(obj1, obj2, do_raise=False):
    return _assert_wrapper(
        obj1,
        obj2,
        expected_type=Principal,
        deep_fields={"roles": partial(assert_role_equal, do_raise=True)},
        do_raise=do_raise,
    )


def assert_request_equal(obj1, obj2, do_raise=False):
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
            _assert(arg is None, "")

    # Parent requests will not serialize their children since that's a loop
    def compare_parent(req1, req2):
        _assert_wrapper(
            req1,
            req2,
            expected_type=Request,
            deep_fields={"children": assert_all_none},
            do_raise=True,
        )

    # Child requests will not serialize their parent since that's also a loop
    # They also don't serialize their children for performance reasons
    def compare_child(req1, req2):
        _assert_wrapper(
            req1,
            req2,
            expected_type=Request,
            deep_fields={"children": assert_all_none, "parent": assert_all_none},
            do_raise=True,
        )

    return _assert_wrapper(
        obj1,
        obj2,
        expected_type=Request,
        deep_fields={"children": compare_child, "parent": compare_parent},
        do_raise=do_raise,
    )


def assert_role_equal(obj1, obj2, do_raise=False):
    return _assert_wrapper(
        obj1,
        obj2,
        expected_type=Role,
        deep_fields={"roles": partial(assert_role_equal, do_raise=True)},
        do_raise=do_raise,
    )


def assert_system_equal(obj1, obj2, do_raise=False):
    return _assert_wrapper(
        obj1,
        obj2,
        expected_type=System,
        deep_fields={
            "commands": partial(assert_command_equal, do_raise=True),
            "instances": partial(assert_instance_equal, do_raise=True),
        },
        do_raise=do_raise,
    )


def assert_job_equal(obj1, obj2, do_raise=False):
    return _assert_wrapper(
        obj1,
        obj2,
        expected_type=Job,
        deep_fields={
            "trigger": partial(assert_trigger_equal, do_raise=True),
            "request_template": partial(assert_request_template_equal, do_raise=True),
        },
        do_raise=do_raise,
    )


def assert_operation_equal(obj1, obj2, do_raise=False):

    _assert(obj1.model_type == obj2.model_type, "Model types were not equal")

    comparison_func_name = "_assert_wrapper"
    if obj1.model_type:
        comparison_func_name = "assert_%s_equal" % obj1.model_type.lower()

    model_compare = getattr(brewtils.test.comparable, comparison_func_name)

    return _assert_wrapper(
        obj1,
        obj2,
        expected_type=Operation,
        deep_fields={"model": partial(model_compare, do_raise=True)},
        do_raise=do_raise,
    )


def assert_garden_equal(obj1, obj2, do_raise=False):
    return _assert_wrapper(
        obj1,
        obj2,
        expected_type=Garden,
        deep_fields={"systems": partial(assert_system_equal, do_raise=True)},
        do_raise=do_raise,
    )
