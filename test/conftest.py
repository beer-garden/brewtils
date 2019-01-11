# -*- coding: utf-8 -*-

import brewtils.test

pytest_plugins = ["brewtils.test.fixtures"]


def pytest_configure():
    setattr(brewtils.test, "_running_tests", True)


def pytest_unconfigure():
    delattr(brewtils.test, "_running_tests")
