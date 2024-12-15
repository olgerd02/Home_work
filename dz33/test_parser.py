# test_parser.py

import unittest
from parser_module import tokenize, Parser

class TestParser(unittest.TestCase):
    def test_numbers(self):
        code = '12345'
        tokens = tokenize(code)
        parser = Parser(tokens)
        result = parser.parse()
        self.assertEqual(result, ['12345'])

    def test_strings(self):
        code = '@"Hello World"'
        tokens = tokenize(code)
        parser = Parser(tokens)
        result = parser.parse()
        self.assertEqual(result, ['Hello World'])

    def test_list(self):
        code = '(list 1 2 3)'
        tokens = tokenize(code)
        parser = Parser(tokens)
        result = parser.parse()
        self.assertEqual(result, [['1', '2', '3']])

    def test_nested_list(self):
        code = '(list 1 (list 2 3) 4)'
        tokens = tokenize(code)
        parser = Parser(tokens)
        result = parser.parse()
        self.assertEqual(result, [['1', ['2', '3'], '4']])

    def test_const_declaration_and_evaluation(self):
        code = '''
        const x = 100
        const y = @"text"
        (list $[x] $[y])
        '''
        tokens = tokenize(code)
        parser = Parser(tokens)
        result = parser.parse()
        self.assertEqual(result, [['100', 'text']])

    def test_unknown_const(self):
        code = '''
        (list $[unknown])
        '''
        tokens = tokenize(code)
        parser = Parser(tokens)
        with self.assertRaises(NameError):
            parser.parse()

    def test_syntax_error(self):
        code = '''
        (list 1 2 3
        '''
        tokens = tokenize(code)
        parser = Parser(tokens)
        with self.assertRaises(SyntaxError):
            parser.parse()

    def test_comments(self):
        code = '''
        ; Это комментарий
        %{
        Это многострочный
        комментарий
        %}
        (list 1 2 3)
        '''
        tokens = tokenize(code)
        parser = Parser(tokens)
        result = parser.parse()
        self.assertEqual(result, [['1', '2', '3']])

if __name__ == '__main__':
    unittest.main()