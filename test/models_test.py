import unittest

from mock import Mock, PropertyMock

from brewtils.errors import ModelValidationError, RequestStatusTransitionError
from brewtils.models import Command, Instance, Parameter, PatchOperation, Request, System, \
    Choices, LoggingConfig, Event, Queue, Job, RequestTemplate


class CommandTest(unittest.TestCase):

    def test_parameter_keys(self):
        param1 = Parameter(key='key1', optional=False)
        param2 = Parameter(key='key2', optional=False)
        c = Command(name='foo', description='bar', parameters=[param1, param2])
        keys = c.parameter_keys()
        self.assertEqual(len(keys), 2)
        self.assertIn('key1', keys)
        self.assertIn('key2', keys)

    def test_get_parameter_by_key_none(self):
        c = Command(name='foo', description='bar')
        self.assertIsNone(c.get_parameter_by_key('some_key'))

    def test_get_parameter_by_key_true(self):
        param1 = Parameter(key='key1', optional=False)
        c = Command(name='foo', description='bar', parameters=[param1])
        self.assertEqual(c.get_parameter_by_key('key1'), param1)

    def test_get_parameter_by_key_False(self):
        param1 = Parameter(key='key1', optional=False)
        c = Command(name='foo', description='bar', parameters=[param1])
        self.assertIsNone(c.get_parameter_by_key('key2'))

    def test_has_different_parameters_different_length(self):
        c = Command(name='foo', description='bar')
        self.assertTrue(c.has_different_parameters([Parameter(key='key1', optional=False)]))

    def test_has_different_parameters_different_keys(self):
        param1 = Parameter(key='key1', type='String', multi=True, display_name='Key 1',
                           optional=True, default='key1',
                           description='this is key1')
        c = Command(name='foo', description='bar', parameters=[param1])
        param2 = Parameter(key='key2', type='String', multi=True, display_name='Key 1',
                           optional=True, default='key1',
                           description='this is key1')
        self.assertTrue(c.has_different_parameters([param2]))

    def test_has_different_parameters_different_type(self):
        param1 = Parameter(key='key1', type='String', multi=True, display_name='Key 1',
                           optional=True, default='key1',
                           description='this is key1')
        c = Command(name='foo', description='bar', parameters=[param1])
        param2 = Parameter(key='key1', type='Integer', multi=True, display_name='Key 1',
                           optional=True, default='key1',
                           description='this is key1')
        self.assertTrue(c.has_different_parameters([param2]))

    def test_has_different_parameters_different_multi(self):
        param1 = Parameter(key='key1', type='String', multi=True, display_name='Key 1',
                           optional=True, default='key1',
                           description='this is key1')
        c = Command(name='foo', description='bar', parameters=[param1])
        param2 = Parameter(key='key1', type='String', multi=False, display_name='Key 1',
                           optional=True, default='key1',
                           description='this is key1')
        self.assertTrue(c.has_different_parameters([param2]))

    def test_has_different_parameters_different_optional(self):
        param1 = Parameter(key='key1', type='String', multi=True, display_name='Key 1',
                           optional=True, default='key1',
                           description='this is key1')
        c = Command(name='foo', description='bar', parameters=[param1])
        param2 = Parameter(key='key1', type='String', multi=True, display_name='Key 1',
                           optional=False, default='key1',
                           description='this is key1')
        self.assertTrue(c.has_different_parameters([param2]))

    def test_has_different_parameters_different_default(self):
        param1 = Parameter(key='key1', type='String', multi=True, display_name='Key 1',
                           optional=True, default='key1',
                           description='this is key1')
        c = Command(name='foo', description='bar', parameters=[param1])
        param2 = Parameter(key='key1', type='String', multi=True, display_name='Key 1',
                           optional=True, default='key2',
                           description='this is key1')
        self.assertTrue(c.has_different_parameters([param2]))

    def test_has_different_parameters_different_maximum(self):
        param1 = Parameter(key='key1', type='String', multi=True, display_name='Key 1',
                           optional=True, default='key1',
                           maximum=10)
        c = Command(name='foo', description='bar', parameters=[param1])
        param2 = Parameter(key='key1', type='String', multi=True, display_name='Key 1',
                           optional=True, default='key1',
                           maximum=20)
        self.assertTrue(c.has_different_parameters([param2]))

    def test_has_different_parameters_different_minimum(self):
        param1 = Parameter(key='key1', type='String', multi=True, display_name='Key 1',
                           optional=True, default='key1',
                           minimum=10)
        c = Command(name='foo', description='bar', parameters=[param1])
        param2 = Parameter(key='key1', type='String', multi=True, display_name='Key 1',
                           optional=True, default='key1',
                           minimum=20)
        self.assertTrue(c.has_different_parameters([param2]))

    def test_has_different_parameters_different_regex(self):
        param1 = Parameter(key='key1', type='String', multi=False, display_name='Key 1',
                           optional=True, default='key1',
                           regex=r'.')
        c = Command(name='foo', description='bar', parameters=[param1])
        param2 = Parameter(key='key1', type='String', multi=False, display_name='Key 1',
                           optional=True, default='key1',
                           regex=r'.*')
        self.assertTrue(c.has_different_parameters([param2]))

    def test_has_different_parameters_different_order(self):
        param1 = Parameter(key='key1', type='String', multi=True, display_name='Key 1',
                           optional=True, default='key1',
                           description='this is key1')
        param2 = Parameter(key='key2', type='String', multi=True, display_name='Key 2',
                           optional=True, default='key2',
                           description='this is key2')

        c = Command(name='foo', description='bar', parameters=[param1, param2])
        self.assertFalse(c.has_different_parameters([param2, param1]))

    def test_has_different_parameters_false(self):
        param1 = Parameter(key='key1', type='String', multi=True, display_name='Key 1',
                           optional=True, default='key1',
                           description='this is key1')
        c = Command(name='foo', description='bar', parameters=[param1])
        param2 = Parameter(key='key1', type='String', multi=True, display_name='Key 1',
                           optional=True, default='key1',
                           description='this is key1')
        self.assertFalse(c.has_different_parameters([param2]))

    def test_str(self):
        c = Command(name='foo', description='bar', parameters=[])
        self.assertEqual('foo', str(c))

    def test_repr(self):
        c = Command(name='foo', description='bar', parameters=[])
        self.assertEqual('<Command: foo>', repr(c))


class InstanceTest(unittest.TestCase):

    def test_str(self):
        self.assertEqual('name', str(Instance(name='name')))

    def test_repr(self):
        instance = Instance(name='name', status='RUNNING')
        self.assertNotEqual(-1, repr(instance).find('name'))
        self.assertNotEqual(-1, repr(instance).find('RUNNING'))


class ChoicesTest(unittest.TestCase):

    def test_str(self):
        self.assertEqual('value', str(Choices(value='value')))

    def test_repr(self):
        choices = Choices(type='static', display='select', value=[1], strict=True)
        self.assertNotEqual(-1, repr(choices).find('static'))
        self.assertNotEqual(-1, repr(choices).find('select'))
        self.assertNotEqual(-1, repr(choices).find('[1]'))


class ParameterTest(unittest.TestCase):

    def test_status_fields(self):
        self.assertIn("String", Parameter.TYPES)
        self.assertIn("Integer", Parameter.TYPES)
        self.assertIn("Float", Parameter.TYPES)
        self.assertIn("Boolean", Parameter.TYPES)
        self.assertIn("Any", Parameter.TYPES)
        self.assertIn("Dictionary", Parameter.TYPES)
        self.assertIn("Date", Parameter.TYPES)
        self.assertIn("DateTime", Parameter.TYPES)

    def test_str(self):
        p = Parameter(key='foo', description='bar', type='Boolean', optional=False)
        self.assertEqual('foo', str(p))

    def test_repr(self):
        p = Parameter(key='foo', description='bar', type='Boolean', optional=False)
        self.assertEqual('<Parameter: key=foo, type=Boolean, description=bar>', repr(p))

    def test_is_different_mismatched_type(self):
        p = Parameter(key='foo', description='bar', type='Boolean', optional=False)
        self.assertTrue(p.is_different("NOT_A_PARAMETER"))

    def test_is_different_mismatched_required_field(self):
        p1 = Parameter(key='foo', description='bar', type='Boolean', optional=False)
        p2 = Parameter(key='bar', description='bar', type='Boolean', optional=False)
        self.assertTrue(p1.is_different(p2))

    def test_is_different_mismatched_number_of_parameters(self):
        p1 = Parameter(key='foo', description='bar', type='Boolean', optional=False,
                       parameters=[])
        p2 = Parameter(key='foo', description='bar', type='Boolean', optional=False,
                       parameters=[p1])
        self.assertTrue(p1.is_different(p2))

    def test_is_different_nested_parameter_different_missing_key(self):
        nested_parameter1 = Parameter(key='foo', description='bar', type='Boolean',
                                      optional=False, parameters=[])
        nested_parameter2 = Parameter(key='bar', description='bar', type='Boolean',
                                      optional=False, parameters=[])
        p1 = Parameter(key='foo', description='bar', type='Boolean', optional=False,
                       parameters=[nested_parameter1])
        p2 = Parameter(key='foo', description='bar', type='Boolean', optional=False,
                       parameters=[nested_parameter2])
        self.assertTrue(p1.is_different(p2))

    def test_is_different_nested_parameter_different(self):
        nested_parameter1 = Parameter(key='foo', description='bar', type='Boolean',
                                      optional=False, parameters=[])
        nested_parameter2 = Parameter(key='foo', description='bar', type='String',
                                      optional=False, parameters=[])
        p1 = Parameter(key='foo', description='bar', type='Boolean', optional=False,
                       parameters=[nested_parameter1])
        p2 = Parameter(key='foo', description='bar', type='Boolean', optional=False,
                       parameters=[nested_parameter2])
        self.assertTrue(p1.is_different(p2))

    def test_is_different_false_no_nested(self):
        p1 = Parameter(key='foo', description='bar', type='Boolean', optional=False)
        self.assertFalse(p1.is_different(p1))

    def test_is_different_false_nested(self):
        nested_parameter1 = Parameter(key='foo', description='bar', type='Boolean',
                                      optional=False, parameters=[])
        p1 = Parameter(key='foo', description='bar', type='Boolean', optional=False,
                       parameters=[nested_parameter1])
        self.assertFalse(p1.is_different(p1))


class RequestTemplateTest(unittest.TestCase):

    def test_str(self):
        self.assertEqual('command', str(RequestTemplate(command='command')))

    def test_repr(self):
        request = RequestTemplate(command='command', system='system')
        self.assertNotEqual(-1, repr(request).find('name'))
        self.assertNotEqual(-1, repr(request).find('system'))


class RequestTest(unittest.TestCase):

    def test_command_type_fields(self):
        self.assertEqual(Request.COMMAND_TYPES, Command.COMMAND_TYPES)

    def test_init_none_command_type(self):
        try:
            Request(system='foo', command='bar', command_type=None)
        except ModelValidationError:
            self.fail("Request should be allowed to initialize a None Command Type.")

    def test_str(self):
        self.assertEqual('command', str(Request(command='command')))

    def test_repr(self):
        request = Request(command='command', status='CREATED')
        self.assertNotEqual(-1, repr(request).find('name'))
        self.assertNotEqual(-1, repr(request).find('CREATED'))

    def test_set_valid_status(self):
        request = Request(status='CREATED')
        request.status = 'RECEIVED'
        request.status = 'IN_PROGRESS'
        request.status = 'SUCCESS'

    def test_invalid_status_transitions(self):
        states = [
            ('SUCCESS', 'IN_PROGRESS'),
            ('SUCCESS', 'ERROR'),
            ('IN_PROGRESS', 'CREATED')
        ]
        for begin_status, end_status in states:
            request = Request(status=begin_status)
            try:
                request.status = end_status
                self.fail("Request should not be able to go from status {0} to {1}"
                          .format(begin_status, end_status))
            except RequestStatusTransitionError:
                pass

    def test_is_ephemral(self):
        request = Request(command_type=None)
        self.assertFalse(request.is_ephemeral)
        request.command_type = 'EPHEMERAL'
        self.assertTrue(request.is_ephemeral)

    def test_is_json(self):
        request = Request(output_type=None)
        self.assertFalse(request.is_json)
        request.output_type = 'JSON'
        self.assertTrue(request.is_json)


class SystemTest(unittest.TestCase):

    def setUp(self):
        self.default_system = System(name='foo', version='1.0.0')

    def tearDown(self):
        self.default_system = None

    def test_get_command_by_name_found(self):
        mock_name = PropertyMock(return_value='name')
        command = Mock()
        type(command).name = mock_name
        self.default_system.commands.append(command)
        self.assertEqual(self.default_system.get_command_by_name('name'), command)

    def test_get_command_by_name_none(self):
        mock_name = PropertyMock(return_value='foo')
        command = Mock()
        type(command).name = mock_name
        self.default_system.commands.append(command)
        self.assertIsNone(self.default_system.get_command_by_name('name'))

    def test_has_instance_true(self):
        self.default_system.instances = [Instance(name='foo')]
        self.assertTrue(self.default_system.has_instance('foo'))

    def test_has_instance_false(self):
        self.default_system.instances = [Instance(name='foo')]
        self.assertFalse(self.default_system.has_instance('bar'))

    def test_instance_names(self):
        self.default_system.instances = [Instance(name='foo'), Instance(name='bar')]
        self.assertEqual(self.default_system.instance_names, ['foo', 'bar'])

    def test_get_instance_true(self):
        instance = Instance(name='bar')
        self.default_system.instances = [Instance(name='foo'), instance]
        self.assertEqual(instance, self.default_system.get_instance('bar'))

    def test_get_instance_false(self):
        self.default_system.instances = [Instance(name='foo')]
        self.assertIsNone(self.default_system.get_instance('bar'))

    def test_has_different_commands_different_length(self):
        self.assertEqual(self.default_system.has_different_commands([1]), True)

    def test_has_different_commands_different_name(self):
        mock_name1 = PropertyMock(return_value='name')
        mock_name2 = PropertyMock(return_value='name2')
        command = Mock(description='description')
        type(command).name = mock_name1

        self.default_system.commands.append(command)

        new_command = Mock(description='description')
        type(new_command).name = mock_name2
        command.has_different_parameters = Mock(return_value=False)
        self.assertTrue(self.default_system.has_different_commands([new_command]))

    def test_has_different_commands_different_description(self):
        mock_name = PropertyMock(return_value='name')
        command = Mock(description='description')
        type(command).name = mock_name
        self.default_system.commands.append(command)
        new_command = Mock(description='description2')
        type(new_command).name = mock_name
        command.has_different_parameters = Mock(return_value=False)
        self.assertFalse(self.default_system.has_different_commands([new_command]))

    def test_has_different_commands_different_parameters_true(self):
        mock_name = PropertyMock(return_value='name')
        command = Mock(description='description')
        type(command).name = mock_name
        self.default_system.commands.append(command)
        new_command = Mock(description='description')
        type(new_command).name = mock_name
        command.has_different_parameters = Mock(return_value=True)
        self.assertTrue(self.default_system.has_different_commands([new_command]))

    def test_has_different_commands_the_same(self):
        mock_name = PropertyMock(return_value='name')
        command = Mock()
        type(command).name = mock_name
        command.description = 'description'

        self.default_system.commands.append(command)

        new_command = Mock()
        type(new_command).name = mock_name
        new_command.description = 'description'
        command.has_different_parameters = Mock(return_value=False)

        self.assertFalse(self.default_system.has_different_commands([new_command]))

    def test_str(self):
        self.assertEqual('foo-1.0.0', str(self.default_system))

    def test_repr(self):
        self.assertNotEqual(-1, repr(self.default_system).find('foo'))
        self.assertNotEqual(-1, repr(self.default_system).find('1.0.0'))


class PatchOperationTest(unittest.TestCase):

    def test_str(self):
        p = PatchOperation(operation='op', path='path', value='value')
        self.assertEqual('op, path, value', str(p))

    def test_str_only_operation(self):
        p = PatchOperation(operation='op')
        self.assertEqual('op, None, None', str(p))

    def test_repr(self):
        p = PatchOperation(operation='op', path='path', value='value')
        self.assertEqual('<Patch: operation=op, path=path, value=value>', repr(p))

    def test_repr_only_operation(self):
        p = PatchOperation(operation='op')
        self.assertEqual('<Patch: operation=op, path=None, value=None>', repr(p))


class LoggingConfigTest(unittest.TestCase):

    def test_str(self):
        c = LoggingConfig(level="INFO",
                          handlers={"logstash": {}, "stdout": {}, "file": {}},
                          formatters={"default": {"format": LoggingConfig.DEFAULT_FORMAT}},
                          loggers=None)
        self.assertEqual('INFO, %s, %s' % (c.handler_names, c.formatter_names), str(c))

    def test_repr(self):
        c = LoggingConfig(level="INFO",
                          handlers={"logstash": {}, "stdout": {}, "file": {}},
                          formatters={"default": {"format": LoggingConfig.DEFAULT_FORMAT}},
                          loggers=None)
        self.assertEqual('<LoggingConfig: level=INFO, handlers=%s, formatters=%s' % (
            c.handler_names, c.formatter_names), repr(c))

    def test_handler_names(self):
        c = LoggingConfig(level="INFO",
                          handlers={"logstash": {}, "stdout": {}, "file": {}},
                          formatters={"default": {"format": LoggingConfig.DEFAULT_FORMAT}},
                          loggers=None)
        self.assertListEqual(sorted(list(c.handler_names)), ["file", "logstash", "stdout"])

    def test_handler_names_none(self):
        c = LoggingConfig(level="INFO")
        self.assertIsNone(c.handler_names)

    def test_formatter_names(self):
        c = LoggingConfig(level="INFO",
                          handlers={"logstash": {}, "stdout": {}, "file": {}},
                          formatters={"default": {"format": LoggingConfig.DEFAULT_FORMAT}},
                          loggers=None)
        self.assertListEqual(list(c.formatter_names), ["default"])

    def test_formatter_names_none(self):
        c = LoggingConfig(level="INFO")
        self.assertIsNone(c.formatter_names)

    def test_get_plugin_log_config_no_system_name(self):
        c = LoggingConfig(level="INFO",
                          handlers={"logstash": {}, "stdout": {}, "file": {}},
                          formatters={"default": {"format": LoggingConfig.DEFAULT_FORMAT}},
                          loggers=None)
        self.assertEqual(c.get_plugin_log_config(), c)

    def test_get_plugin_log_config_handler_names_specified(self):
        c = LoggingConfig(level="INFO",
                          handlers={"logstash": {}, "stdout": {}, "file": {}},
                          formatters={"default": {"format": LoggingConfig.DEFAULT_FORMAT}},
                          loggers={"system1": {
                              "handlers": ["stdout"]
                          }})
        log_config = c.get_plugin_log_config(system_name="system1")
        self.assertListEqual(list(log_config.handler_names), ["stdout"])

    def test_get_plugin_log_config_handlers_as_dict(self):
        c = LoggingConfig(level="INFO",
                          handlers={"logstash": {}, "stdout": {}, "file": {}},
                          formatters={"default": {"format": LoggingConfig.DEFAULT_FORMAT}},
                          loggers={"system1": {
                              "handlers": {"stdout": {"foo": "bar"}}
                          }})
        log_config = c.get_plugin_log_config(system_name="system1")
        self.assertListEqual(list(log_config.handler_names), ["stdout"])
        self.assertDictEqual(log_config.handlers['stdout'], {"foo": "bar"})

    def test_get_plugin_log_config_override_formatter(self):
        c = LoggingConfig(level="INFO",
                          handlers={"logstash": {}, "stdout": {}, "file": {}},
                          formatters={"default": {"format": LoggingConfig.DEFAULT_FORMAT}},
                          loggers={"system1": {
                              "formatters": {"stdout": "%(message)s"}
                          }})
        log_config = c.get_plugin_log_config(system_name="system1")
        self.assertListEqual(sorted(list(log_config.formatter_names)), ["default", "stdout"])
        self.assertEqual(log_config.formatters['default'], {
            "format": LoggingConfig.DEFAULT_FORMAT
        })
        self.assertEqual(log_config.formatters['stdout'], {"format": "%(message)s"})


class EventTest(unittest.TestCase):

    def test_str(self):
        event = Event(name='REQUEST_CREATED', error=False, payload={'request': 'request'},
                      metadata={})
        self.assertEqual('%s: %s, %s' % (event.name, event.payload, event.metadata), str(event))

    def test_repr(self):
        event = Event(name='REQUEST_CREATED', error=False, payload={'request': 'request'},
                      metadata={})
        self.assertEqual('<Event: name=%s, error=%s, payload=%s, metadata=%s>' %
                         (event.name, event.error, event.payload, event.metadata), repr(event))


class QueueTest(unittest.TestCase):

    def test_str(self):
        queue = Queue(name='echo.1-0-0.default', system='echo', version='1.0.0',
                      instance='default', system_id='1234',
                      display='foo.1-0-0.default', size=3)
        self.assertEqual('%s: %s' % (queue.name, queue.size), str(queue))

    def test_repr(self):
        queue = Queue(name='echo.1-0-0.default', system='echo', version='1.0.0',
                      instance='default', system_id='1234',
                      display='foo.1-0-0.default', size=3)
        self.assertEqual('<Queue: name=echo.1-0-0.default, size=3>', repr(queue))


class JobTest(unittest.TestCase):

    def test_str(self):
        job = Job(name='name', trigger_type='cron', trigger_args={}, id='id')
        self.assertEqual('name: id', str(job))

    def test_repr(self):
        job = Job(name='name', id='id')
        self.assertEqual('<Job: name=name, id=id>', repr(job))
