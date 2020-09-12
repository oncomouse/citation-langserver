"""Citation Language Server.
Creates the language server constant and wraps "features" with it.
Official language server spec:
    https://microsoft.github.io/language-server-protocol/specification
"""
import json
import os
import re
from glob import glob
from pygls import types
from pygls.features import (HOVER, COMPLETION, TEXT_DOCUMENT_DID_CHANGE,
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

# async def get_configuration(ls: LanguageServer):
#     config = await ls.get_configuration_async(
#         types.ConfigurationParams([
#             types.ConfigurationItem(
#                 '', CitationLanguageServer.CONFIGURATION_SECTION)
#         ]))
#     for key in config:
#         if key in configuration:
#             configuration[key] = config[key]


def __read_bibliography(file):
    cached_bibliographies = Biblio()
    for f in glob(os.path.expanduser(file)):
        cached_bibliographies.read(f)
    print(cached_bibliographies)


completion_list = types.CompletionList(False, [])


def __generate_completion_list(bibliographies):
    output = []
    for key, entry in bibliographies.items():
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


@citation_langserver.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: LanguageServer, params: types.DidChangeTextDocumentParams):
    get_markdown_file(ls, params.textDocument.uri, True)


@citation_langserver.feature(WORKSPACE_DID_CHANGE_CONFIGURATION)
def did_change_configuration(ls: LanguageServer,
                             params: types.DidChangeConfigurationParams):
    if hasattr(params.settings.citation, 'bibliographies'):
        bibliographies = getattr(params.settings.citation, 'bibliographies')
        configuration['bibliographies'] = bibliographies
        for file in bibliographies:
            __read_bibliography(file)
        # __generate_completion_list()


# @citation_langserver.feature(WORKSPACE_DID_CHANGE_WORKSPACE_FOLDERS)
# def did_change_workspace_folders(
#         ls: LanguageServer, params: types.DidChangeWorkspaceFoldersParams):
#     if any(glob_re.match(line) for line in configuration['bibliographies']):

#         read_bibliography(configuration['bibliographies'])


async def __load_bibliographies(ls: LanguageServer):
    if len(cached_bibliographies.keys()) == 0:
        config = await ls.get_configuration_async(
            types.ConfigurationParams(
                [types.ConfigurationItem('', 'citation')]))
        bibliographies = getattr(config[0], 'bibliographies')
        configuration['bibliographies'] = bibliographies
        for file in bibliographies:
            print("Caching {}…".format(file))
            __read_bibliography(file)
    return cached_bibliographies


@citation_langserver.feature(HOVER)
async def hover(ls: LanguageServer, params: types.TextDocumentPositionParams):
    bibliographies = await __load_bibliographies(ls)
    print("textDocument/hover {}".format(repr(params)))
    markdown_file = get_markdown_file(ls, params.textDocument.uri)
    key, start, stop = find_key(markdown_file, params.position)
    if key is not None and key in bibliographies:
        return types.Hover(contents=__format_info(bibliographies[key]),
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
async def completion(ls: LanguageServer,
                     params: types.CompletionParams = None):
    bibliographies = await __load_bibliographies(ls)
    markdown_file = get_markdown_file(ls, params.textDocument.uri)
    key = find_key(markdown_file, params.position)
    print("textDocument/completion {}".format(repr(params)))
    return types.CompletionList(
        False, list(__generate_completion_list(bibliographies)))
