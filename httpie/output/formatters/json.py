from __future__ import absolute_import
import json

from httpie.plugins import FormatterPlugin


DEFAULT_INDENT = 4


class JSONFormatter(FormatterPlugin):

    def format_body(self, body, mime):
        """
        Formats the body as pretty-printed JSON if the MIME type indicates JSON.
        
        If the MIME type contains 'json', attempts to parse and reformat the body with sorted keys, UTF-8 characters, and indentation for readability. Returns the original body if parsing fails or if the MIME type does not indicate JSON.
        """
        if 'json' in mime:
            try:
                obj = json.loads(body)
            except ValueError:
                # Invalid JSON, ignore.
                pass
            else:
                # Indent, sort keys by name, and avoid
                # unicode escapes to improve readability.
                body = json.dumps(obj,
                                  sort_keys=True,
                                  ensure_ascii=False,
                                  indent=DEFAULT_INDENT)
        return body
