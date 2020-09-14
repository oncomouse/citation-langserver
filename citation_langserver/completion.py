"""Citation Language Server Completion Utilities"""
import re
from typing import List
from pygls.types import CompletionItem, CompletionItemKind
from bibparse import Biblio
from .format import info


def generate_list(bibliographies: Biblio,
                  search_key: str) -> List[CompletionItem]:
    """Given a bibliography and a search string, find all completion items
    that might match the entry."""
    key_regex = re.compile('^{}.*'.format(search_key))
    for key in list(filter(key_regex.match, bibliographies.keys())):
        entry = bibliographies[key]
        yield CompletionItem(label="@{}".format(key),
                             kind=CompletionItemKind.Text,
                             documentation=info(entry),
                             insert_text=key)
