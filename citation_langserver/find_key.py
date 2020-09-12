import re

non_cite_key_re = re.compile(r"[,\s}{@\]\[]")


def find_key(doc, position):
    line = doc["source"].split("\n")[position.line]
    start_char = position.character
    stop_char = position.character
    while start_char >= 0:
        if line[start_char] == '@':
            break
        if non_cite_key_re.match(line[start_char]):
            return None
        start_char -= 1
    if start_char < 0:
        return None
    while stop_char < len(line):
        if non_cite_key_re.match(line[stop_char]):
            break
        stop_char += 1
    if stop_char >= len(line):
        return None
    return [line[start_char + 1:stop_char], start_char + 1, stop_char - 1]
