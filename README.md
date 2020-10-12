# citation-langserver

This uses the [Language Server Protocol](https://langserver.org/) to handle the inclusion and management of citations stored in BibTeX and BibLaTeX (`.bib`) files.

# Installation

Run `pip3 citation-langserver` to install.

# Usage

Configure `citation-langserver` as you would any other LSP in your text editor of choice.

For instance, using [CoC](https://github.com/neoclide/coc.nvim) in vim, you might add the following to your `coc-settings.json` file:

```json
  "languageserver": {
    "citation": {
      "command": "/usr/local/bin/citation-langserver",
      "filetypes": ["markdown"],
      "settings": {
        "citation": {
          "bibliographies": [
            "~/library.bib",
			"./*.bib"
          ]
        }
      }
    }
  }
```

## Configuration

The setting `citation.bibliographies` needs to be sent by the client to the server and contain an array of file paths. The file paths can include:

- Absolute paths
- Relative paths
- Globs (absolute or relative)
