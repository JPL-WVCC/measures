import re
import lxml.etree
from StringIO import StringIO


NS_RE = re.compile(r'\s+xmlns:?(\w*?)\s*=\s*[\'"](.*?)[\'"]')

NS = {
    'xs': 'http://www.w3.org/2001/XMLSchema',
    'py': 'http://sciflo.jpl.nasa.gov/2006v1/py',
    'sf': 'http://sciflo.jpl.nasa.gov/2006v1/sf',
}


def get_nsmap(xml):
    """Extract namespace prefixes. Return namespace prefix dict."""

    nsmap = {}
    matches = NS_RE.findall(xml)
    for match in matches:
        prefix = match[0]; ns = match[1]
        if prefix == '': prefix = '_'
        nsmap[prefix] = ns
    return nsmap


def get_etree(xml):
    """Return lxml etree root."""

    return lxml.etree.parse(
        StringIO(xml),
        lxml.etree.XMLParser(remove_blank_text=True)
    ).getroot()
