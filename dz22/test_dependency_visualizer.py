import unittest
from unittest.mock import patch, Mock
from dependency_visualizer import build_dependency_graph, generate_plantuml_code
import zipfile
import io  # Убедитесь, что импортируете io вместе с zipfile

class TestNuGetPackage(unittest.TestCase):
    @patch('dependency_visualizer.NuGetPackage.fetch_package')
    def test_get_dependencies_no_dependencies(self, mock_fetch):
        # Подготовка моковых данных
        fake_nupkg_content = self.create_fake_nupkg_content('<metadata></metadata>')
        mock_fetch.return_value = fake_nupkg_content
        from dependency_visualizer import NuGetPackage  # Импортируем здесь, чтобы избежать конфликтов с моками

        package = NuGetPackage('TestPackage', '1.0.0')
        deps = package.get_dependencies()
        self.assertEqual(deps, [])

    @patch('dependency_visualizer.NuGetPackage.fetch_package')
    def test_get_dependencies_with_dependencies(self, mock_fetch):
        nuspec_xml = '''
        <metadata>
            <dependencies>
                <dependency id="DepPackage1" version="1.0.0" />
                <dependency id="DepPackage2" version="2.0.0" />
            </dependencies>
        </metadata>
        '''
        fake_nupkg_content = self.create_fake_nupkg_content(nuspec_xml)
        mock_fetch.return_value = fake_nupkg_content
        from dependency_visualizer import NuGetPackage  # Импортируем здесь, чтобы избежать конфликтов с моками

        package = NuGetPackage('TestPackage', '1.0.0')
        deps = package.get_dependencies()
        expected_deps = [('DepPackage1', '1.0.0'), ('DepPackage2', '2.0.0')]
        self.assertEqual(deps, expected_deps)

    def create_fake_nupkg_content(self, nuspec_metadata_xml):
        # Создаем fake nupkg с nuspec файлом
        nuspec_content = f'''
        <?xml version="1.0"?>
        <package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
            {nuspec_metadata_xml}
        </package>
        '''.strip().encode('utf-8')
        fake_nupkg = io.BytesIO()
        with zipfile.ZipFile(fake_nupkg, 'w') as z:
            z.writestr('TestPackage.nuspec', nuspec_content)
        return fake_nupkg.getvalue()

class TestDependencyGraph(unittest.TestCase):
    def test_build_dependency_graph(self):
        deps_map = {
            'TestPackage:1.0.0': [('Dep1', '1.0.0'), ('Dep2', '1.0.0')],
            'Dep1:1.0.0': [('Dep3', '1.0.0')],
            'Dep2:1.0.0': [],
            'Dep3:1.0.0': []
        }

        # Определяем фабричную функцию для создания мок-объектов NuGetPackage
        def mock_NuGetPackage(name, version, source_url='https://api.nuget.org/v3-flatcontainer'):
            pkg_key = f'{name}:{version}'
            mock_instance = Mock()
            mock_instance.name = name
            mock_instance.version = version
            mock_instance.get_dependencies.return_value = deps_map.get(pkg_key, [])
            mock_instance.package_exists.return_value = True  # Предполагаем, что пакет всегда существует
            return mock_instance

        # Патчим класс NuGetPackage в модуле dependency_visualizer
        with patch('dependency_visualizer.NuGetPackage', side_effect=mock_NuGetPackage):
            from dependency_visualizer import NuGetPackage  # Импортируем здесь, чтобы использовать замоканный класс
            graph = build_dependency_graph('TestPackage', '1.0.0')
            expected_graph = {
                'TestPackage:1.0.0': [('Dep1', '1.0.0'), ('Dep2', '1.0.0')],
                'Dep1:1.0.0': [('Dep3', '1.0.0')],
                'Dep2:1.0.0': [],
                'Dep3:1.0.0': []
            }
            self.assertEqual(graph, expected_graph)

class TestPlantUMLGeneration(unittest.TestCase):
    def test_generate_plantuml_code(self):
        graph = {
            'TestPackage:1.0.0': [('Dep1', '1.0.0'), ('Dep2', '1.0.0')],
            'Dep1:1.0.0': [('Dep3', '1.0.0')],
            'Dep2:1.0.0': [],
            'Dep3:1.0.0': []
        }
        plantuml_code = generate_plantuml_code(graph)
        expected_lines = [
            '@startuml',
            'digraph dependencies {',
            '"TestPackage:1.0.0"',
            '"Dep1:1.0.0"',
            '"TestPackage:1.0.0" -> "Dep1:1.0.0"',
            '"Dep2:1.0.0"',
            '"TestPackage:1.0.0" -> "Dep2:1.0.0"',
            '"Dep3:1.0.0"',
            '"Dep1:1.0.0" -> "Dep3:1.0.0"',
            '}',
            '@enduml'
        ]
        self.assertEqual(plantuml_code.strip().split('\n'), expected_lines)

if __name__ == '__main__':
    unittest.main()