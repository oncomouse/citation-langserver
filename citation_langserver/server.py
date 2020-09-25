"""Citation Language Server.
Creates the language server constant and wraps "features" with it.
Official language server spec:
    https://microsoft.github.io/language-server-protocol/specification
"""
import errno
import os
from glob import glob
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from bibparse import Biblio
from pygls import types
from pygls.features import COMPLETION
from pygls.features import DEFINITION
from pygls.features import HOVER
from pygls.features import INITIALIZE
from pygls.features import INITIALIZED
from pygls.features import REFERENCES
from pygls.features import RENAME
from pygls.features import TEXT_DOCUMENT_DID_CHANGE
from pygls.features import WORKSPACE_DID_CHANGE_CONFIGURATION
from pygls.features import WORKSPACE_DID_CHANGE_WORKSPACE_FOLDERS
from pygls.server import LanguageServer

from .bibliography import key_positions
from .completion import generate_list
from .document import find_key
from .document import get_references
from .format import info

cached_bibliographies = Biblio()
workspace_folders: List[str] = []
configuration = {"bibliographies": ["~/*.bib"]}
keys = {}


class CitationLanguageServer(LanguageServer):
    """Language Server Class"""

    CONFIGURATION_SECTION = "citation"

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
    if my_file[0] == ".":
        output = [os.path.join(directory, my_file)
                  for directory in workspace_folders]
    return [os.path.normpath(os.path.expanduser(file)) for file in output]


def __read_bibliographies(bibliographies: List[str]) -> None:
    cached_bibliographies.clear()
    for file in bibliographies:
        __read_bibliography(file)


def __read_bibliography(maybe_glob: str) -> None:
    for file in __handle_glob(__norm_file(maybe_glob)):
        if not os.path.exists(file):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), file)
        cached_bibliographies.read(os.path.abspath(file))
        keys.update(key_positions(file))


def __update_bibliography_configuration(config: List[Any]) -> None:
    bibliographies = getattr(config[0], "bibliographies")
    if bibliographies != configuration["bibliographies"]:
        configuration["bibliographies"] = bibliographies
        __read_bibliographies(configuration["bibliographies"])


markdown_files: Dict[str, Dict[str, str]] = {}


def get_markdown_file(
    ls: LanguageServer, uri: str, update: bool = False
) -> Dict[str, str]:
    """Given a document uri and a language server, get the cached file contents"""
    result = None if update else markdown_files.get(uri)
    if not result:
        document = ls.workspace.get_document(uri)
        result = {"source": document.source, "path": document.path}
        markdown_files[uri] = result
    return result


has_get_configuration = False


@citation_langserver.feature(INITIALIZE)
def initialize(_ls: LanguageServer, params: types.InitializeParams) -> None:
    """Initialization handler; sets rootPath and gets configuration, if possible"""
    global has_get_configuration
    if params is None:
        return
    if params.rootPath:
        workspace_folders.append(params.rootPath)
    if (
        params.capabilities.workspace is not None
        and params.capabilities.workspace.configuration
    ):
        has_get_configuration = True


@citation_langserver.feature(INITIALIZED)
def initialized(ls: LanguageServer, _params: types.InitializeParams) -> None:
    """Initialization handler; sets rootPath and gets configuration, if possible"""
    if has_get_configuration:
        try:
            ls.get_configuration(
                types.ConfigurationParams(
                    [
                        types.ConfigurationItem(
                            "", CitationLanguageServer.CONFIGURATION_SECTION
                        )
                    ]
                ),
                __update_bibliography_configuration,
            )
        except FileNotFoundError as err:
            ls.show_message(
                "File Not Found Error: {}".format(err), types.MessageType.Error
            )


@citation_langserver.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: LanguageServer, params: types.DidChangeTextDocumentParams) -> None:
    """Update document cache on document change event."""
    get_markdown_file(ls, params.textDocument.uri, True)


@citation_langserver.feature(WORKSPACE_DID_CHANGE_CONFIGURATION)
def did_change_configuration(
    ls: LanguageServer, params: types.DidChangeConfigurationParams
) -> None:
    """Change the bibliography path on configuration change"""
    try:
        __update_bibliography_configuration(
            [getattr(params.settings, CitationLanguageServer.CONFIGURATION_SECTION)]
        )
    except FileNotFoundError as err:
        ls.show_message("File Not Found Error: {}".format(err),
                        types.MessageType.Error)


@citation_langserver.feature(WORKSPACE_DID_CHANGE_WORKSPACE_FOLDERS)
def did_change_workspace_folders(
    _ls: LanguageServer, params: types.DidChangeWorkspaceFoldersParams
) -> None:
    """Handle opening and closing files in the workspace"""
    workspace_folders.extend(map(lambda x: x.name, params.event.added))
    for folder in params.event.removed:
        workspace_folders.remove(folder.name)
    __read_bibliographies(configuration["bibliographies"])


@citation_langserver.feature(HOVER)
def hover(
    ls: LanguageServer, params: types.TextDocumentPositionParams
) -> Optional[types.Hover]:
    """Get hover information for a symbol, if present at position"""
    markdown_file = get_markdown_file(ls, params.textDocument.uri)
    key, start, stop = find_key(markdown_file, params.position)
    if start is None or stop is None:
        return None
    if key is not None and key in cached_bibliographies:
        return types.Hover(
            contents=info(cached_bibliographies[key]),
            range=types.Range(
                start=types.Position(
                    line=params.position.line, character=start),
                end=types.Position(line=params.position.line, character=stop),
            ),
        )
    return None


@citation_langserver.feature(COMPLETION)  # , trigger_characters=['@'])
def completion(
    ls: LanguageServer, params: types.CompletionParams = None
) -> types.CompletionList:
    """Handle completion if the user is typing a key"""
    if params is None:
        return types.CompletionList(False, [])
    markdown_file = get_markdown_file(ls, params.textDocument.uri)
    key, *_ = find_key(markdown_file, params.position)
    if key is None:
        return types.CompletionList(False, [])
    return types.CompletionList(
        False, list(generate_list(cached_bibliographies, search_key=key))
    )


@citation_langserver.feature(DEFINITION)
def definition(
    ls: LanguageServer, params: types.TextDocumentPositionParams = None
) -> Optional[types.Location]:
    """Goto definition of symbol, if a bibliography key is present"""
    if params is None:
        return None
    markdown_file = get_markdown_file(ls, params.textDocument.uri)
    key, *_ = find_key(markdown_file, params.position)
    if key is None or not key in keys:
        return None
    key_position = keys[key]
    return types.Location(
        uri=key_position.textDocument.uri,
        range=types.Range(
            start=key_position.position,
            end=types.Position(
                line=key_position.position.line,
                character=key_position.position.character + len(key),
            ),
        ),
    )


@citation_langserver.feature(REFERENCES)
def references(
    ls: LanguageServer, params: types.ReferenceParams = None
) -> Optional[List[types.Location]]:
    """Find references to current symbol, if a bibliography key is present"""
    if params is None:
        return None
    markdown_file = get_markdown_file(ls, params.textDocument.uri)
    key, *_ = find_key(markdown_file, params.position)
    if key is None:
        return None
    return get_references(markdown_file, key)


@citation_langserver.feature(RENAME)
def rename(
    ls: LanguageServer, params: types.RenameParams = None
) -> Optional[types.WorkspaceEdit]:
    """Rename the symbol, if a bibliography key is present"""
    if params is None:
        return None
    markdown_file = get_markdown_file(ls, params.textDocument.uri)
    key, *_ = find_key(markdown_file, params.position)
    new_key = params.newName
    if key is None:
        return None
    output = {}
    output[params.textDocument.uri] = [
        types.TextEdit(
            range=loc.range,
            new_text=new_key,
        )
        for loc in get_references(markdown_file, key)
    ]
    return types.WorkspaceEdit(changes=output)
