"""Citation Language Server.
Creates the language server constant and wraps "features" with it.
Official language server spec:
    https://microsoft.github.io/language-server-protocol/specification
"""
import errno
import os
import re
from glob import glob
from pygls import types
from pygls.features import (HOVER, COMPLETION, DEFINITION,
                            TEXT_DOCUMENT_DID_CHANGE, INITIALIZE,
                            WORKSPACE_DID_CHANGE_WORKSPACE_FOLDERS,
                            WORKSPACE_DID_CHANGE_CONFIGURATION)
from pygls.server import LanguageServer
from bibparse import Biblio
from .bibliography import find_key, key_positions
from .completion import generate_list
from .format import info

cached_bibliographies = Biblio()
workspace_folders = []
configuration = {'bibliographies': ['~/*.bib']}
glob_re = re.compile(r"\*")
keys = {}


class CitationLanguageServer(LanguageServer):
    CONFIGURATION_SECTION = 'citation'

    def __init__(self):
        super().__init__()


citation_langserver = CitationLanguageServer()


def __handle_glob(my_file):
    output = []
    for file in my_file:
        if glob_re.match(file):
            output.extend(glob(file))
        else:
            output.append(file)
    return output


def __norm_file(my_file):
    output = [my_file]
    if my_file[0] == '.':
        output = [
            os.path.join(directory, my_file) for directory in workspace_folders
        ]
    return [os.path.normpath(os.path.expanduser(file)) for file in output]


def __read_bibliographies(bibliographies):
    cached_bibliographies.clear()
    for file in bibliographies:
        __read_bibliography(file)


def __read_bibliography(maybe_glob):
    for file in __handle_glob(__norm_file(maybe_glob)):
        if not os.path.exists(file):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                                    file)
        cached_bibliographies.read(os.path.abspath(file))
        keys.update(key_positions(file))


def __update_bibliography_configuration(config):
    bibliographies = getattr(config[0], 'bibliographies')
    if bibliographies != configuration['bibliographies']:
        configuration['bibliographies'] = bibliographies
        __read_bibliographies(configuration['bibliographies'])


markdown_files = {}


def get_markdown_file(ls: LanguageServer, uri: str, update: bool = False):
    result = None if update else markdown_files.get(uri)
    if not result:
        document = ls.workspace.get_document(uri)
        result = {'source': document.source, 'path': document.path}
        markdown_files[uri] = result
    return result


@citation_langserver.feature(INITIALIZE)
def initialize(ls: LanguageServer, params: types.InitializeParams):
    if params.rootPath:
        workspace_folders.append(params.rootPath)
    if params.workspace.configuration:
        try:
            ls.get_configuration(
                types.ConfigurationParams([
                    types.ConfigurationItem(
                        '', CitationLanguageServer.CONFIGURATION_SECTION)
                ]), __update_bibliography_configuration)
        except FileNotFoundError as err:
            ls.show_message("File Not Found Error: {}".format(err),
                            types.MessageType.Error)


@citation_langserver.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: LanguageServer, params: types.DidChangeTextDocumentParams):
    get_markdown_file(ls, params.textDocument.uri, True)


@citation_langserver.feature(WORKSPACE_DID_CHANGE_CONFIGURATION)
def did_change_configuration(ls: LanguageServer,
                             params: types.DidChangeConfigurationParams):
    try:
        __update_bibliography_configuration([
            getattr(params.settings,
                    CitationLanguageServer.CONFIGURATION_SECTION)
        ])
    except FileNotFoundError as err:
        ls.show_message("File Not Found Error: {}".format(err),
                        types.MessageType.Error)


@citation_langserver.feature(WORKSPACE_DID_CHANGE_WORKSPACE_FOLDERS)
def did_change_workspace_folders(
        _ls: LanguageServer, params: types.DidChangeWorkspaceFoldersParams):
    workspace_folders.extend(params.event.added)
    for folder in params.event.removed:
        workspace_folders.remove(folder)
    __read_bibliographies(configuration['bibliographies'])


@citation_langserver.feature(HOVER)
def hover(ls: LanguageServer, params: types.TextDocumentPositionParams):
    markdown_file = get_markdown_file(ls, params.textDocument.uri)
    key, start, stop = find_key(markdown_file, params.position)
    if key is not None and key in cached_bibliographies:
        return types.Hover(contents=info(cached_bibliographies[key]),
                           range=types.Range(
                               start=types.Position(line=params.position.line,
                                                    character=start),
                               end=types.Position(line=params.position.line,
                                                  character=stop)))
    return None


@citation_langserver.feature(COMPLETION)  # , trigger_characters=['@'])
def completion(ls: LanguageServer, params: types.CompletionParams = None):
    markdown_file = get_markdown_file(ls, params.textDocument.uri)
    key, *_ = find_key(markdown_file, params.position)
    if key is None:
        return []
    return types.CompletionList(
        False, list(generate_list(cached_bibliographies, search_key=key)))


@citation_langserver.feature(DEFINITION)
def definition(ls: LanguageServer,
               params: types.TextDocumentPositionParams = None):
    markdown_file = get_markdown_file(ls, params.textDocument.uri)
    key, *_ = find_key(markdown_file, params.position)
    if key is None or not key in keys:
        return None
    key_position = keys[key]
    return types.Location(
        uri=key_position.textDocument.uri,
        range=types.Range(
            start=key_position.position,
            end=types.Position(line=key_position.position.line,
                               character=key_position.position.character +
                               len(key))))
