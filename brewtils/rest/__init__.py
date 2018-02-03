
def normalize_url_prefix(url_prefix):

    # Regex to find everything between the / / in the url
    # Should cover all cases
    # url_prefix -------- base_url
    # None                http://localhost:2337/
    # ''                  http://localhost:2337/
    # '/'                 http://localhost:2337/
    # 'example'           http://localhost:2337/example/
    # '/example'          http://localhost:2337/example/
    # 'example/'          http://localhost:2337/example/
    # '/example/'         http://localhost:2337/example/

    if url_prefix in (None, '/', ''):
        return '/'

    new_url_prefix = ""

    # Make string begin with /
    if not url_prefix.startswith("/"):
        new_url_prefix += '/'

    new_url_prefix += url_prefix

    # Make string end with /
    if not url_prefix.endswith("/"):
        new_url_prefix += '/'

    return new_url_prefix
