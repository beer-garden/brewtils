# -*- coding: utf-8 -*-
import sys

import pytest

import brewtils.test

pytest_plugins = ["brewtils.test.fixtures"]


def pytest_configure():
    setattr(brewtils.test, "_running_tests", True)


def pytest_unconfigure():
    delattr(brewtils.test, "_running_tests")


@pytest.hookimpl(hookwrapper=True)
def pytest_collect_file(path):
    outcome = yield

    if sys.version_info < (3, 6) and path.basename == "type_hint_test.py":
        outcome.get_result().pop()
