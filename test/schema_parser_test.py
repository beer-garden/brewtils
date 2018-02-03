from __future__ import unicode_literals
# Doing this because marshmallow uses unicode when it serializes things to dictionaries

# Detailed explanation:
# When everything works (the dictionary comparisons are good) it's fine, but if there's a problem (like a new field
# was added to the data model and not to the test object here) then the diff output between the two dictionaries will
# be enormous (because the serialized keys are unicode and the literals in this file aren't). It's kind of weird that
# there's a 'difference' that doesn't fail the comparison but does show up in the diff if the comparison fails, but
# that's the way it is :/

import copy
import unittest
import warnings
from datetime import datetime

from marshmallow.exceptions import MarshmallowError

from brewtils.models import Command, Instance, Parameter, Request, System, PatchOperation, Choices, LoggingConfig,\
    Event, Queue
from brewtils.schema_parser import SchemaParser, BrewmasterSchemaParser
from test.utils.comparable import assert_parameter_equal, assert_command_equal, assert_system_equal, \
    assert_instance_equal, assert_request_equal, assert_patch_equal, assert_logging_config_equal, assert_event_equal, \
    assert_queue_equal


class SchemaParserTest(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.parser = SchemaParser()

        nested_parameter_dict = {
            'key': 'nested', 'type': None, 'multi': None, 'display_name': None, 'optional': None,
            'default': None, 'description': None, 'choices': None, 'parameters': [],
            'nullable': None, 'maximum': None, 'minimum': None, 'regex': None,
            'form_input_type': None,
        }

        self.parameter_dict = {
            'key': 'key',
            'type': 'Any',
            'multi': False,
            'display_name': 'display',
            'optional': True,
            'default': 'default',
            'description': 'desc',
            'choices': {'display': 'select', 'strict': True, 'type': 'static', 'value': ['choiceA', 'choiceB'],
                        'details': {}},
            'parameters': [nested_parameter_dict],
            'nullable': False,
            'maximum': 10,
            'minimum': 1,
            'regex': '.*',
            'form_input_type': None
        }
        self.parameter = Parameter('key', type='Any', multi=False, display_name='display', optional=True,
                                   default='default', description='desc', nullable=False, regex='.*',
                                   parameters=[Parameter('nested')], maximum=10, minimum=1,
                                   choices=Choices(type='static', value=['choiceA', 'choiceB'], strict=True,
                                                   display='select', details={}),
                                   form_input_type=None)

        # Need to set the system after we declare the system...
        self.command_dict = {
            'name': 'name',
            'description': 'desc',
            'id': '123f11af55a38e64799f1234',
            'parameters': [self.parameter_dict],
            'command_type': 'ACTION',
            'output_type': 'STRING',
            'schema': {},
            'form': {},
            'template': '<html></html>',
            'icon_name': 'icon!',
            'system': None  # Set at the bottom of __init__
        }
        self.command = Command('name', description='desc', id='123f11af55a38e64799f1234', parameters=[self.parameter],
                               command_type='ACTION', output_type='STRING', schema={}, form={},
                               template='<html></html>', icon_name='icon!', system=None)

        self.instance_dict = {
            'id': '584f11af55a38e64799fd1d4',
            'name': 'default',
            'description': 'desc',
            'status': 'RUNNING',
            'icon_name': 'icon!',
            'queue_type': 'rabbitmq',
            'queue_info': {'queue': 'abc[default]-0.0.1', 'url': 'amqp://guest:guest@localhost:5672'},
            'status_info': {'heartbeat': 1451606400000},
            'metadata': {}
        }
        self.instance = Instance(id='584f11af55a38e64799fd1d4', name='default', description='desc', status='RUNNING',
                                 icon_name='icon!', status_info={'heartbeat': datetime(2016, 1, 1)},
                                 metadata={}, queue_type='rabbitmq',
                                 queue_info={'queue': 'abc[default]-0.0.1', 'url': 'amqp://guest:guest@localhost:5672'})

        self.system_dict = {
            'name': 'name',
            'description': 'desc',
            'version': '1.0.0',
            'id': '584f11af55a38e64799f1234',
            'max_instances': 1,
            'instances': [self.instance_dict],
            'commands': [self.command_dict],
            'icon_name': 'fa-beer',
            'display_name': 'non-offensive',
            'metadata': {'some': 'stuff'}
        }
        self.system = System(name='name', description='desc', version='1.0.0', id='584f11af55a38e64799f1234',
                             max_instances=1, instances=[self.instance], commands=[self.command], icon_name='fa-beer',
                             display_name='non-offensive', metadata={'some': 'stuff'})

        self.child_request_dict = {
            'system': 'child_system',
            'system_version': '1.0.0',
            'instance_name': 'default',
            'command': 'say',
            'id': '58542eb571afd47ead90d25f',
            'parameters': {},
            'comment': 'bye!',
            'output': 'nested output',
            'output_type': 'STRING',
            'status': 'CREATED',
            'command_type': 'ACTION',
            'created_at': 1451606400000,
            'updated_at': 1451606400000,
            'error_class': None,
            'metadata': {'child': 'stuff'}
        }
        self.child_request =\
            Request(system='child_system', system_version='1.0.0', instance_name='default', command='say',
                    id='58542eb571afd47ead90d25f', parent=None, children=None, parameters={}, comment='bye!',
                    output='nested output', output_type='STRING', status='CREATED', command_type='ACTION',
                    created_at=datetime(2016, 1, 1), error_class=None, metadata={'child': 'stuff'},
                    updated_at=datetime(2016, 1, 1))

        self.parent_request_dict = {
            'system': 'parent_system',
            'system_version': '1.0.0',
            'instance_name': 'default',
            'command': 'say',
            'id': '58542eb571afd47ead90d25f',
            'parent': None,
            'parameters': {},
            'comment': 'bye!',
            'output': 'nested output',
            'output_type': 'STRING',
            'status': 'CREATED',
            'command_type': 'ACTION',
            'created_at': 1451606400000,
            'updated_at': 1451606400000,
            'error_class': None,
            'metadata': {'parent': 'stuff'}
        }
        self.parent_request =\
            Request(system='parent_system', system_version='1.0.0', instance_name='default', command='say',
                    id='58542eb571afd47ead90d25f', parent=None, children=None, parameters={}, comment='bye!',
                    output='nested output', output_type='STRING', status='CREATED', command_type='ACTION',
                    created_at=datetime(2016, 1, 1), error_class=None, metadata={'parent': 'stuff'},
                    updated_at=datetime(2016, 1, 1))

        self.request_dict = {
            'system': 'system',
            'system_version': '1.0.0',
            'instance_name': 'default',
            'command': 'speak',
            'id': '58542eb571afd47ead90d25e',
            'parent': self.parent_request_dict,
            'children': [self.child_request_dict],
            'parameters': {'message': 'hey!'},
            'comment': 'hi!',
            'output': 'output',
            'output_type': 'STRING',
            'status': 'CREATED',
            'command_type': 'ACTION',
            'created_at': 1451606400000,
            'updated_at': 1451606400000,
            'error_class': 'ValueError',
            'metadata': {'request': 'stuff'}
        }
        self.request =\
            Request(system='system', system_version='1.0.0', instance_name='default', command='speak',
                    id='58542eb571afd47ead90d25e', parent=self.parent_request, children=[self.child_request],
                    parameters={'message': 'hey!'}, comment='hi!', output='output', output_type='STRING',
                    status='CREATED', command_type='ACTION', created_at=datetime(2016, 1, 1), error_class='ValueError',
                    metadata={'request': 'stuff'}, updated_at=datetime(2016, 1, 1))

        self.patch_dict = {'operations': [{'operation': 'replace', 'path': '/status', 'value': 'RUNNING'}]}
        self.patch_many_dict = {'operations': [
            {'operation': 'replace', 'path': '/status', 'value': 'RUNNING'},
            {'operation': 'replace2', 'path': '/status2', 'value': 'RUNNING2'}
        ]}
        self.patch_no_envelope_dict = {'operation': 'replace', 'path': '/status', 'value': 'RUNNING'}
        self.patch1 = PatchOperation(operation='replace', path='/status', value='RUNNING')
        self.patch2 = PatchOperation(operation='replace2', path='/status2', value='RUNNING2')

        self.logging_config_dict = {
            "level": "INFO",
            "handlers": {"stdout": {"foo": "bar"}},
            "formatters": {"default": {"format": LoggingConfig.DEFAULT_FORMAT}}
        }
        self.logging_config = LoggingConfig(level="INFO",
                                            handlers={"stdout": {"foo": "bar"}},
                                            formatters={"default": {"format": LoggingConfig.DEFAULT_FORMAT}})

        self.event_dict = {
            'name': 'REQUEST_CREATED',
            'error': False,
            'payload': {'id': '58542eb571afd47ead90d25e'},
            'metadata': {'extra': 'info'},
            'timestamp': 1451606400000
        }
        self.event = Event(name='REQUEST_CREATED', error=False, payload={'id': '58542eb571afd47ead90d25e'},
                           metadata={'extra': 'info'}, timestamp=datetime(2016, 1, 1))

        self.queue_dict = {
            'name': 'echo.1-0-0.default',
            'system': 'echo',
            'version': '1.0.0',
            'instance': 'default',
            'system_id': '1234',
            'display': 'foo.1-0-0.default',
            'size': 3
        }
        self.queue = Queue(name='echo.1-0-0.default', system='echo', version='1.0.0', instance='default',
                           system_id='1234', display='foo.1-0-0.default', size=3)

        # Finish setting up our circular system <-> command dependency
        self.command.system = self.system
        self.command_dict['system'] = {'id': self.system.id}

        # Finish setting up our circular request parent <-> dependencies
        self.child_request.parent = self.request
        self.parent_request.children = [self.request]

    def test_parse_none(self):
        self.assertRaises(TypeError, self.parser.parse_system, None, from_string=True)
        self.assertRaises(TypeError, self.parser.parse_system, None, from_string=False)

    def test_parse_empty(self):
        self.parser.parse_system({}, from_string=False)
        self.parser.parse_system('{}', from_string=True)

    def test_parse_error(self):
        self.assertRaises(ValueError, self.parser.parse_system, '', from_string=True)
        self.assertRaises(ValueError, self.parser.parse_system, 'bad bad bad', from_string=True)

    def test_parse_bad_input_type(self):
        self.assertRaises(TypeError, self.parser.parse_system, ['list', 'is', 'bad'], from_string=True)
        self.assertRaises(TypeError, self.parser.parse_system, {'bad': 'bad bad'}, from_string=True)

    def test_parse_fail_validation(self):
        self.system_dict['name'] = None
        self.assertRaises(MarshmallowError, self.parser.parse_system, self.system_dict)
        self.assertRaises(MarshmallowError, self.parser.parse_system, 'bad bad bad', from_string=False)

    def test_parse_non_strict_failure(self):
        self.system_dict['name'] = None
        self.parser.parse_system(self.system_dict, from_string=False, strict=False)

    def test_no_modify_arguments(self):
        system_copy = copy.deepcopy(self.system_dict)
        self.parser.parse_system(self.system_dict)
        self.assertEqual(system_copy, self.system_dict)

    def test_parse_system(self):
        assert_system_equal(self.system, self.parser.parse_system(self.system_dict), True)

    def test_parse_instance(self):
        assert_instance_equal(self.instance, self.parser.parse_instance(self.instance_dict), True)

    def test_parse_command(self):
        assert_command_equal(self.command, self.parser.parse_command(self.command_dict), True)

    def test_parse_parameter(self):
        assert_parameter_equal(self.parameter, self.parser.parse_parameter(self.parameter_dict), True)

    def test_parse_request(self):
        assert_request_equal(self.request, self.parser.parse_request(self.request_dict), True)

    def test_parse_patch(self):
        assert_patch_equal(self.patch1, self.parser.parse_patch(self.patch_dict)[0], True)

    def test_parse_patch_ignore_many(self):
        assert_patch_equal(self.patch1, self.parser.parse_patch(self.patch_dict, many=False)[0], True)

    def test_parse_patch_no_envelope(self):
        assert_patch_equal(self.parser.parse_patch(self.patch_no_envelope_dict)[0], self.patch1)

    def test_parse_many_patch_no_envelope(self):
        assert_patch_equal(self.parser.parse_patch([self.patch_no_envelope_dict])[0], self.patch1)

    def test_parse_patch_many(self):
        patches = sorted(self.parser.parse_patch(self.patch_many_dict, many=True), key=lambda x: x.operation)
        for index, patch in enumerate([self.patch1, self.patch2]):
            assert_patch_equal(patch, patches[index])

    def test_parse_logging_config(self):
        assert_logging_config_equal(self.logging_config, self.parser.parse_logging_config(self.logging_config_dict))

    def test_parse_logging_config_ignore_many(self):
        assert_logging_config_equal(self.logging_config, self.parser.parse_logging_config(self.logging_config_dict,
                                                                                          many=True))

    def test_parse_event(self):
        assert_event_equal(self.event, self.parser.parse_event(self.event_dict))

    def test_parse_queue(self):
        assert_queue_equal(self.queue, self.parser.parse_queue(self.queue_dict))

    def test_serialize_system(self):
        self.assertEqual(self.system_dict, self.parser.serialize_system(self.system, to_string=False))

    def test_serialize_system_no_commands(self):
        self.system_dict.pop('commands')
        self.assertEqual(self.system_dict, self.parser.serialize_system(self.system, to_string=False,
                                                                        include_commands=False))

    def test_serialize_system_no_commands_other_excludes(self):
        self.system_dict.pop('commands')
        self.system_dict.pop('icon_name')
        self.assertEqual(self.system_dict, self.parser.serialize_system(self.system, to_string=False,
                                                                        include_commands=False, exclude=('icon_name',)))

    def test_serialize_instance(self):
        self.assertEqual(self.instance_dict, self.parser.serialize_instance(self.instance, to_string=False))

    def test_serialize_command(self):
        self.assertEqual(self.command_dict, self.parser.serialize_command(self.command, to_string=False))

    def test_serialize_parameter(self):
        self.assertEqual(self.parameter_dict, self.parser.serialize_parameter(self.parameter, to_string=False))

    def test_serialize_request(self):
        self.assertEqual(self.request_dict, self.parser.serialize_request(self.request, to_string=False))

    def test_serialize_patch(self):
        self.assertEqual(self.patch_dict, self.parser.serialize_patch(self.patch1, to_string=False, many=False))

    def test_serialize_patch_many(self):
        self.assertEqual(self.patch_many_dict,
                         self.parser.serialize_patch([self.patch1, self.patch2], to_string=False, many=True))

    def test_serialize_logging_config(self):
        self.assertEqual(self.logging_config_dict,
                         self.parser.serialize_logging_config(self.logging_config, to_string=False))

    def test_serialize_event(self):
        self.assertEqual(self.event_dict,
                         self.parser.serialize_event(self.event, to_string=False))

    def test_serialize_queue(self):
        self.assertEqual(self.queue_dict,
                         self.parser.serialize_queue(self.queue, to_string=False))


class BrewmasterSchemaParserTest(unittest.TestCase):

    def test_deprecation(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')

            BrewmasterSchemaParser()
            self.assertEqual(1, len(w))

            warning = w[0]
            self.assertEqual(warning.category, DeprecationWarning)
            self.assertIn("'BrewmasterSchemaParser'", str(warning))
            self.assertIn("'SchemaParser'", str(warning))
            self.assertIn('3.0', str(warning))
