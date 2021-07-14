# -*- coding: utf-8 -*-


def normalize_url_prefix(url_prefix):
    """Enforce a consistent URL representation

    The normalized prefix will begin and end with '/'. If there is no prefix
    the normalized form will be '/'.

    Examples:
        ===========  ============
        INPUT        NORMALIZED
        ===========  ============
        None         '/'
        ''           '/'
        '/'          '/'
        'example'    '/example/'
        '/example'   '/example/'
        'example/'   '/example/'
        '/example/'  '/example/'
        ===========  ============

    Args:
        url_prefix (str): The prefix

    Returns:
        str: The normalized prefix
    """
    if url_prefix in (None, "/", ""):
        return "/"

    new_url_prefix = ""

    # Make string begin with /
    if not url_prefix.startswith("/"):
        new_url_prefix += "/"

    new_url_prefix += url_prefix

    # Make string end with /
    if not url_prefix.endswith("/"):
        new_url_prefix += "/"

    return new_url_prefix
