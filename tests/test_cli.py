"""CLI argument parsing related tests."""
import json
# noinspection PyCompatibility
import argparse

import pytest
from requests.exceptions import InvalidSchema

from httpie import input
from httpie.input import KeyValue, KeyValueArgType, DataDict
from httpie import ExitStatus
from httpie.cli import parser
from utils import TestEnvironment, http, HTTP_OK
from fixtures import (
    FILE_PATH_ARG, JSON_FILE_PATH_ARG,
    JSON_FILE_CONTENT, FILE_CONTENT, FILE_PATH
)


class TestItemParsing:

    key_value = KeyValueArgType(*input.SEP_GROUP_ALL_ITEMS)

    def test_invalid_items(self):
        """
        Tests that items without a valid key-value separator raise an ArgumentTypeError.
        """
        items = ['no-separator']
        for item in items:
            pytest.raises(argparse.ArgumentTypeError, self.key_value, item)

    def test_escape_separator(self):
        """
        Tests that escaped separator characters in CLI key-value arguments are correctly parsed.
        
        Verifies that colons, at signs, and equal signs can be escaped in headers, data, and file fields, ensuring the resulting keys and values preserve the intended characters.
        """
        items = input.parse_items([
            # headers
            self.key_value(r'foo\:bar:baz'),
            self.key_value(r'jack\@jill:hill'),

            # data
            self.key_value(r'baz\=bar=foo'),

            # files
            self.key_value(r'bar\@baz@%s' % FILE_PATH_ARG),
        ])
        # `requests.structures.CaseInsensitiveDict` => `dict`
        headers = dict(items.headers._store.values())

        assert headers == {
            'foo:bar': 'baz',
            'jack@jill': 'hill',
        }
        assert items.data == {'baz=bar': 'foo'}
        assert 'bar@baz' in items.files

    @pytest.mark.parametrize(('string', 'key', 'sep', 'value'), [
        ('path=c:\windows', 'path', '=', 'c:\windows'),
        ('path=c:\windows\\', 'path', '=', 'c:\windows\\'),
        ('path\==c:\windows', 'path=', '=', 'c:\windows'),
    ])
    def test_backslash_before_non_special_character_does_not_escape(
            self, string, key, sep, value):
        """
            Tests that a backslash before a non-special character does not escape the character.
            
            Verifies that when a backslash precedes a character that is not a recognized separator,
            the character is treated literally in key-value parsing.
            """
            expected = KeyValue(orig=string, key=key, sep=sep, value=value)
        actual = self.key_value(string)
        assert actual == expected

    def test_escape_longsep(self):
        """
        Tests that keys containing escaped long separators (e.g., '\:==') are correctly parsed as part of the key in key-value CLI arguments.
        """
        items = input.parse_items([
            self.key_value(r'bob\:==foo'),
        ])
        assert items.params == {'bob:': 'foo'}

    def test_valid_items(self):
        """
        Tests parsing of various valid CLI key-value items and verifies correct categorization into headers, data, query parameters, and files.
        
        Ensures that different value types (strings, booleans, JSON objects, lists, empty values, file references, and embedded file contents) are parsed and assigned to the appropriate request components.
        """
        items = input.parse_items([
            self.key_value('string=value'),
            self.key_value('header:value'),
            self.key_value('list:=["a", 1, {}, false]'),
            self.key_value('obj:={"a": "b"}'),
            self.key_value('eh:'),
            self.key_value('ed='),
            self.key_value('bool:=true'),
            self.key_value('file@' + FILE_PATH_ARG),
            self.key_value('query==value'),
            self.key_value('string-embed=@' + FILE_PATH_ARG),
            self.key_value('raw-json-embed:=@' + JSON_FILE_PATH_ARG),
        ])

        # Parsed headers
        # `requests.structures.CaseInsensitiveDict` => `dict`
        headers = dict(items.headers._store.values())
        assert headers == {'header': 'value', 'eh': ''}

        # Parsed data
        raw_json_embed = items.data.pop('raw-json-embed')
        assert raw_json_embed == json.loads(JSON_FILE_CONTENT)
        items.data['string-embed'] = items.data['string-embed'].strip()
        assert dict(items.data) == {
            "ed": "",
            "string": "value",
            "bool": True,
            "list": ["a", 1, {}, False],
            "obj": {"a": "b"},
            "string-embed": FILE_CONTENT,
        }

        # Parsed query string parameters
        assert items.params == {'query': 'value'}

        # Parsed file fields
        assert 'file' in items.files
        assert (items.files['file'][1].read().strip().decode('utf8')
                == FILE_CONTENT)

    def test_multiple_file_fields_with_same_field_name(self):
        """
        Tests that multiple file fields with the same name are stored as separate entries.
        
        Verifies that when multiple file inputs with the same field name are provided, they are correctly parsed and stored as multiple entries under that field name.
        """
        items = input.parse_items([
            self.key_value('file_field@' + FILE_PATH_ARG),
            self.key_value('file_field@' + FILE_PATH_ARG),
        ])
        assert len(items.files['file_field']) == 2

    def test_multiple_text_fields_with_same_field_name(self):
        """
        Tests that multiple text fields with the same field name are stored as lists and preserve insertion order.
        """
        items = input.parse_items(
            [self.key_value('text_field=a'),
             self.key_value('text_field=b')],
            data_class=DataDict
        )
        assert items.data['text_field'] == ['a', 'b']
        assert list(items.data.items()) == [
            ('text_field', 'a'),
            ('text_field', 'b'),
        ]


class TestQuerystring:
    def test_query_string_params_in_url(self, httpbin):
        """
        Tests that query string parameters included in the URL are preserved in the HTTP request.
        
        Verifies that the request path and full URL with query parameters are correctly reflected in the request and response.
        """
        r = http('--print=Hhb', 'GET', httpbin.url + '/get?a=1&b=2')
        path = '/get?a=1&b=2'
        url = httpbin.url + path
        assert HTTP_OK in r
        assert 'GET %s HTTP/1.1' % path in r
        assert '"url": "%s"' % url in r

    def test_query_string_params_items(self, httpbin):
        """
        Tests that query string parameters provided as CLI items are correctly appended to the request URL.
        
        Verifies that the parameter is included in both the request line and the JSON response URL.
        """
        r = http('--print=Hhb', 'GET', httpbin.url + '/get', 'a==1')
        path = '/get?a=1'
        url = httpbin.url + path
        assert HTTP_OK in r
        assert 'GET %s HTTP/1.1' % path in r
        assert '"url": "%s"' % url in r

    def test_query_string_params_in_url_and_items_with_duplicates(self,
                                                                  httpbin):
        """
                                                                  Tests that duplicate query parameters from both the URL and CLI items are combined in the request.
                                                                  
                                                                  Verifies that when the same query parameter appears multiple times in both the URL and as CLI items, all instances are included in the final request URL.
                                                                  """
                                                                  r = http('--print=Hhb', 'GET',
                 httpbin.url + '/get?a=1&a=1', 'a==1', 'a==1')
        path = '/get?a=1&a=1&a=1&a=1'
        url = httpbin.url + path
        assert HTTP_OK in r
        assert 'GET %s HTTP/1.1' % path in r
        assert '"url": "%s"' % url in r


class TestURLshorthand:
    def test_expand_localhost_shorthand(self):
        """
        Tests that the ':' shorthand argument is expanded to 'http://localhost' by the parser.
        """
        args = parser.parse_args(args=[':'], env=TestEnvironment())
        assert args.url == 'http://localhost'

    def test_expand_localhost_shorthand_with_slash(self):
        """
        Tests that the `:/` shorthand is expanded to `http://localhost/` in the parsed URL.
        """
        args = parser.parse_args(args=[':/'], env=TestEnvironment())
        assert args.url == 'http://localhost/'

    def test_expand_localhost_shorthand_with_port(self):
        """
        Tests that the localhost shorthand with a port (e.g., ':3000') expands to 'http://localhost:3000'.
        """
        args = parser.parse_args(args=[':3000'], env=TestEnvironment())
        assert args.url == 'http://localhost:3000'

    def test_expand_localhost_shorthand_with_path(self):
        """
        Tests that the localhost shorthand with a path (':/path') expands to 'http://localhost/path'.
        """
        args = parser.parse_args(args=[':/path'], env=TestEnvironment())
        assert args.url == 'http://localhost/path'

    def test_expand_localhost_shorthand_with_port_and_slash(self):
        """
        Tests that the localhost shorthand with a specified port and trailing slash expands to the correct URL.
        """
        args = parser.parse_args(args=[':3000/'], env=TestEnvironment())
        assert args.url == 'http://localhost:3000/'

    def test_expand_localhost_shorthand_with_port_and_path(self):
        """
        Tests that the localhost shorthand with a specified port and path expands to the correct full URL.
        """
        args = parser.parse_args(args=[':3000/path'], env=TestEnvironment())
        assert args.url == 'http://localhost:3000/path'

    def test_dont_expand_shorthand_ipv6_as_shorthand(self):
        """
        Tests that an IPv6 address shorthand (e.g., '::1') is not expanded as a localhost shorthand, but is correctly interpreted as a full URL.
        """
        args = parser.parse_args(args=['::1'], env=TestEnvironment())
        assert args.url == 'http://::1'

    def test_dont_expand_longer_ipv6_as_shorthand(self):
        """
        Tests that IPv6 addresses with extended notation are not expanded as URL shorthand.
        
        Ensures that an IPv6 address like '::ffff:c000:0280' is treated as a full URL and not expanded to a localhost shorthand.
        """
        args = parser.parse_args(
            args=['::ffff:c000:0280'],
            env=TestEnvironment()
        )
        assert args.url == 'http://::ffff:c000:0280'

    def test_dont_expand_full_ipv6_as_shorthand(self):
        """
        Tests that a full IPv6 address is not expanded as a URL shorthand.
        
        Ensures that when a full IPv6 address is provided as an argument, it is treated as a complete URL and not expanded to a localhost shorthand.
        """
        args = parser.parse_args(
            args=['0000:0000:0000:0000:0000:0000:0000:0001'],
            env=TestEnvironment()
        )
        assert args.url == 'http://0000:0000:0000:0000:0000:0000:0000:0001'


class TestArgumentParser:

    def setup_method(self, method):
        """
        Initializes a new instance of HTTPieArgumentParser before each test method.
        """
        self.parser = input.HTTPieArgumentParser()

    def test_guess_when_method_set_and_valid(self):
        """
        Tests that the HTTP method remains unchanged when a valid method is already set.
        """
        self.parser.args = argparse.Namespace()
        self.parser.args.method = 'GET'
        self.parser.args.url = 'http://example.com/'
        self.parser.args.items = []
        self.parser.args.ignore_stdin = False

        self.parser.env = TestEnvironment()

        self.parser._guess_method()

        assert self.parser.args.method == 'GET'
        assert self.parser.args.url == 'http://example.com/'
        assert self.parser.args.items == []

    def test_guess_when_method_not_set(self):
        """
        Tests that the HTTP method defaults to 'GET' when not explicitly set.
        
        Ensures that if no method is provided, the argument parser assigns 'GET' as the HTTP method without altering the URL or items.
        """
        self.parser.args = argparse.Namespace()
        self.parser.args.method = None
        self.parser.args.url = 'http://example.com/'
        self.parser.args.items = []
        self.parser.args.ignore_stdin = False
        self.parser.env = TestEnvironment()

        self.parser._guess_method()

        assert self.parser.args.method == 'GET'
        assert self.parser.args.url == 'http://example.com/'
        assert self.parser.args.items == []

    def test_guess_when_method_set_but_invalid_and_data_field(self):
        """
        Tests that when the HTTP method is invalid and the URL argument resembles a data field,
        the parser sets the method to 'POST', moves the data field to items, and updates the URL.
        """
        self.parser.args = argparse.Namespace()
        self.parser.args.method = 'http://example.com/'
        self.parser.args.url = 'data=field'
        self.parser.args.items = []
        self.parser.args.ignore_stdin = False
        self.parser.env = TestEnvironment()
        self.parser._guess_method()

        assert self.parser.args.method == 'POST'
        assert self.parser.args.url == 'http://example.com/'
        assert self.parser.args.items == [
            KeyValue(key='data',
                     value='field',
                     sep='=',
                     orig='data=field')
        ]

    def test_guess_when_method_set_but_invalid_and_header_field(self):
        """
        Tests that when the HTTP method is invalid and the next argument resembles a header field,
        the method is set to 'GET', the URL is updated, and the argument is moved to items.
        """
        self.parser.args = argparse.Namespace()
        self.parser.args.method = 'http://example.com/'
        self.parser.args.url = 'test:header'
        self.parser.args.items = []
        self.parser.args.ignore_stdin = False

        self.parser.env = TestEnvironment()

        self.parser._guess_method()

        assert self.parser.args.method == 'GET'
        assert self.parser.args.url == 'http://example.com/'
        assert self.parser.args.items, [
            KeyValue(key='test',
                     value='header',
                     sep=':',
                     orig='test:header')
        ]

    def test_guess_when_method_set_but_invalid_and_item_exists(self):
        """
        Tests that when the HTTP method is invalid and a new item is provided as the URL, the new item is appended to the existing items list.
        """
        self.parser.args = argparse.Namespace()
        self.parser.args.method = 'http://example.com/'
        self.parser.args.url = 'new_item=a'
        self.parser.args.items = [
            KeyValue(
                key='old_item', value='b', sep='=', orig='old_item=b')
        ]
        self.parser.args.ignore_stdin = False

        self.parser.env = TestEnvironment()

        self.parser._guess_method()

        assert self.parser.args.items, [
            KeyValue(key='new_item', value='a', sep='=', orig='new_item=a'),
            KeyValue(
                key='old_item', value='b', sep='=', orig='old_item=b'),
        ]


class TestNoOptions:

    def test_valid_no_options(self, httpbin):
        """
        Tests that mutually exclusive CLI flags '--verbose' and '--no-verbose' cancel each other out.
        
        Verifies that when both flags are provided, verbose output is not included in the HTTP request.
        """
        r = http('--verbose', '--no-verbose', 'GET', httpbin.url + '/get')
        assert 'GET /get HTTP/1.1' not in r

    def test_invalid_no_options(self, httpbin):
        """
        Tests that providing an unrecognized `--no-` CLI option results in an error.
        
        Verifies that the CLI exits with a status code of 1, outputs an appropriate error message, and does not attempt to make an HTTP request.
        """
        r = http('--no-war', 'GET', httpbin.url + '/get',
                 error_exit_ok=True)
        assert r.exit_status == 1
        assert 'unrecognized arguments: --no-war' in r.stderr
        assert 'GET /get HTTP/1.1' not in r


class TestIgnoreStdin:

    def test_ignore_stdin(self, httpbin):
        """
        Tests that using --ignore-stdin prevents sending stdin data and defaults the method to GET.
        
        Ensures that when --ignore-stdin is specified, input from stdin is ignored, the HTTP method remains GET, and no stdin data is included in the request.
        """
        with open(FILE_PATH) as f:
            env = TestEnvironment(stdin=f, stdin_isatty=False)
            r = http('--ignore-stdin', '--verbose', httpbin.url + '/get',
                     env=env)
        assert HTTP_OK in r
        assert 'GET /get HTTP' in r, "Don't default to POST."
        assert FILE_CONTENT not in r, "Don't send stdin data."

    def test_ignore_stdin_cannot_prompt_password(self, httpbin):
        """
        Tests that using --ignore-stdin with --auth=no-password results in an error.
        
        Ensures that when standard input is ignored, the CLI cannot prompt for a password, and an appropriate error message is displayed.
        """
        r = http('--ignore-stdin', '--auth=no-password', httpbin.url + '/get',
                 error_exit_ok=True)
        assert r.exit_status == ExitStatus.ERROR
        assert 'because --ignore-stdin' in r.stderr


class TestSchemes:

    def test_custom_scheme(self):
        # InvalidSchema is expected because HTTPie
        # shouldn't touch a formally valid scheme.
        """
        Tests that using a custom URL scheme results in an InvalidSchema exception.
        
        Verifies that HTTPie does not alter formally valid but unsupported URL schemes and raises the appropriate error.
        """
        with pytest.raises(InvalidSchema):
            http('foo+bar-BAZ.123://bah')
