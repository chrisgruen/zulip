from __future__ import absolute_import
from __future__ import print_function

import sys
import unittest

try:
    from tools.lib.template_parser import (
        TemplateParserException,
        get_tag_info,
        html_tag_tree,
        is_django_block_tag,
        tokenize,
        validate,
    )
except ImportError:
    print('ERROR!!! You need to run this via tools/test-tools.')
    sys.exit(1)

class ParserTest(unittest.TestCase):
    def _assert_validate_error(self, error, fn=None, text=None, check_indent=True):
        # See https://github.com/python/typeshed/issues/372
        # for why we have to ingore types here.
        with self.assertRaisesRegexp(TemplateParserException, error): # type: ignore
            validate(fn=fn, text=text, check_indent=check_indent)

    def test_is_django_block_tag(self):
        # type: () -> None
        self.assertTrue(is_django_block_tag('block'))
        self.assertFalse(is_django_block_tag('not a django tag'))

    def test_validate_vanilla_html(self):
        # type: () -> None
        '''
        Verify that validate() does not raise errors for
        well-formed HTML.
        '''
        my_html = '''
            <table>
                <tr>
                <td>foo</td>
                </tr>
            </table>'''
        validate(text=my_html)

    def test_validate_handlebars(self):
        # type: () -> None
        my_html = '''
            {{#with stream}}
                <p>{{stream}}</p>
            {{/with}}
            '''
        validate(text=my_html)

    def test_validate_django(self):
        # type: () -> None
        my_html = '''
            {% include "some_other.html" %}
            {% if foo %}
                <p>bar</p>
            {% endif %}
            '''
        validate(text=my_html)

    def test_validate_no_start_tag(self):
        # type: () -> None
        my_html = '''
            foo</p>
        '''
        self._assert_validate_error('No start tag', text=my_html)

    def test_validate_mismatched_tag(self):
        # type: () -> None
        my_html = '''
            <b>foo</i>
        '''
        self._assert_validate_error('Mismatched tag.', text=my_html)

    def test_validate_bad_indentation(self):
        # type: () -> None
        my_html = '''
            <p>
                foo
                </p>
        '''
        self._assert_validate_error('Bad indentation.', text=my_html, check_indent=True)

    def test_validate_state_depth(self):
        # type: () -> None
        my_html = '''
            <b>
        '''
        self._assert_validate_error('Missing end tag', text=my_html)

    def test_validate_incomplete_handlebars_tag_1(self):
        # type: () -> None
        my_html = '''
            {{# foo
        '''
        self._assert_validate_error('Tag missing }}', text=my_html)

    def test_validate_incomplete_handlebars_tag_2(self):
        # type: () -> None
        my_html = '''
            {{# foo }
        '''
        self._assert_validate_error('Tag missing }}', text=my_html)

    def test_validate_incomplete_django_tag_1(self):
        # type: () -> None
        my_html = '''
            {% foo
        '''
        self._assert_validate_error('Tag missing %}', text=my_html)

    def test_validate_incomplete_django_tag_2(self):
        # type: () -> None
        my_html = '''
            {% foo %
        '''
        self._assert_validate_error('Tag missing %}', text=my_html)

    def test_validate_incomplete_html_tag_1(self):
        # type: () -> None
        my_html = '''
            <b
        '''
        self._assert_validate_error('Tag missing >', text=my_html)

    def test_validate_incomplete_html_tag_2(self):
        # type: () -> None
        my_html = '''
            <a href="
        '''
        self._assert_validate_error('Tag missing >', text=my_html)

    def test_validate_empty_html_tag(self):
        # type: () -> None
        my_html = '''
            < >
        '''
        self._assert_validate_error('Tag name missing', text=my_html)

    def test_code_blocks(self):
        # type: () -> None

        # This is fine.
        my_html = '''
            <code>
                x = 5
                y = x + 1
            </code>'''
        validate(text=my_html)

        # This is also fine.
        my_html = "<code>process_widgets()</code>"
        validate(text=my_html)

        # This is illegal.
        my_html = '''
            <code>x =
            5</code>
            '''
        self._assert_validate_error('Code tag is split across two lines.', text=my_html)

    def test_anchor_blocks(self):
        # type: () -> None

        # This is allowed, although strange.
        my_html = '''
            <a hef="/some/url">
            Click here
            for more info.
            </a>'''
        validate(text=my_html)

        # This is fine.
        my_html = '<a href="/some/url">click here</a>'
        validate(text=my_html)

        # Even this is fine.
        my_html = '''
            <a class="twitter-timeline" href="https://twitter.com/ZulipStatus"
                data-widget-id="443457763394334720"
                data-screen-name="ZulipStatus"
                >@ZulipStatus on Twitter</a>.
            '''
        validate(text=my_html)


    def test_tokenize(self):
        # type: () -> None
        tag = '<meta whatever>bla'
        token = tokenize(tag)[0]
        self.assertEqual(token.kind, 'html_special')

        tag = '<a>bla'
        token = tokenize(tag)[0]
        self.assertEqual(token.kind, 'html_start')
        self.assertEqual(token.tag, 'a')

        tag = '<br />bla'
        token = tokenize(tag)[0]
        self.assertEqual(token.kind, 'html_singleton')
        self.assertEqual(token.tag, 'br')

        tag = '</a>bla'
        token = tokenize(tag)[0]
        self.assertEqual(token.kind, 'html_end')
        self.assertEqual(token.tag, 'a')

        tag = '{{#with foo}}bla'
        token = tokenize(tag)[0]
        self.assertEqual(token.kind, 'handlebars_start')
        self.assertEqual(token.tag, 'with')

        tag = '{{/with}}bla'
        token = tokenize(tag)[0]
        self.assertEqual(token.kind, 'handlebars_end')
        self.assertEqual(token.tag, 'with')

        tag = '{% if foo %}bla'
        token = tokenize(tag)[0]
        self.assertEqual(token.kind, 'django_start')
        self.assertEqual(token.tag, 'if')

        tag = '{% endif %}bla'
        token = tokenize(tag)[0]
        self.assertEqual(token.kind, 'django_end')
        self.assertEqual(token.tag, 'if')

    def test_get_tag_info(self):
        html = '''
            <p id="test" class="test1 test2">foo</p>
        '''

        start_tag, end_tag = tokenize(html)

        start_tag_info = get_tag_info(start_tag)
        end_tag_info = get_tag_info(end_tag)

        self.assertEqual(start_tag_info.text(), 'p.test1.test2#test')
        self.assertEqual(end_tag_info.text(), 'p')

    def test_html_tag_tree(self):
        # type: () -> None
        html = '''
        <body><p>Hello world</p></body>
        '''
        tree = html_tag_tree(html)
        self.assertEqual(tree.children[0].children[0].token.s, '<p>')
