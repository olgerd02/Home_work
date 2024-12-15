import os
import sys
import tarfile
import csv
from datetime import datetime
import tkinter as tk
from tkinter import scrolledtext
from shutil import rmtree
from collections import deque

class ShellEmulator:
    def __init__(self, username, hostname, vfs_path, script_path):
        self.username = username
        self.hostname = hostname
        self.vfs_path = vfs_path
        self.script_path = script_path
        self.current_directory = ''
        self.start_time = datetime.now()
        self.tmp_dir = 'tmp'
        self.history = deque()
        self.load_virtual_file_system()
        self.commands = {
            'ls': self.ls,
            'cd': self.cd,
            'exit': self.exit_emulator,
            'wc': self.wc,
            'history': self.show_history,
            'du': self.du,
        }
        self.execute_startup_script()

    def load_virtual_file_system(self):
        if os.path.exists(self.tmp_dir):
            rmtree(self.tmp_dir)
        os.makedirs(self.tmp_dir, exist_ok=True)
        with tarfile.open(self.vfs_path) as tar:
            tar.extractall(path=self.tmp_dir)

    def write_log(self, command):
        with open('emulator.log', 'a', encoding='utf8') as logfile:
            logfile.write(f'{datetime.now()} - {self.username}@{self.hostname} - {command}\n')

    def execute_startup_script(self):
        if self.script_path and os.path.exists(self.script_path):
            with open(self.script_path, 'r', encoding='utf8') as script_file:
                for line in script_file:
                    command = line.strip()
                    if command:
                        self.execute_command(command)

    def execute_command(self, command):
        self.write_log(command)
        self.history.append(command)
        command = command.strip()
        if not command:
            return "Ошибка: команда не распознана"
        command_parts = command.split()
        cmd = command_parts[0]
        args = command_parts[1:]
        if cmd in self.commands:
            try:
                return self.commands[cmd](*args)
            except TypeError:
                return f"Ошибка: неверное использование команды '{cmd}'"
            except Exception as e:
                return f"Ошибка: {e}"
        else:
            return "Ошибка: команда не распознана"

    def ls(self):
        path = os.path.join(self.tmp_dir, self.current_directory.strip('/'))
        if os.path.exists(path):
            entries = os.listdir(path)
            if entries:
                return '\n'.join(entries)
            else:
                return "Пустая директория"
        else:
            return "Ошибка: директория не найдена"

    def cd(self, path=None):
        if path is None:
            return "Ошибка: неверное использование команды 'cd'"
        if path == '..':
            if self.current_directory:
                self.current_directory = os.path.dirname(self.current_directory.rstrip('/'))
            if not self.current_directory:
                self.current_directory = ''
            return f"Перешел в {self.current_directory or '/'}"
        else:
            new_directory = os.path.join(self.current_directory, path)
            full_path = os.path.join(self.tmp_dir, new_directory.strip('/'))
            if os.path.isdir(full_path):
                self.current_directory = os.path.normpath(new_directory)
                return f"Перешел в {self.current_directory or '/'}"
            else:
                return "Ошибка: директория не найдена"


    def wc(self, filename=None):
        if filename is None:
            return "Ошибка: не указано имя файла"
        full_path = os.path.join(self.tmp_dir, self.current_directory.strip('/'), filename)
        if not os.path.isfile(full_path):
            return "Ошибка: файл не найден"
        with open(full_path, 'r', encoding='utf8') as file:
            content = file.read()
            lines = content.count('\n')
            words = len(content.split())
            bytes_ = len(content.encode('utf8'))
            return f"{lines} {words} {bytes_} {filename}"

    def show_history(self):
        return '\n'.join(self.history)

    def du(self, path=None):
        target_path = path or '.'
        full_path = os.path.join(self.tmp_dir, self.current_directory.strip('/'), target_path)
        if not os.path.exists(full_path):
            return "Ошибка: путь не найден"
        total_size = 0
        if os.path.isfile(full_path):
            total_size = os.path.getsize(full_path)
        else:
            for dirpath, dirnames, filenames in os.walk(full_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.isfile(fp):
                        total_size += os.path.getsize(fp)
        return f"{total_size} {target_path}"

    def exit_emulator(self):
        self.cleanup()
        sys.exit("Эмулятор завершен")

    def cleanup(self):
        if os.path.exists(self.tmp_dir):
            rmtree(self.tmp_dir)

    def __del__(self):
        self.cleanup()

class GUI:
    def __init__(self, emulator):
        self.emulator = emulator
        self.window = tk.Tk()
        self.window.title("Shell Emulator")
        self.text_area = scrolledtext.ScrolledText(self.window, width=100, height=20)
        self.text_area.pack()
        self.command_entry = tk.Entry(self.window, width=100)
        self.command_entry.pack()
        self.command_entry.focus()
        self.command_entry.bind('<Return>', self.execute_command)
        self.display_output(f"Добро пожаловать, {self.emulator.username}\n")
        self.update_prompt()

    def update_prompt(self):
        prompt = f"{self.emulator.username}@{self.emulator.hostname}:{self.emulator.current_directory or '/'}$ "
        self.command_entry.delete(0, tk.END)
        self.command_entry.insert(0, prompt)
        self.command_entry.icursor(len(prompt))

    def execute_command(self, event):
        prompt_length = len(f"{self.emulator.username}@{self.emulator.hostname}:{self.emulator.current_directory or '/'}$ ")
        command = self.command_entry.get()[prompt_length:]
        output = self.emulator.execute_command(command)
        self.display_output(f"{command}\n{output}\n")
        self.update_prompt()
        if command == 'exit':
            self.window.quit()

    def display_output(self, output):
        self.text_area.insert(tk.END, output)
        self.text_area.yview(tk.END)

    def run(self):
        self.window.mainloop()

def main():
    if len(sys.argv) != 9:
        print("Использование: python emulator.py --username <имя> --hostname <имя> --vfspath <путь> --scriptpath <путь>")
        sys.exit(1)
    username = sys.argv[sys.argv.index('--username') + 1]
    hostname = sys.argv[sys.argv.index('--hostname') + 1]
    vfspath = sys.argv[sys.argv.index('--vfspath') + 1]
    scriptpath = sys.argv[sys.argv.index('--scriptpath') + 1]
    if scriptpath.lower() in ['none', '']:
        scriptpath = None

    emulator = ShellEmulator(username, hostname, vfspath, scriptpath)
    gui = GUI(emulator)
    gui.run()

if __name__ == '__main__':
    main()
