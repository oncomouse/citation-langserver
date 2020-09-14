import re
from typing import Dict


def info(entry: Dict[str, str]) -> str:
    return "{title}{author}{date}".format(
        title=("Title: {}\n".format(re.sub(r"[}{]", "", entry["title"]))
               if "title" in entry else ""),
        author=("Author{plural}: {author}\n".format(
            plural="s" if len(entry["author"]) > 1 else "",
            author="; ".join(entry["author"]),
        ) if "author" in entry else ""),
        date=("Year: {}\n".format(entry["date"].split("-")[0])
              if "date" in entry else ""),
    )
