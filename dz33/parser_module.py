# parser_module.py

import sys
import re
import json

# Определение шаблонов токенов
TOKEN_REGEX = [
    ('MULTILINE_COMMENT_START', r'%\{'),
    ('MULTILINE_COMMENT_END', r'%\}'),
    ('COMMENT', r';[^\n]*'),
    ('CONST', r'\bconst\b'),
    ('EQUALS', r'='),
    ('DOLLAR', r'\$\['),
    ('DOLLAR_END', r'\]'),
    ('LIST_START', r'\(list'),
    ('LIST_END', r'\)'),
    ('STRING', r'@\"(.*?)\"'),
    ('NUMBER', r'\b\d+\b'),
    ('IDENTIFIER', r'\b[_a-zA-Z][_a-zA-Z0-9]*\b'),
    ('WHITESPACE', r'[ \t]+'),
    ('NEWLINE', r'\n'),
]

# Компиляция регулярных выражений
TOKEN_REGEX = [(name, re.compile(pattern)) for name, pattern in TOKEN_REGEX]

# Лексический анализатор
def tokenize(code):
    pos = 0
    tokens = []
    line = 1
    multiline_comment = False

    while pos < len(code):
        match = None
        if not multiline_comment:
            for token_name, token_re in TOKEN_REGEX:
                match = token_re.match(code, pos)
                if match:
                    text = match.group(0)
                    if token_name == 'MULTILINE_COMMENT_START':
                        multiline_comment = True
                    elif token_name == 'COMMENT':
                        pass  # Однострочный комментарий, игнорируем
                    elif token_name == 'WHITESPACE' or token_name == 'NEWLINE':
                        if token_name == 'NEWLINE':
                            line += 1
                        pass  # Пропускаем пробелы и новые строки
                    else:
                        tokens.append((token_name, text, line))
                    pos = match.end(0)
                    break
            else:
                raise SyntaxError(f"Неожиданное выражение на строке {line}: {code[pos]}")
        else:
            # Находим конец многострочного комментария
            end_comment = re.search(r'%\}', code[pos:])
            if end_comment:
                pos += end_comment.end(0)
                multiline_comment = False
            else:
                break  # Многострочный комментарий до конца файла

    return tokens

# Синтаксический анализатор
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.constants = {}

    def parse(self):
        result = []
        while self.pos < len(self.tokens):
            res = self.parse_expression()
            if res is not None:
                result.append(res)
        return result

    def parse_expression(self):
        token = self.peek()
        if token is None:
            return None
        if token[0] == 'CONST':
            return self.parse_const_declaration()
        elif token[0] == 'LIST_START':
            return self.parse_list()
        elif token[0] == 'IDENTIFIER':
            return self.parse_identifier()
        elif token[0] == 'NUMBER':
            return self.consume('NUMBER')[1]
        elif token[0] == 'STRING':
            return self.consume('STRING')[1][2:-1]  # Убираем @" и "
        elif token[0] == 'DOLLAR':
            return self.parse_constant_evaluation()
        else:
            raise SyntaxError(f"Неожиданное выражение на строке {token[2]}: {token[1]}")

    def parse_const_declaration(self):
        self.consume('CONST')
        name = self.consume('IDENTIFIER')[1]
        self.consume('EQUALS')
        value = self.parse_expression()
        self.constants[name] = value
        return None  # Не добавляем в итоговый результат

    def parse_constant_evaluation(self):
        self.consume('DOLLAR')
        name = self.consume('IDENTIFIER')[1]
        self.consume('DOLLAR_END')
        if name in self.constants:
            return self.constants[name]
        else:
            raise NameError(f"Константа {name} не определена")

    def parse_list(self):
        self.consume('LIST_START')
        elements = []
        while True:
            token = self.peek()
            if token is None:
                raise SyntaxError("Ожидается ')' для закрытия списка")
            if token[0] == 'LIST_END':
                self.consume('LIST_END')
                break
            else:
                elements.append(self.parse_expression())
        return elements

    def parse_identifier(self):
        ident = self.consume('IDENTIFIER')[1]
        return ident  # В данном случае просто возвращаем идентификатор

    def consume(self, expected_type):
        token = self.peek()
        if token is None:
            raise SyntaxError("Неожиданный конец ввода")
        if token[0] != expected_type:
            raise SyntaxError(f"Ожидается {expected_type}, найдено {token[0]} на строке {token[2]}")
        self.pos += 1
        return token

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        else:
            return None

# Основная функция для запуска через командную строку
def main():
    if len(sys.argv) != 5:
        print("Использование: parser_module.py -i input_file -o output_file")
        sys.exit(1)

    input_file = None
    output_file = None

    for i in range(1, len(sys.argv), 2):
        if sys.argv[i] == '-i':
            input_file = sys.argv[i + 1]
        elif sys.argv[i] == '-o':
            output_file = sys.argv[i + 1]

    if input_file is None or output_file is None:
        print("Необходимо указать входной и выходной файлы")
        sys.exit(1)

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            code = f.read()
        tokens = tokenize(code)
        parser = Parser(tokens)
        parsed_data = parser.parse()
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=4)
        print("Преобразование завершено успешно")
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()