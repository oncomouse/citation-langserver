from typing import Dict, List
from pygls.types import Location, Range, Position
from pygls.uris import from_fs_path


def get_references(doc: Dict[str, str], symbol: str) -> List[Location]:
    current_line = 0
    output = []
    symbol_len = len(symbol)
    uri = from_fs_path(doc['path'])
    for line in doc["source"].split("\n"):
        for index in [
                i for i in range(len(line)) if line.startswith(symbol, i)
        ]:
            output.append(
                Location(uri=uri,
                         range=Range(start=Position(line=current_line,
                                                    character=index),
                                     end=Position(line=current_line,
                                                  character=index +
                                                  symbol_len))))

        current_line += 1
    return output
