import re
from pygls import types
from .format import info


def generate_list(bibliographies, search_key=''):
    types.CompletionList(False, [])
    key_regex = re.compile('^{}.*'.format(search_key))
    for key in list(filter(key_regex.match, bibliographies.keys())):
        entry = bibliographies[key]
        yield types.CompletionItem(label="@{}".format(key),
                                   kind=types.CompletionItemKind.Text,
                                   documentation=info(entry),
                                   insert_text=key)
