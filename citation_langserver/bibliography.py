"""Bibliography Utiltities"""
import re
from typing import Dict
from pygls.types import Position, TextDocumentPositionParams, TextDocumentIdentifier
from pygls.uris import from_fs_path

__key_re = re.compile(r"@[^,\s{}@\]\[]+\s*{\s*([^,\s{}@\]\[]+)")


def key_positions(file_path: str) -> Dict[str, TextDocumentPositionParams]:
    """Find the position of all keys in a provided .bib file"""
    file_pointer = open(file_path)
    linenr = 0
    keys = {}
    for line in file_pointer:
        position = __key_re.search(line)
        if position is not None:
            key = position.groups()[0]
            keys[key] = TextDocumentPositionParams(
                position=Position(line=linenr, character=position.span()[0]),
                text_document=TextDocumentIdentifier(
                    uri=from_fs_path(file_path)))
        linenr += 1
    return keys
