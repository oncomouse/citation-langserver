import re
from typing import List
from pygls.types import CompletionList, CompletionItem, CompletionItemKind
from .format import info
from bibparse import Biblio


def generate_list(bibliographies: Biblio,
                  search_key='') -> List[CompletionItem]:
    key_regex = re.compile('^{}.*'.format(search_key))
    for key in list(filter(key_regex.match, bibliographies.keys())):
        entry = bibliographies[key]
        yield CompletionItem(label="@{}".format(key),
                             kind=CompletionItemKind.Text,
                             documentation=info(entry),
                             insert_text=key)
