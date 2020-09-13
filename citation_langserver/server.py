"""Citation Language Server.
Creates the language server constant and wraps "features" with it.
Official language server spec:
    https://microsoft.github.io/language-server-protocol/specification
"""
import os
import re
from glob import glob
from pygls import types
from pygls.features import (HOVER, COMPLETION, TEXT_DOCUMENT_DID_CHANGE,
                            INITIALIZED,
                            WORKSPACE_DID_CHANGE_WORKSPACE_FOLDERS,
                            WORKSPACE_DID_CHANGE_CONFIGURATION)
from pygls.server import LanguageServer
from bibparse import Biblio
from .find_key import find_key

cached_bibliographies = Biblio()
workspace_folders = {}
configuration = {'bibliographies': ['~/*.bib']}
glob_re = re.compile(r"\*")


class CitationLanguageServer(LanguageServer):
    CONFIGURATION_SECTION = 'citation'

    def __init__(self):
        super().__init__()


citation_langserver = CitationLanguageServer()


def __read_bibliographies(bibliographies):
    cached_bibliographies = Biblio()
    for file in bibliographies:
        __read_bibliography(file)


def __read_bibliography(file):
    for f in glob(os.path.expanduser(file)):
        if not os.path.exists(f):
            print("Error locating {f}".format(f))
        cached_bibliographies.read(f)


def __generate_completion_list():
    types.CompletionList(False, [])
    for key, entry in cached_bibliographies.items():
        yield types.CompletionItem(label="@{}".format(key),
                                   kind=types.CompletionItemKind.Text,
                                   documentation=__format_info(entry),
                                   insert_text=key)


markdown_files = {}


def get_markdown_file(ls: LanguageServer, uri: str, update: bool = False):
    result = None if update else markdown_files.get(uri)
    if not result:
        document = ls.workspace.get_document(uri)
        result = {'source': document.source, 'path': document.path}
        markdown_files[uri] = result
    return result


def __callback(config):
    bibliographies = getattr(config[0], 'bibliographies')
    if bibliographies != configuration['bibliographies']:
        configuration['bibliographies'] = bibliographies
        __read_bibliographies(configuration['bibliographies'])


@citation_langserver.feature(INITIALIZED)
def initialized(ls: LanguageServer, params: types.InitializeParams):
    if params.workspace.configuration:
        conf = ls.get_configuration(
            types.ConfigurationParams(
                [types.ConfigurationItem('', 'citation')]), __callback)


@citation_langserver.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: LanguageServer, params: types.DidChangeTextDocumentParams):
    get_markdown_file(ls, params.textDocument.uri, True)


@citation_langserver.feature(WORKSPACE_DID_CHANGE_CONFIGURATION)
def did_change_configuration(ls: LanguageServer,
                             params: types.DidChangeConfigurationParams):
    print("workspace/didChangeConfiguration {}".format(params))
    if hasattr(params.settings.citation, 'bibliographies'):
        bibliographies = getattr(params.settings.citation, 'bibliographies')
        if configuration['bibliographies'] != bibliographies:
            configuration['bibliographies'] = bibliographies
            __read_bibliographies(bibliographies)


# @citation_langserver.feature(WORKSPACE_DID_CHANGE_WORKSPACE_FOLDERS)
# def did_change_workspace_folders(
#         ls: LanguageServer, params: types.DidChangeWorkspaceFoldersParams):
#     if any(glob_re.match(line) for line in configuration['bibliographies']):

#         read_bibliography(configuration['bibliographies'])


@citation_langserver.feature(HOVER)
async def hover(ls: LanguageServer, params: types.TextDocumentPositionParams):
    markdown_file = get_markdown_file(ls, params.textDocument.uri)
    key, start, stop = find_key(markdown_file, params.position)
    if key is not None and key in cached_bibliographies:
        return types.Hover(contents=__format_info(cached_bibliographies[key]),
                           range=types.Range(
                               start=types.Position(line=params.position.line,
                                                    character=start),
                               end=types.Position(line=params.position.line,
                                                  character=stop)))
    return None


def __format_info(entry):
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


@citation_langserver.feature(COMPLETION, trigger_characters=['@'])
def completion(ls: LanguageServer, params: types.CompletionParams = None):
    markdown_file = get_markdown_file(ls, params.textDocument.uri)
    print(__generate_completion_list())
    return types.CompletionList(False, list(__generate_completion_list()))
