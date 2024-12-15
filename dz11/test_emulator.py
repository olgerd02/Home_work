import unittest
import os
import sys
import tarfile
import shutil
from datetime import datetime
from emulator import ShellEmulator
import csv

class TestShellEmulator(unittest.TestCase):
    def setUp(self):
        # Создаем виртуальную файловую систему для тестов
        self.vfs_path = 'testvfs.tar'
        self.tmp_dir = 'tmp'
        test_vfs_dir = 'testvfsdir'
        os.makedirs(os.path.join(test_vfs_dir, 'subdir'), exist_ok=True)
        # Write testfile.txt in binary mode with Unix line endings
        with open(os.path.join(test_vfs_dir, 'testfile.txt'), 'wb') as f:
            f.write(b"Hello World\nThis is a test file.\n")
        # Создаем tar-архив с arcname='.' для правильного извлечения
        with tarfile.open(self.vfs_path, 'w') as tar:
            tar.add(test_vfs_dir, arcname='.')
        shutil.rmtree(test_vfs_dir)
        self.username = 'testuser'
        self.hostname = 'testhost'
        self.script_path = None  # Не используем стартовый скрипт в тестах
        self.emulator = ShellEmulator(self.username, self.hostname, self.vfs_path, self.script_path)

    def tearDown(self):
        # Удаляем временные файлы и директории после тестов
        if os.path.exists(self.vfs_path):
            os.remove(self.vfs_path)
        if self.script_path and os.path.exists(self.script_path):
            os.remove(self.script_path)
        self.emulator.cleanup()
        if os.path.exists('testvfsdir'):
            shutil.rmtree('testvfsdir')
        if os.path.exists('emulator.log'):
            os.remove('emulator.log')

    # Тесты для команды ls
    def test_ls_root_directory(self):
        output = self.emulator.ls()
        self.assertIn('subdir', output)
        self.assertIn('testfile.txt', output)

    def test_ls_empty_directory(self):
        self.emulator.cd('subdir')
        output = self.emulator.ls()
        self.assertEqual(output, 'Пустая директория')

    def test_ls_nonexistent_directory(self):
        self.emulator.current_directory = 'nonexistent'
        output = self.emulator.ls()
        self.assertEqual(output, 'Ошибка: директория не найдена')

    # Тесты для команды cd
    def test_cd_to_subdirectory(self):
        output = self.emulator.cd('subdir')
        self.assertEqual(output, 'Перешел в subdir')
        self.assertEqual(self.emulator.current_directory, 'subdir')

    def test_cd_to_parent_directory(self):
        self.emulator.current_directory = 'subdir'
        output = self.emulator.cd('..')
        self.assertEqual(output, 'Перешел в /')
        self.assertEqual(self.emulator.current_directory, '')

    def test_cd_nonexistent_directory(self):
        output = self.emulator.cd('nonexistent')
        self.assertEqual(output, 'Ошибка: директория не найдена')
        self.assertEqual(self.emulator.current_directory, '')

    # Тесты для команды exit
    def test_exit_emulator(self):
        with self.assertRaises(SystemExit) as cm:
            self.emulator.exit_emulator()
        self.assertEqual(str(cm.exception), 'Эмулятор завершен')

    def test_exit_cleans_up_tmp_dir(self):
        try:
            self.emulator.exit_emulator()
        except SystemExit:
            pass
        self.assertFalse(os.path.exists(self.emulator.tmp_dir))

    def test_exit_logs_command(self):
        try:
            self.emulator.execute_command('exit')
        except SystemExit:
            pass
        with open('emulator.log', 'r', encoding='utf8') as f:
            logs = f.read()
        self.assertIn('exit', logs)


    # Тесты для команды wc
    def test_wc_existing_file(self):
        output = self.emulator.wc('testfile.txt')
        full_path = os.path.join(self.emulator.tmp_dir, 'testfile.txt')
        expected_bytes = os.path.getsize(full_path)
        expected_lines = 2  # Known number of lines
        expected_words = 7  # Known number of words
        expected_output = f'{expected_lines} {expected_words} {expected_bytes} testfile.txt'
        self.assertEqual(output, expected_output)

    def test_wc_nonexistent_file(self):
        output = self.emulator.wc('nofile.txt')
        self.assertEqual(output, 'Ошибка: файл не найден')

    def test_wc_no_filename(self):
        output = self.emulator.wc()
        self.assertEqual(output, 'Ошибка: не указано имя файла')

    # Тесты для команды history
    def test_history_after_commands(self):
        self.emulator.execute_command('ls')
        self.emulator.execute_command('cd subdir')
        output = self.emulator.show_history()
        expected_history = ['ls', 'cd subdir']
        self.assertEqual(output.split('\n'), expected_history)

    def test_history_empty(self):
        output = self.emulator.show_history()
        self.assertEqual(output, '')

    def test_history_command_logged(self):
        self.emulator.execute_command('history')
        self.assertIn('history', self.emulator.history)

    # Тесты для команды du
    def test_du_current_directory(self):
        output = self.emulator.du()
        # Check that output starts with a number indicating size
        self.assertRegex(output, r'^\d+ \.$')

    def test_du_specific_file(self):
        output = self.emulator.du('testfile.txt')
        full_path = os.path.join(self.emulator.tmp_dir, 'testfile.txt')
        expected_size = os.path.getsize(full_path)
        expected_output = f'{expected_size} testfile.txt'
        self.assertEqual(output, expected_output)

    def test_du_nonexistent_path(self):
        output = self.emulator.du('nonexistent')
        self.assertEqual(output, 'Ошибка: путь не найден')

if __name__ == '__main__':
    unittest.main()
