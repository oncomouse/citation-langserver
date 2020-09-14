"""Citation Language Server.
Creates the language server constant and wraps "features" with it.
Official language server spec:
    https://microsoft.github.io/language-server-protocol/specification
"""
import errno
import os
from typing import Dict, List, Any
from glob import glob
from pygls import types
from pygls.features import (HOVER, COMPLETION, DEFINITION, REFERENCES, RENAME,
                            TEXT_DOCUMENT_DID_CHANGE, INITIALIZE,
                            WORKSPACE_DID_CHANGE_WORKSPACE_FOLDERS,
                            WORKSPACE_DID_CHANGE_CONFIGURATION)
from pygls.server import LanguageServer
from bibparse import Biblio
from .bibliography import key_positions
from .completion import generate_list
from .format import info
from .document import get_references, find_key

cached_bibliographies = Biblio()
workspace_folders = []
configuration = {'bibliographies': ['~/*.bib']}
keys = {}


class CitationLanguageServer(LanguageServer):
    """Language Server Class"""
    CONFIGURATION_SECTION = 'citation'

    def __init__(self):
        super().__init__()


citation_langserver = CitationLanguageServer()


def __handle_glob(my_file: List[str]) -> List[str]:
    output = []
    for file in my_file:
        if file.count("*") > 0:
            output.extend(glob(file))
        else:
            output.append(file)
    return output


def __norm_file(my_file: str) -> List[str]:
    output = [my_file]
    if my_file[0] == '.':
        output = [
            os.path.join(directory, my_file) for directory in workspace_folders
        ]
    return [os.path.normpath(os.path.expanduser(file)) for file in output]


def __read_bibliographies(bibliographies: List[str]) -> None:
    cached_bibliographies.clear()
    for file in bibliographies:
        __read_bibliography(file)


def __read_bibliography(maybe_glob: List[str]) -> None:
    for file in __handle_glob(__norm_file(maybe_glob)):
        if not os.path.exists(file):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                                    file)
        cached_bibliographies.read(os.path.abspath(file))
        keys.update(key_positions(file))


def __update_bibliography_configuration(config: List[Any]) -> None:
    bibliographies = getattr(config[0], 'bibliographies')
    if bibliographies != configuration['bibliographies']:
        configuration['bibliographies'] = bibliographies
        __read_bibliographies(configuration['bibliographies'])


markdown_files = {}


def get_markdown_file(ls: LanguageServer,
                      uri: str,
                      update: bool = False) -> Dict[str, str]:
    """Given a document uri and a language server, get the cached file contents"""
    result = None if update else markdown_files.get(uri)
    if not result:
        document = ls.workspace.get_document(uri)
        result = {'source': document.source, 'path': document.path}
        markdown_files[uri] = result
    return result


@citation_langserver.feature(INITIALIZE)
def initialize(ls: LanguageServer, params: types.InitializeParams) -> None:
    """Initialization handler; sets rootPath and gets configuration, if possible"""
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
def did_change(ls: LanguageServer,
               params: types.DidChangeTextDocumentParams) -> None:
    """Update document cache on document change event."""
    get_markdown_file(ls, params.textDocument.uri, True)


@citation_langserver.feature(WORKSPACE_DID_CHANGE_CONFIGURATION)
def did_change_configuration(
        ls: LanguageServer,
        params: types.DidChangeConfigurationParams) -> None:
    """Change the bibliography path on configuration change"""
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
        _ls: LanguageServer,
        params: types.DidChangeWorkspaceFoldersParams) -> None:
    """Handle opening and closing files in the workspace"""
    workspace_folders.extend(params.event.added)
    for folder in params.event.removed:
        workspace_folders.remove(folder)
    __read_bibliographies(configuration['bibliographies'])


@citation_langserver.feature(HOVER)
def hover(ls: LanguageServer,
          params: types.TextDocumentPositionParams) -> types.Hover:
    """Get hover information for a symbol, if present at position"""
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
def completion(ls: LanguageServer,
               params: types.CompletionParams = None) -> types.CompletionList:
    """Handle completion if the user is typing a key"""
    markdown_file = get_markdown_file(ls, params.textDocument.uri)
    key, *_ = find_key(markdown_file, params.position)
    if key is None:
        return []
    return types.CompletionList(
        False, list(generate_list(cached_bibliographies, search_key=key)))


@citation_langserver.feature(DEFINITION)
def definition(
        ls: LanguageServer,
        params: types.TextDocumentPositionParams = None) -> types.Location:
    """Goto definition of symbol, if a bibliography key is present"""
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


@citation_langserver.feature(REFERENCES)
def references(ls: LanguageServer,
               params: types.ReferenceParams = None) -> List[types.Location]:
    """Find references to current symbol, if a bibliography key is present"""
    markdown_file = get_markdown_file(ls, params.textDocument.uri)
    key, *_ = find_key(markdown_file, params.position)
    if key is None:
        return None
    return get_references(markdown_file, key)


@citation_langserver.feature(RENAME)
def rename(ls: LanguageServer,
           params: types.RenameParams = None) -> types.WorkspaceEdit:
    """Rename the symbol, if a bibliography key is present"""
    markdown_file = get_markdown_file(ls, params.textDocument.uri)
    key, *_ = find_key(markdown_file, params.position)
    new_key = params.newName
    output = {}
    output[params.textDocument.uri] = [
        types.TextEdit(
            range=loc.range,
            new_text=new_key,
        ) for loc in get_references(markdown_file, key)
    ]
    return types.WorkspaceEdit(changes=output)
