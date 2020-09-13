"""Citation Language Server command line interface."""
import argparse
import logging

from .server import citation_langserver

logging.basicConfig(filename="pygls.log", level=logging.DEBUG, filemode="w")


def add_arguments(parser):
    parser.description = "LanguageServer for BibTeX files"
    parser.add_argument("--tcp",
                        action="store_true",
                        help="Use TCP server instead of stdio")
    parser.add_argument("--host",
                        default="127.0.0.1",
                        help="Bind to this address")
    parser.add_argument("--port",
                        type=int,
                        default=2087,
                        help="Bind to this port")


def cli():
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()

    if args.tcp:
        citation_langserver.start_tcp(args.host, args.port)
    else:
        citation_langserver.start_io()
