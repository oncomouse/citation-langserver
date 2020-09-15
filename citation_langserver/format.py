"""Citation Language Server Formatting Utilities"""
import re

from bibparse import BibItem


def info(entry: BibItem) -> str:
    """Given a bibliography entry, describe it for human readers."""
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
