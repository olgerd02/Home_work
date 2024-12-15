import json
import sys
import os
import zipfile
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
import argparse
import io  # Необходим для BytesIO
import ssl
import certifi

class NuGetPackage:
    def __init__(self, name, version, source_url='https://api.nuget.org/v3-flatcontainer'):
        self.name = name.lower()
        self.version = version.lower()
        self.source_url = source_url
        self.dependencies = []
        self.nuspec_xml = None

    def package_exists(self):
        # Проверяем наличие пакета, получая список доступных версий
        url = f'{self.source_url}/{self.name}/index.json'
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(url, context=ssl_context) as response:
                data = response.read()
                versions_data = json.loads(data)
                available_versions = versions_data.get('versions', [])
                return self.version in available_versions
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            else:
                raise e
        except Exception as e:
            print(f'Ошибка при проверке наличия пакета {self.name}: {e}')
            return False

    def fetch_package(self):
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        # Создаем URL для загрузки nupkg файла
        url = f'{self.source_url}/{self.name}/{self.version}/{self.name}.{self.version}.nupkg'
        try:
            with urllib.request.urlopen(url, context=ssl_context) as response:
                if response.status != 200:
                    raise Exception(f'Не удалось загрузить пакет {self.name} версии {self.version}')
                return response.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise Exception(f'Пакет {self.name} версии {self.version} не найден.')
            else:
                raise Exception(f'Ошибка HTTP при загрузке пакета {self.name} версии {self.version}: {e}')
        except Exception as e:
            raise Exception(f'Не удалось загрузить пакет {self.name} версии {self.version}: {e}')

    def parse_nuspec(self, nupkg_content):
        with zipfile.ZipFile(io.BytesIO(nupkg_content)) as z:
            nuspec_files = [f for f in z.namelist() if f.endswith('.nuspec')]
            if not nuspec_files:
                raise Exception(f'Файл .nuspec не найден в пакете {self.name}')
            nuspec_content = z.read(nuspec_files[0])
        self.nuspec_xml = ET.fromstring(nuspec_content)
        ns = {'ns': self.nuspec_xml.tag.split('}')[0].strip('{')}
        metadata = self.nuspec_xml.find('ns:metadata', ns)
        if metadata is None:
            raise Exception(f'Метаданные не найдены в пакете {self.name}')
        dependencies = metadata.find('ns:dependencies', ns)
        deps = []
        if dependencies is not None:
            for child in dependencies:
                if child.tag.endswith('group'):
                    for dep in child.findall('ns:dependency', ns):
                        dep_id = dep.attrib.get('id')
                        dep_version = dep.attrib.get('version', '')
                        deps.append((dep_id, dep_version))
                elif child.tag.endswith('dependency'):
                    dep_id = child.attrib.get('id')
                    dep_version = child.attrib.get('version', '')
                    deps.append((dep_id, dep_version))
        self.dependencies = deps

    def get_dependencies(self):
        nupkg_content = self.fetch_package()
        self.parse_nuspec(nupkg_content)
        return self.dependencies

def build_dependency_graph(package_name, package_version, visited=None):
    if visited is None:
        visited = {}
    key = f'{package_name}:{package_version}'
    if key in visited:
        return
    package = NuGetPackage(package_name, package_version)
    if not package.package_exists():
        print(f'Пакет {package_name}:{package_version} не найден в репозитории.')
        visited[key] = []
        return
    try:
        deps = package.get_dependencies()
    except Exception as e:
        print(e)
        deps = []
    visited[key] = deps
    for dep_name, dep_version in deps:
        build_dependency_graph(dep_name, dep_version, visited)
    return visited

def generate_plantuml_code(graph):
    lines = ['@startuml']
    lines.append('digraph dependencies {')
    added_nodes = set()
    for package, deps in graph.items():
        if package not in added_nodes:
            lines.append(f'"{package}"')
            added_nodes.add(package)
        for dep_name, dep_version in deps:
            dep_pkg = f'{dep_name}:{dep_version}'
            if dep_pkg not in added_nodes:
                lines.append(f'"{dep_pkg}"')
                added_nodes.add(dep_pkg)
            lines.append(f'"{package}" -> "{dep_pkg}"')
    lines.append('}')
    lines.append('@enduml')
    return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser(description='Dependency Visualizer')
    parser.add_argument('--graphviz-path', dest='graphviz_path', type=str, help='Путь к программе для визуализации графов', required=False)
    parser.add_argument('--package-name', dest='package_name', type=str, help='Имя анализируемого пакета', required=True)
    parser.add_argument('--package-version', dest='package_version', type=str, help='Версия анализируемого пакета', required=True)
    parser.add_argument('--output-file', dest='output_file', type=str, help='Путь к файлу-результату в виде кода', required=False)
    args = parser.parse_args()

    graph = build_dependency_graph(args.package_name, args.package_version)
    if graph is None:
        print('Не удалось построить граф зависимостей.')
        sys.exit(1)
    plantuml_code = generate_plantuml_code(graph)

    print(plantuml_code)
    if args.output_file:
        with open(args.output_file, 'w', encoding='utf8') as f:
            f.write(plantuml_code)

if __name__ == '__main__':
    main()