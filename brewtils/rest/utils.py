def unroll_object(obj, key_map=None, ignore=None, strip_characters=None):
    """
    Reads the object __dict__ and uses the map or ignore
    fields to return an altered version of it.

    Parameters:
        obj: The object to unroll into a dictionary.
        key_map: A map to transform a set of keys to another key.
                 Valid values are new keys or functions of the signature:
                    func(dict, key, value) **Alters the dict in-place
                 (e.g. {'original_key': 'new_key', 'other_key': func})
        ignore: A list of strings corresponding to object variable names that should NOT
                be added to the resulting dictionary.
        strip_characters: A string of characters to trim from the front and back of all keys
                          (matching is per-character, not the whole string)
    """
    if key_map is None:
        key_map = {}
    if ignore is None:
        ignore = []
    if strip_characters is None:
        strip_characters = ""
    tmp_dict = {}
    for (key, value) in obj.__dict__.items():
        key = key.strip(strip_characters)
        if key in key_map:
            if callable(key_map[key]):
                key_map[key](tmp_dict, key, value)
            else:
                tmp_dict[key_map[key]] = value
        elif key not in ignore:
            tmp_dict[key] = value
    return tmp_dict
