from httpie.plugins import FormatterPlugin


class HeadersFormatter(FormatterPlugin):

    def format_headers(self, headers):
        """
        Sorts HTTP header lines by header name, preserving the order of duplicate headers.
        
        Args:
            headers: A string containing HTTP headers, with each header on a separate line.
        
        Returns:
            A string with the first line unchanged and the remaining headers sorted by name, joined by CRLF.
        """
        lines = headers.splitlines()
        headers = sorted(lines[1:], key=lambda h: h.split(':')[0])
        return '\r\n'.join(lines[:1] + headers)
