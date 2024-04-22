# -*- coding: utf-8 -*-

import pytest
from mock import Mock

from brewtils.errors import RequestProcessException
from brewtils.resolvers.manager import ResolutionManager


@pytest.fixture
def resolver_mock():
    r = Mock()
    r.should_upload.return_value = False
    r.should_download.return_value = False
    return r


@pytest.fixture
def manager(resolver_mock):
    m = ResolutionManager()
    m.resolvers = [resolver_mock]
    return m


class TestBasic(object):
    """Tests with no resolution necessary"""

    def test_simple(self, manager, bg_command):
        values = {"message": "hi"}

        # Need to clear out nested parameters otherwise this is a model parameter
        for param in bg_command.parameters:
            param.parameters = None

        resolved = manager.resolve(values, definitions=bg_command.parameters)
        assert resolved == values

    def test_nested(self, manager, bg_command):
        values = {"message": {"nested": "hi"}}

        resolved = manager.resolve(values, definitions=bg_command.parameters)
        assert resolved == values

    def test_multi(self, manager, bg_command):
        values = {"message": ["hi", "bye"]}

        # Make this non-nested multi
        for param in bg_command.parameters:
            param.parameters = None
            param.multi = True

        resolved = manager.resolve(values, definitions=bg_command.parameters)
        assert resolved == values

    def test_multi_nested(self, manager, bg_command):
        values = {"message": [{"nested": "hi"}, {"nested": "bye"}]}

        # Make this multi
        for param in bg_command.parameters:
            param.multi = True

        resolved = manager.resolve(values, definitions=bg_command.parameters)
        assert resolved == values


class TestSimpleResolve(object):
    """Test non-nested, non-multi resolution"""

    def test_upload(
        self, manager, resolver_mock, bg_command, resolvable_dict, bg_resolvable
    ):
        resolver_mock.should_upload.return_value = True
        resolver_mock.upload.return_value = bg_resolvable

        # Need to clear out nested parameters otherwise this is a model parameter
        for param in bg_command.parameters:
            param.parameters = None

        resolved = manager.resolve(
            {"message": "hi"}, definitions=bg_command.parameters, upload=True
        )

        assert resolved == {"message": resolvable_dict}

    def test_download(
        self, manager, resolver_mock, bg_command, resolvable_dict, bg_resolvable
    ):
        resolver_mock.should_download.return_value = True
        resolver_mock.download.return_value = "hi"

        # Need to clear out nested parameters otherwise this is a model parameter
        for param in bg_command.parameters:
            param.parameters = None

        resolved = manager.resolve(
            {"message": resolvable_dict},
            definitions=bg_command.parameters,
            upload=False,
        )

        assert resolved == {"message": "hi"}

    def test_download_value_none(
        self, manager, resolver_mock, bg_command, bg_resolvable
    ):
        resolver_mock.should_download.return_value = True

        # Need to clear out nested parameters otherwise this is a model parameter
        for param in bg_command.parameters:
            param.parameters = None

        resolved = manager.resolve(
            {"message": None},
            definitions=bg_command.parameters,
            upload=False,
        )

        assert resolved == {"message": None}


class TestNestedResolve(object):
    """Test nested, non-multi"""

    def test_upload(
        self, manager, resolver_mock, bg_command, resolvable_dict, bg_resolvable
    ):
        resolver_mock.should_upload.return_value = True
        resolver_mock.upload.return_value = bg_resolvable

        resolved = manager.resolve(
            {"message": {"nested": "hi"}},
            definitions=bg_command.parameters,
            upload=True,
        )

        assert resolved == {"message": {"nested": resolvable_dict}}

    def test_download(
        self, manager, resolver_mock, bg_command, resolvable_dict, bg_resolvable
    ):
        resolver_mock.should_download.return_value = True
        resolver_mock.download.return_value = "hi"

        resolved = manager.resolve(
            {"message": {"nested": resolvable_dict}},
            definitions=bg_command.parameters,
            upload=False,
        )

        assert resolved == {"message": {"nested": "hi"}}


class TestMultiResolve(object):
    """Test non-nested, multi"""

    def test_upload(
        self, manager, resolver_mock, bg_command, resolvable_dict, bg_resolvable
    ):
        resolver_mock.should_upload.return_value = True
        resolver_mock.upload.return_value = bg_resolvable

        # Clear out nested params, make this a multi
        for param in bg_command.parameters:
            param.parameters = None
            param.multi = True

        resolved = manager.resolve(
            {"message": ["hi", "bye"]},
            definitions=bg_command.parameters,
            upload=True,
        )

        assert resolved == {"message": [resolvable_dict, resolvable_dict]}

    def test_download(
        self, manager, resolver_mock, bg_command, resolvable_dict, bg_resolvable
    ):
        resolver_mock.should_download.return_value = True
        resolver_mock.download.return_value = "hi"

        # Clear out nested params, make this a multi
        for param in bg_command.parameters:
            param.parameters = None
            param.multi = True

        resolved = manager.resolve(
            {"message": [resolvable_dict, resolvable_dict]},
            definitions=bg_command.parameters,
            upload=False,
        )

        assert resolved == {"message": ["hi", "hi"]}


class TestNestedMultiResolve(object):
    """Test nested, multi"""

    def test_upload(
        self, manager, resolver_mock, bg_command, resolvable_dict, bg_resolvable
    ):
        resolver_mock.should_upload.return_value = True
        resolver_mock.upload.return_value = bg_resolvable

        # Make this a multi
        for param in bg_command.parameters:
            param.multi = True

        resolved = manager.resolve(
            {"message": [{"nested": "hi"}, {"nested": "bye"}]},
            definitions=bg_command.parameters,
            upload=True,
        )

        assert resolved == {
            "message": [{"nested": resolvable_dict}, {"nested": resolvable_dict}]
        }

    def test_download(
        self, manager, resolver_mock, bg_command, resolvable_dict, bg_resolvable
    ):
        resolver_mock.should_download.return_value = True
        resolver_mock.download.return_value = "hi"

        # Make this a multi
        for param in bg_command.parameters:
            param.multi = True

        resolved = manager.resolve(
            {"message": [{"nested": resolvable_dict}, {"nested": resolvable_dict}]},
            definitions=bg_command.parameters,
            upload=False,
        )

        assert resolved == {"message": [{"nested": "hi"}, {"nested": "hi"}]}


class TestAnyParameters(object):
    """Tests with no resolution necessary"""

    def test_kwarg_simple(self, manager, bg_command):
        values = {"kwarg": "kwargs"}

        # Need to clear out nested parameters otherwise this is a model parameter
        for param in bg_command.parameters:
            param.parameters = None

        resolved = manager.resolve(
            values, definitions=bg_command.parameters, allow_any_parameter=True
        )
        assert resolved == values

    def test_mixed_kwarg(self, manager, bg_command):
        values = {"message": "hi", "kwarg": "kwargs"}

        # Need to clear out nested parameters otherwise this is a model parameter
        for param in bg_command.parameters:
            param.parameters = None

        resolved = manager.resolve(
            values, definitions=bg_command.parameters, allow_any_parameter=True
        )
        assert resolved == values

    def test_raise_error(self, manager, bg_command):
        values = {"message": "hi", "kwarg": "kwargs"}

        # Need to clear out nested parameters otherwise this is a model parameter
        for param in bg_command.parameters:
            param.parameters = None

        with pytest.raises(RequestProcessException):
            manager.resolve(
                values, definitions=bg_command.parameters, allow_any_parameter=False
            )
