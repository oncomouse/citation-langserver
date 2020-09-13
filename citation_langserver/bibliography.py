import re
from pygls.types import Position, TextDocumentPositionParams, TextDocumentIdentifier
from pygls.uris import from_fs_path

__key_re = re.compile(r"@[^,\s{}@\]\[]+\s*{\s*([^,\s{}@\]\[]+)")
__non_cite_key_re = re.compile(r"[,\s}{@\]\[]")


def key_positions(file_path):
    fp = open(file_path)
    linenr = 0
    keys = {}
    for line in fp:
        position = __key_re.search(line)
        if position is not None:
            key = position.groups()[0]
            keys[key] = TextDocumentPositionParams(
                position=Position(line=linenr, character=position.span()[0]),
                text_document=TextDocumentIdentifier(
                    uri=from_fs_path(file_path)))
        linenr += 1
    return keys


def find_key(doc, position):
    line = doc["source"].split("\n")[position.line]
    start_char = position.character - 1
    stop_char = position.character - 1
    while start_char >= 0:
        if line[start_char] == '@':
            break
        if __non_cite_key_re.match(line[start_char]):
            return [None, None, None]
        start_char -= 1
    if start_char < 0:
        return [None, None, None]
    while stop_char < len(line):
        if __non_cite_key_re.match(line[stop_char]):
            break
        stop_char += 1
    return [line[start_char + 1:stop_char], start_char + 1, stop_char - 1]
