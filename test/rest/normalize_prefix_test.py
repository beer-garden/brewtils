# -*- coding: utf-8 -*-

import pytest

from brewtils.rest import normalize_url_prefix


@pytest.mark.parametrize('normalized,initial', [
    ('/', None),
    ('/', '',),
    ('/', '/'),
    ('/example/', 'example'),
    ('/example/', '/example'),
    ('/example/', 'example/'),
    ('/example/', '/example/'),
    ('/beer/garden/', 'beer/garden'),
    ('/beer/garden/', '/beer/garden'),
    ('/beer/garden/', '/beer/garden/'),
    ('/+-?.,/', '+-?.,'),
    ('/+-?.,/', '/+-?.,'),
    ('/+-?.,/', '+-?.,/'),
    ('/+-?.,/', '/+-?.,/'),
])
def test_normalize_url_prefix(normalized, initial):
    assert normalized == normalize_url_prefix(initial)
