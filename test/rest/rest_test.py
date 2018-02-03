import unittest

from brewtils.rest import normalize_url_prefix


class RestTest(unittest.TestCase):

    def test_normalize_url_prefix(self):
        simple_prefixes = [None, '', '/']
        example_prefixes = ['example', '/example', 'example/', '/example/']
        example_prefixes_2 = ['beer/garden', '/beer/garden', '/beer/garden/']
        example_prefix_chars = ['+-?.,', '/+-?.,', '+-?.,/', '/+-?.,/']

        for i in simple_prefixes:
            self.assertEquals("/", normalize_url_prefix(i))

        for i in example_prefixes:
            self.assertEquals("/example/", normalize_url_prefix(i))

        for i in example_prefixes_2:
            self.assertEquals('/beer/garden/', normalize_url_prefix(i))

        for i in example_prefix_chars:
            self.assertEquals('/+-?.,/', normalize_url_prefix(i))