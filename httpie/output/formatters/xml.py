from __future__ import absolute_import
import re
from xml.etree import ElementTree

from httpie.plugins import FormatterPlugin


DECLARATION_RE = re.compile('<\?xml[^\n]+?\?>', flags=re.I)
DOCTYPE_RE = re.compile('<!DOCTYPE[^\n]+?>', flags=re.I)


DEFAULT_INDENT = 4


def indent(elem, indent_text=' ' * DEFAULT_INDENT):
    """
    Formats an XML element tree in place with indentation for improved readability.
    
    Args:
        elem: The root XML element to format.
        indent_text: The string used for indentation at each level (default is four spaces).
    
    This function modifies the input element tree directly, adding newlines and indentation
    to the `text` and `tail` properties of each element to produce a pretty-printed XML structure.
    """
    def _indent(elem, level=0):
        """
        Recursively applies indentation and newlines to an XML element and its children.
        
        Modifies the `text` and `tail` properties of each element to ensure proper pretty-print formatting based on the element's nesting level.
        """
        i = "\n" + level * indent_text
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + indent_text
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                _indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    return _indent(elem)


class XMLFormatter(FormatterPlugin):
    # TODO: tests

    def format_body(self, body, mime):
        """
        Formats an XML response body with pretty-printed indentation.
        
        If the MIME type indicates XML, attempts to parse and reformat the body for improved readability, preserving the original XML declaration and DOCTYPE if present. Returns the formatted XML string, or the original body if parsing fails or the MIME type is not XML.
        """
        if 'xml' in mime:
            # FIXME: orig NS names get forgotten during the conversion, etc.
            try:
                root = ElementTree.fromstring(body.encode('utf8'))
            except ElementTree.ParseError:
                # Ignore invalid XML errors (skips attempting to pretty print)
                pass
            else:
                indent(root)
                # Use the original declaration
                declaration = DECLARATION_RE.match(body)
                doctype = DOCTYPE_RE.match(body)
                body = ElementTree.tostring(root, encoding='utf-8')\
                                  .decode('utf8')
                if doctype:
                    body = '%s\n%s' % (doctype.group(0), body)
                if declaration:
                    body = '%s\n%s' % (declaration.group(0), body)
        return body
