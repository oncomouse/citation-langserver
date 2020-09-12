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


def read_bibliography(file):
    cached_bibliographies = Biblio()
    for f in glob(os.path.expanduser(file)):
        cached_bibliographies.read(f)


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
            read_bibliography(file)


@citation_langserver.feature(WORKSPACE_DID_CHANGE_WORKSPACE_FOLDERS)
def did_change_workspace_folders(
        ls: LanguageServer, params: types.DidChangeWorkspaceFoldersParams):
    if any(glob_re.match(line) for line in configuration['bibliographies']):

        read_bibliography(configuration['bibliographies'])


@citation_langserver.feature(HOVER)
def hover(ls: LanguageServer, params: types.TextDocumentPositionParams):
    print("textDocument/hover {}".format(repr(params)))
    pass


@citation_langserver.feature(COMPLETION)  # , trigger_characters=['@'])
def completion(ls: LanguageServer, params: types.CompletionParams = None):
    markdown_file = get_markdown_file(ls, params.textDocument.uri)
    print("textDocument/completion {}".format(repr(params)))
