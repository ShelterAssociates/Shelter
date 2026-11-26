import re

from lxml import objectify

_DTD_MARKUP = re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.IGNORECASE)


class UnsafeKMLError(ValueError):
    pass


REJECTED_MESSAGE = "KML files with DOCTYPE or ENTITY declarations are not accepted."


def parse_kml(data):
    """pykml.parser.fromstring equivalent that never resolves entities, loads DTDs or touches the network."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    if _DTD_MARKUP.search(data):
        raise UnsafeKMLError(REJECTED_MESSAGE)
    parser = objectify.makeparser(
        resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False
    )
    root = objectify.fromstring(data, parser=parser)
    # The byte check above misses UTF-16/32 files; the parsed docinfo does not.
    if root.getroottree().docinfo.doctype:
        raise UnsafeKMLError(REJECTED_MESSAGE)
    return root
