import unittest
import json
from brewtils.errors import parse_exception_as_json


class ErrorsTest(unittest.TestCase):

    def test_parse_as_json(self):
        e = Exception({"foo": "bar"})
        value = parse_exception_as_json(e)
        self.assertEqual(json.dumps({"foo": "bar"}), value)

    def test_parse_as_json_str(self):
        e = Exception(json.dumps({"foo": "bar"}))
        value = parse_exception_as_json(e)
        self.assertEqual(json.dumps({"foo": "bar"}), value)

    def test_parse_as_json_value_error(self):
        self.assertRaises(ValueError,
                          parse_exception_as_json,
                          123)

    def test_parse_as_json_multiple_args(self):
        e = Exception("message1", "message2")
        value = parse_exception_as_json(e)
        self.assertDictEqual(json.loads(value),
                             {
                                 "message": str(e),
                                 "arguments": ["message1", "message2"],
                                 "attributes": {}
                             })

    def test_parse_as_json_str_to_str(self):
        e = Exception('"message1"')
        value = parse_exception_as_json(e)
        self.assertDictEqual(json.loads(value),
                             {
                                 "message": str(e),
                                 "arguments": ['"message1"'],
                                 "attributes": {}
                             })

    def test_parse_as_json_int_to_str(self):
        e = Exception('1')
        value = parse_exception_as_json(e)
        self.assertDictEqual(json.loads(value),
                             {
                                 "message": str(e),
                                 "arguments": [1],
                                 "attributes": {}
                             })
