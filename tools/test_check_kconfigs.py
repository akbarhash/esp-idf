#!/usr/bin/env python
#
# Copyright 2018 Espressif Systems (Shanghai) PTE LTD
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from check_kconfigs import LineRuleChecker
from check_kconfigs import InputError
from check_kconfigs import IndentAndNameChecker


class ApplyLine(object):
    def apply_line(self, string):
        self.checker.process_line(string + '\n', 0)

    def expect_error(self, string, expect, cleanup=None):
        try:
            with self.assertRaises(InputError) as cm:
                self.apply_line(string)
            if expect:
                self.assertEqual(cm.exception.suggested_line, expect + '\n')
        finally:
            if cleanup:
                # cleanup of the previous failure
                self.apply_line(cleanup)

    def expt_success(self, string):
        self.apply_line(string)


class TestLineRuleChecker(unittest.TestCase, ApplyLine):
    def setUp(self):
        self.checker = LineRuleChecker('Kconfig')

    def tearDown(self):
        pass

    def test_tabulators(self):
        self.expect_error('\ttest', expect='    test')
        self.expect_error('\t    test', expect='        test')
        self.expect_error('   \ttest', expect='       test')
        self.expect_error('     \t     test', expect='              test')
        self.expt_success('         test')
        self.expt_success('test')

    def test_trailing_whitespaces(self):
        self.expect_error(' ', expect='')
        self.expect_error('     ', expect='')
        self.expect_error('test ', expect='test')
        self.expt_success('test')
        self.expt_success('')

    def test_line_length(self):
        self.expect_error('x' * 120, expect=None)
        self.expt_success('x' * 119)
        self.expt_success('')


class TestIndentAndNameChecker(unittest.TestCase, ApplyLine):
    def setUp(self):
        self.checker = IndentAndNameChecker('Kconfig')
        self.checker.min_prefix_length = 4

    def tearDown(self):
        self.checker.__exit__('Kconfig', None, None)


class TestIndent(TestIndentAndNameChecker):
    def setUp(self):
        super(TestIndent, self).setUp()
        self.checker.min_prefix_length = 0  # prefixes are ignored in this test case

    def test_indent_characters(self):
        self.expt_success('menu "test"')
        self.expect_error(' test', expect='    test')
        self.expect_error('  test', expect='    test')
        self.expect_error('   test', expect='    test')
        self.expect_error('     test', expect='    test')
        self.expt_success('    test')
        self.expt_success('    test2')
        self.expt_success('    config')
        self.expect_error('    default', expect='        default')
        self.expt_success('        help')
        self.expect_error('         text', expect='            text')
        self.expt_success('            help text')
        self.expt_success('    menu')
        self.expt_success('    endmenu')
        self.expect_error('         choice', expect='    choice', cleanup='    endchoice')
        self.expect_error('       choice', expect='    choice', cleanup='    endchoice')
        self.expt_success('    choice')
        self.expt_success('    endchoice')
        self.expt_success('    config')
        self.expt_success('endmenu')

    def test_help_content(self):
        self.expt_success('menu "test"')
        self.expt_success('    config')
        self.expt_success('        help')
        self.expt_success('            description')
        self.expt_success('            config keyword in the help')
        self.expt_success('            menu keyword in the help')
        self.expt_success('            menuconfig keyword in the help')
        self.expt_success('            endmenu keyword in the help')
        self.expt_success('            endmenu keyword in the help')
        self.expt_success('            endmenu keyword in the help')
        self.expect_error('          menu "real menu with wrong indent"',
                          expect='    menu "real menu with wrong indent"', cleanup='    endmenu')
        self.expt_success('endmenu')

    def test_mainmenu(self):
        self.expt_success('mainmenu "test"')
        self.expect_error('test', expect='    test')
        self.expt_success('    not_a_keyword')
        self.expt_success('    config')
        self.expt_success('    menuconfig')
        self.expect_error('test', expect='        test')
        self.expect_error('   test', expect='        test')
        self.expt_success('    menu')
        self.expt_success('    endmenu')

    def test_ifendif(self):
        self.expt_success('menu "test"')
        self.expt_success('    config')
        self.expt_success('        help')
        self.expect_error('        if', expect='    if', cleanup='    endif')
        self.expt_success('    if')
        self.expect_error('    config', expect='        config')
        self.expt_success('        config')
        self.expt_success('            help')
        self.expt_success('    endif')
        self.expt_success('    config')
        self.expt_success('endmenu')


class TestName(TestIndentAndNameChecker):
    def setUp(self):
        super(TestName, self).setUp()
        self.checker.min_prefix_length = 0  # prefixes are ignored in this test case

    def test_name_length(self):
        self.expt_success('menu "test"')
        self.expt_success('    config ABC')
        self.expt_success('    config ' + ('X' * 50))
        self.expect_error('    config ' + ('X' * 51), expect=None)
        self.expt_success('    menuconfig ' + ('X' * 50))
        self.expect_error('    menuconfig ' + ('X' * 51), expect=None)
        self.expt_success('    choice ' + ('X' * 50))
        self.expect_error('    choice ' + ('X' * 51), expect=None)
        self.expt_success('endmenu')


class TestPrefix(TestIndentAndNameChecker):
    def test_prefix_len(self):
        self.expt_success('menu "test"')
        self.expt_success('    config ABC_1')
        self.expt_success('    config ABC_2')
        self.expt_success('    config ABC_DEBUG')
        self.expt_success('    config ABC_ANOTHER')
        self.expt_success('endmenu')
        self.expt_success('menu "test2"')
        self.expt_success('    config A')
        self.expt_success('    config B')
        self.expect_error('endmenu', expect=None)

    def test_choices(self):
        self.expt_success('menu "test"')
        self.expt_success('    choice ASSERTION_LEVEL')
        self.expt_success('        config ASSERTION_DEBUG')
        self.expt_success('        config ASSERTION_RELEASE')
        self.expt_success('        menuconfig ASSERTION_XY')
        self.expt_success('    endchoice')
        self.expt_success('    choice DEBUG')
        self.expt_success('        config DE_1')
        self.expt_success('        config DE_2')
        self.expect_error('    endchoice', expect=None)
        self.expect_error('endmenu', expect=None)

    def test_nested_menu(self):
        self.expt_success('menu "test"')
        self.expt_success('    config DOESNT_MATTER')
        self.expt_success('    menu "inner menu"')
        self.expt_success('        config MENUOP_1')
        self.expt_success('        config MENUOP_2')
        self.expt_success('        config MENUOP_3')
        self.expt_success('    endmenu')
        self.expt_success('endmenu')

    def test_nested_ifendif(self):
        self.expt_success('menu "test"')
        self.expt_success('    config MENUOP_1')
        self.expt_success('    if MENUOP_1')
        self.expt_success('        config MENUOP_2')
        self.expt_success('    endif')
        self.expt_success('endmenu')


if __name__ == '__main__':
    unittest.main()
