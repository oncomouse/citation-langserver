"""Citation Language Server Document Utilities"""
import re
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from pygls.lsp.types import Location
from pygls.lsp.types import Position
from pygls.lsp.types import Range
from pygls.uris import from_fs_path

__non_cite_key_re = re.compile(r"[,\s}{@\]\[]")


def find_key(
    doc: Dict[str, str], position: Position
) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """Given a representation of a document and a position object, find if the
    user is typing a key at that position and return the entire typed key, if
    present."""
    line = doc["source"].split("\n")[position.line]
    start_char = position.character - 1
    stop_char = position.character
    while start_char >= 0:
        # We have found a Markdown citation key:
        if line[start_char] == "@":
            break
        # We may have found a LaTeX citation key:
        if line[start_char] == "{":
            # We have found a LaTeX citation key:
            if start_char >= 4 and line[start_char - 4: start_char] == "cite":
                break
            # We have not found a LaTeX citation key:
            return (None, None, None)
        # We have found a character not allowed in a citation key before
        # finding a terminator key (for Markdown or LaTeX):
        if __non_cite_key_re.match(line[start_char]):
            return (None, None, None)
        start_char -= 1
    # We did not find a citation key:
    if start_char < 0:
        return (None, None, None)
    # Find the end of the citation key:
    while stop_char < len(line):
        if __non_cite_key_re.match(line[stop_char]):
            break
        stop_char += 1
    return (line[start_char + 1: stop_char], start_char + 1, stop_char - 1)


def get_references(doc: Dict[str, str], symbol: str) -> List[Location]:
    """Given a representation of a document and a symbol string, return the
    Location of every use of that symbol within the document."""
    current_line = 0
    output = []
    symbol_len = len(symbol)
    uri = from_fs_path(doc["path"])
    for line in doc["source"].split("\n"):
        for index in [i for i in range(len(line)) if line.startswith(symbol, i)]:
            output.append(
                Location(
                    uri=uri,
                    range=Range(
                        start=Position(line=current_line, character=index),
                        end=Position(line=current_line,
                                     character=index + symbol_len),
                    ),
                )
            )

        current_line += 1
    return output
