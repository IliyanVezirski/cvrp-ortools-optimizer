"""
Скрипт за компилиране на CVRP програмата в EXE файл
Използва PyInstaller за създаване на standalone EXE

Актуализиран за поддръжка на:
- Всички типове превозни средства (INTERNAL_BUS, CENTER_BUS, EXTERNAL_BUS, SPECIAL_BUS, VRATZA_BUS)
- Логика за център зона и глоби
- Повторно стартиране на програмата след завършване
- PyVRP solver (алтернативен на OR-Tools)
- Множество депа
- Folium карти за визуализация
- Valhalla routing engine (time-dependent routing)
- OSRM routing engine (static routing)
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_dependencies():
    """Проверява дали са инсталирани необходимите пакети"""
    required_packages = ['pyinstaller', 'pandas', 'openpyxl', 'requests', 'numpy', 'folium']
    optional_packages = ['ortools', 'pyvrp', 'tqdm', 'colorama']
    
    print("🔍 Проверявам зависимости...")
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} - OK")
        except ImportError:
            print(f"❌ {package} - НЕ Е ИНСТАЛИРАН")
            missing_packages.append(package)
    
    print("\n🔍 Проверявам опционални пакети...")
    for package in optional_packages:
        try:
            __import__(package)
            print(f"✅ {package} - OK")
        except ImportError:
            print(f"⚠️ {package} - НЕ Е ИНСТАЛИРАН (опционален)")
    
    if missing_packages:
        print(f"\n❌ Липсват задължителни пакети: {', '.join(missing_packages)}")
        return False
    
    return True

def install_dependencies():
    """Инсталира липсващите зависимости"""
    print("\n📦 Инсталирам липсващи зависимости...")
    
    required_packages = ['pyinstaller', 'pandas', 'openpyxl', 'requests', 'numpy', 'folium']
    optional_packages = ['ortools', 'pyvrp', 'tqdm', 'colorama']
    
    print("📦 Инсталирам задължителни пакети...")
    for package in required_packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} - инсталиран")
        except subprocess.CalledProcessError:
            print(f"❌ Грешка при инсталиране на {package}")
            return False
    
    print("\n📦 Инсталирам опционални пакети...")
    for package in optional_packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} - инсталиран")
        except subprocess.CalledProcessError:
            print(f"⚠️ Грешка при инсталиране на {package} (опционален)")
    
    return True

def get_ortools_path():
    """Открива динамично пътя до OR-Tools библиотеката"""
    try:
        import ortools
        ortools_base_path = os.path.dirname(ortools.__file__)
        ortools_lib_path = os.path.join(ortools_base_path, '.libs')
        
        # Проверяваме различни възможни пътища за виртуални среди
        if not os.path.exists(ortools_lib_path):
            # Търсим в текущата виртуална среда
            venv_path = os.environ.get('VIRTUAL_ENV')
            if venv_path:
                possible_paths = [
                    os.path.join(venv_path, 'Lib', 'site-packages', 'ortools', '.libs'),
                    os.path.join(venv_path, 'lib', 'python*', 'site-packages', 'ortools', '.libs')
                ]
                
                for path in possible_paths:
                    import glob
                    matches = glob.glob(path)
                    if matches:
                        ortools_lib_path = matches[0]
                        break
        
        return ortools_base_path, ortools_lib_path
    except ImportError:
        print("⚠️ OR-Tools не е инсталиран или не може да се намери!")
        return None, None

def get_pyvrp_path():
    """Открива динамично пътя до PyVRP библиотеката"""
    try:
        import pyvrp
        pyvrp_base_path = os.path.dirname(pyvrp.__file__)
        
        print(f"✅ PyVRP намерен в: {pyvrp_base_path}")
        return pyvrp_base_path
    except ImportError:
        print("⚠️ PyVRP не е инсталиран или не може да се намери!")
        return None

def create_spec_file():
    """Създава .spec файл за PyInstaller"""
    # Намираме OR-Tools пътища динамично
    ortools_base_path, ortools_lib_path = get_ortools_path()
    
    if not ortools_base_path or not ortools_lib_path:
        print("⚠️ Не успях да намеря OR-Tools инсталацията. Ще използвам стандартни пътища.")
        ortools_base_path = '.venv/Lib/site-packages/ortools'
        ortools_lib_path = '.venv/Lib/site-packages/ortools/.libs'
    
    # Намираме PyVRP пътя динамично
    pyvrp_base_path = get_pyvrp_path()
    
    # Вземаме текущата директория като основна директория на проекта
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Динамично създаваме бинарните пътища за OR-Tools
    binaries = []
    
    # Добавяме OR-Tools DLL файлове
    dll_files = ['ortools.dll', 'abseil_dll.dll', 'libprotobuf.dll', 're2.dll', 
                 'zlib1.dll', 'libscip.dll', 'libutf8_validity.dll', 'highs.dll', 'bz2.dll']
    for dll in dll_files:
        dll_path = os.path.join(ortools_lib_path, dll)
        if os.path.exists(dll_path):
            binaries.append((dll_path, '.'))
    
    # Добавяме OR-Tools PYD файлове
    pyd_files = [
        ('constraint_solver/_pywrapcp.pyd', 'ortools/constraint_solver'),
        ('linear_solver/_pywraplp.pyd', 'ortools/linear_solver')
    ]
    for pyd_file, dest in pyd_files:
        pyd_path = os.path.join(ortools_base_path, pyd_file)
        if os.path.exists(pyd_path):
            binaries.append((pyd_path, dest))
    
    # Добавяме PyVRP PYD файлове (ако е инсталиран)
    if pyvrp_base_path:
        pyvrp_pyd_path = os.path.join(pyvrp_base_path, '_pyvrp.pyd')
        if os.path.exists(pyvrp_pyd_path):
            binaries.append((pyvrp_pyd_path, 'pyvrp'))
            print(f"✅ Добавен PyVRP binary: {pyvrp_pyd_path}")
        
        # Търсим и други .pyd файлове в pyvrp директорията
        import glob
        pyvrp_pyd_files = glob.glob(os.path.join(pyvrp_base_path, '*.pyd'))
        for pyd_file in pyvrp_pyd_files:
            pyd_name = os.path.basename(pyd_file)
            if (pyd_file, 'pyvrp') not in binaries:
                binaries.append((pyd_file, 'pyvrp'))
                print(f"✅ Добавен PyVRP binary: {pyd_name}")
    
    binaries_str = ',\n        '.join([f"(r'{src}', '{dst}')" for src, dst in binaries])
    
    # Подготвяме всички пътища към файловете като стрингове
    pathex_str = repr(project_dir)
    
    # Подготвяме всички data файлове
    data_files = [
        f"(r'{os.path.join(project_dir, 'input_handler.py')}', '.')",
        f"(r'{os.path.join(project_dir, 'warehouse_manager.py')}', '.')",
        f"(r'{os.path.join(project_dir, 'cvrp_solver.py')}', '.')",
        f"(r'{os.path.join(project_dir, 'pyvrp_solver.py')}', '.')",
        f"(r'{os.path.join(project_dir, 'output_handler.py')}', '.')",
        f"(r'{os.path.join(project_dir, 'osrm_client.py')}', '.')",
        f"(r'{os.path.join(project_dir, 'valhalla_client.py')}', '.')",
        f"(r'{os.path.join(project_dir, 'config.py')}', '.')",
        f"(r'{os.path.join(project_dir, 'config_gui.py')}', '.')",
        f"(r'{os.path.join(project_dir, 'main.py')}', '.')",
        f"(r'{os.path.join(project_dir, 'main_exe.py')}', '.')",
        f"(r'{os.path.join(project_dir, 'run_main.py')}', '.')",
        f"(r'{os.path.join(project_dir, 'data')}', 'data')",
        f"(r'{os.path.join(project_dir, 'logs')}', 'logs')",
        f"(r'{os.path.join(project_dir, 'output')}', 'output')",
        # OR-Tools protobuf файлове
        f"(r'{os.path.join(ortools_base_path, 'constraint_solver', 'routing_parameters_pb2.py')}', 'ortools/constraint_solver')",
        f"(r'{os.path.join(ortools_base_path, 'constraint_solver', 'routing_enums_pb2.py')}', 'ortools/constraint_solver')",
        f"(r'{os.path.join(ortools_base_path, 'constraint_solver', 'assignment_pb2.py')}', 'ortools/constraint_solver')",
        f"(r'{os.path.join(ortools_base_path, 'constraint_solver', 'search_stats_pb2.py')}', 'ortools/constraint_solver')",
        f"(r'{os.path.join(ortools_base_path, 'constraint_solver', 'search_limit_pb2.py')}', 'ortools/constraint_solver')",
        f"(r'{os.path.join(ortools_base_path, 'constraint_solver', 'solver_parameters_pb2.py')}', 'ortools/constraint_solver')",
        f"(r'{os.path.join(ortools_base_path, 'constraint_solver', 'routing_ils_pb2.py')}', 'ortools/constraint_solver')",
        f"(r'{os.path.join(ortools_base_path, 'linear_solver', 'linear_solver_pb2.py')}', 'ortools/linear_solver')",
        # OR-Tools __init__.py файлове
        f"(r'{os.path.join(ortools_base_path, '__init__.py')}', 'ortools')",
        f"(r'{os.path.join(ortools_base_path, 'constraint_solver', '__init__.py')}', 'ortools/constraint_solver')",
        f"(r'{os.path.join(ortools_base_path, 'linear_solver', '__init__.py')}', 'ortools/linear_solver')",
        # OR-Tools допълнителни файлове
        f"(r'{os.path.join(ortools_base_path, 'constraint_solver', 'routing_parameters_pb2.pyi')}', 'ortools/constraint_solver')",
        f"(r'{os.path.join(ortools_base_path, 'constraint_solver', 'routing_enums_pb2.pyi')}', 'ortools/constraint_solver')",
        f"(r'{os.path.join(ortools_base_path, 'constraint_solver', 'assignment_pb2.pyi')}', 'ortools/constraint_solver')",
        f"(r'{os.path.join(ortools_base_path, 'constraint_solver', 'search_stats_pb2.pyi')}', 'ortools/constraint_solver')",
        f"(r'{os.path.join(ortools_base_path, 'constraint_solver', 'search_limit_pb2.pyi')}', 'ortools/constraint_solver')",
        f"(r'{os.path.join(ortools_base_path, 'constraint_solver', 'solver_parameters_pb2.pyi')}', 'ortools/constraint_solver')",
        f"(r'{os.path.join(ortools_base_path, 'constraint_solver', 'routing_ils_pb2.pyi')}', 'ortools/constraint_solver')",
        f"(r'{os.path.join(ortools_base_path, 'linear_solver', 'linear_solver_pb2.pyi')}', 'ortools/linear_solver')",
    ]
    
    # Събираме всички data файлове в един string
    data_str = ",\n        ".join(data_files)
    
    # Подготвяме пътищата за иконата и версионния файл
    icon_path = os.path.join(project_dir, 'data', 'icon.ico')
    version_path = os.path.join(project_dir, 'file_version_info.txt')
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main_exe.py'],
    pathex=[{pathex_str}],
    binaries=[
        # OR-Tools DLL и PYD файлове - динамично генерирани
        {binaries_str},
    ],
    datas=[
        # Динамично добавени Python модули и директории
        {data_str},
    ],
    hiddenimports=[
        'ortools',
        'ortools.constraint_solver',
        'ortools.constraint_solver.pywrapcp',
        'ortools.linear_solver',
        'ortools.linear_solver.pywraplp',
        'ortools.constraint_solver.routing_parameters_pb2',
        'ortools.constraint_solver.routing_enums_pb2',
        'ortools.constraint_solver.assignment_pb2',
        'ortools.constraint_solver.search_stats_pb2',
        'ortools.constraint_solver.search_limit_pb2',
        'ortools.constraint_solver.solver_parameters_pb2',
        'ortools.constraint_solver.routing_ils_pb2',
        'ortools.linear_solver.linear_solver_pb2',
        'pandas',
        'pandas._libs',
        'pandas.core',
        'pandas.core.frame',
        'pandas.core.series',
        'pandas.io',
        'pandas.io.excel',
        'pandas.io.excel._openpyxl',
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.workbook',
        'openpyxl.worksheet',
        'requests',
        'numpy',
        'numpy.random',
        'numpy.random._generator',
        'numpy.random._bounded_integers',
        'numpy.random._common',
        'numpy.random._mt19937',
        'numpy.random._pcg64',
        'numpy.random._philox',
        'numpy.random._sfc64',
        'numpy.random._pickle',
        'numpy.random.bit_generator',
        'numpy.random.mtrand',
        'multiprocessing',
        'logging',
        'pathlib',
        'typing',
        'dataclasses',
        'copy',
        'time',
        'os',
        'sys',
        'tqdm',
        'colorama',
        'enum',  # Добавено за поддръжка на VehicleType.SPECIAL_BUS
        # PyVRP модули
        'pyvrp',
        'pyvrp.Model',
        'pyvrp.solve',
        'pyvrp.stop',
        'pyvrp.stop.MaxRuntime',
        'pyvrp._pyvrp',
        # Folium за картите
        'folium',
        'folium.plugins',
        'branca',
        'branca.colormap',
        'jinja2',
        # Valhalla клиент
        'valhalla_client',
        # Matplotlib за графики (ChartGenerator)
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.ticker',
        'matplotlib.backends',
        'matplotlib.backends.backend_agg',
        # HTTP JSON входни данни
        'urllib.request',
        'json',
        'ssl',
        # tkinter за config_gui
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'scipy',
        'PIL',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CVRP_Optimizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r'{icon_path}' if os.path.exists(r'{icon_path}') else None,
    version=r'{version_path}' if os.path.exists(r'{version_path}') else None
)
'''
    
    spec_file_path = os.path.join(project_dir, 'CVRP_Optimizer.spec')
    with open(spec_file_path, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"✅ Създаден CVRP_Optimizer.spec файл в {spec_file_path}")

def create_version_info():
    """Създава файл с информация за версията"""
    # Вземаме текущата година за авторското право
    import datetime
    current_year = datetime.datetime.now().year
    
    version_info = f'''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers=(1, 2, 0, 0),
    prodvers=(1, 2, 0, 0),
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x40004,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'OptioRoute'),
        StringStruct(u'FileDescription', u'CVRP Optimizer - Оптимизация на маршрути'),
        StringStruct(u'FileVersion', u'1.2.0'),
        StringStruct(u'InternalName', u'CVRP_Optimizer'),
        StringStruct(u'LegalCopyright', u'© {current_year} OptioRoute. Всички права запазени.'),
        StringStruct(u'OriginalFilename', u'CVRP_Optimizer.exe'),
        StringStruct(u'ProductName', u'CVRP Optimizer'),
        StringStruct(u'ProductVersion', u'1.2.0')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [0x0409, 1200])])
  ]
)
'''
    
    # Използваме динамичен път за version файла
    project_dir = os.path.dirname(os.path.abspath(__file__))
    version_file_path = os.path.join(project_dir, 'file_version_info.txt')
    
    with open(version_file_path, 'w', encoding='utf-8') as f:
        f.write(version_info)
    
    print(f"✅ Създаден file_version_info.txt файл в {version_file_path}")

def build_exe():
    """Компилира EXE файла"""
    print("\n🔨 Стартирам компилиране на EXE...")
    
    # Взимаме текущата директория на проекта
    project_dir = os.path.dirname(os.path.abspath(__file__))
    spec_file = os.path.join(project_dir, 'CVRP_Optimizer.spec')
    dist_dir = os.path.join(project_dir, '..', 'dist')
    build_dir = os.path.join(project_dir, '..', 'build')
    
    try:
        # Първо опитваме с .spec файла
        print("📋 Опитвам с .spec файла...")
        subprocess.check_call([
            sys.executable, '-m', 'PyInstaller',
            '--clean',
            '--distpath', dist_dir,
            '--workpath', build_dir,
            spec_file
        ])
        
        print("✅ EXE файлът е създаден успешно!")
        
        # Проверяваме дали файлът съществува
        exe_path = Path(os.path.join(dist_dir, 'CVRP_Optimizer.exe'))
        if exe_path.exists():
            print(f"📁 EXE файл: {exe_path.absolute()}")
            return True
        else:
            print("❌ EXE файлът не е създаден!")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Грешка при компилиране с .spec файла: {e}")
        print("🔄 Опитвам с директни опции...")
        
        try:
            # Ако .spec файлът не работи, опитваме с директни опции
            main_exe_path = os.path.join(project_dir, 'main_exe.py')
            subprocess.check_call([
                sys.executable, '-m', 'PyInstaller',
                '--onefile',
                '--console',
                '--name', 'CVRP_Optimizer',
                '--distpath', dist_dir,
                '--workpath', build_dir,
                main_exe_path
            ])
            
            print("✅ EXE файлът е създаден успешно!")
            
            # Проверяваме дали файлът съществува
            exe_path = Path(os.path.join(dist_dir, 'CVRP_Optimizer.exe'))
            if exe_path.exists():
                print(f"📁 EXE файл: {exe_path.absolute()}")
                return True
            else:
                print("❌ EXE файлът не е създаден!")
                return False
                
        except subprocess.CalledProcessError as e2:
            print(f"❌ Грешка при компилиране с директни опции: {e2}")
            return False

def create_batch_file():
    """Създава .bat файл за лесно стартиране"""
    # Използваме динамични пътища за batch файла
    project_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(project_dir, '..', 'dist')
    
    batch_content = '''@echo off
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"
set "PYINSTALLER_RESET_ENVIRONMENT=1"
set "_MEIPASS2="
echo CVRP Optimizer - Starting...
echo.

REM Проверяваме дали има входен файл
if exist "%APP_DIR%data\input.xlsx" (
    echo Input file found: %APP_DIR%data\input.xlsx
    "%APP_DIR%CVRP_Optimizer.exe" "%APP_DIR%data\input.xlsx"
) else (
    echo Input file not found in data\input.xlsx
    echo Place the input file in data\input.xlsx
    echo or in the current directory as input.xlsx
    echo.
    echo Starting with current configuration...
    "%APP_DIR%CVRP_Optimizer.exe"
)
'''
    
    # Създаваме batch файл в dist директорията
    batch_file_path = os.path.join(project_dir, 'start_cvrp.bat')
    
    with open(batch_file_path, 'w', encoding='utf-8-sig') as f:
        f.write(batch_content)
    
    # Копираме batch файла и в dist директорията
    dist_batch_path = os.path.join(dist_dir, 'start_cvrp.bat')
    if not os.path.exists(dist_dir):
        os.makedirs(dist_dir)
    
    with open(dist_batch_path, 'w', encoding='utf-8-sig') as f:
        f.write(batch_content)
    
    print(f"✅ Създаден start_cvrp.bat файл в {batch_file_path} и {dist_batch_path}")

    # Създаваме Settings.bat за настройки
    settings_content = '@echo off\r\nset "APP_DIR=%~dp0"\r\ncd /d "%APP_DIR%"\r\nset "PYINSTALLER_RESET_ENVIRONMENT=1"\r\nset "_MEIPASS2="\r\n"%APP_DIR%CVRP_Optimizer.exe" --settings\r\n'
    for d in [dist_dir, project_dir]:
        if not os.path.exists(d):
            os.makedirs(d)
        bat_path = os.path.join(d, 'Settings.bat')
        with open(bat_path, 'w', encoding='utf-8-sig') as f:
            f.write(settings_content)
    print(f"✅ Създаден Settings.bat")

def main():
    """Главна функция"""
    print("🚀 CVRP Optimizer - EXE Builder")
    print("=" * 40)
    
    # 1. Проверяваме зависимостите
    if not check_dependencies():
        print("\n❌ Липсват зависимости!")
        if input("Искате ли да инсталирам липсващите пакети? (y/n): ").lower() == 'y':
            if not install_dependencies():
                print("❌ Не успях да инсталирам зависимостите!")
                return
        else:
            print("❌ Не можете да продължите без необходимите пакети!")
            return
    
    # 2. Създаваме .spec файла
    create_spec_file()
    
    # 2.1 Създаваме файл с информация за версията
    create_version_info()
    
    # 3. Компилираме EXE
    if build_exe():
        # 4. Създаваме .bat файл и shortcut
        create_batch_file()
        
        # 5. Копираме config.py в dist/ за Settings GUI
        project_dir = os.path.dirname(os.path.abspath(__file__))
        dist_dir = os.path.join(project_dir, '..', 'dist')
        src_config = os.path.join(project_dir, 'config.py')
        dst_config = os.path.join(dist_dir, 'config.py')
        if os.path.exists(src_config):
            shutil.copy2(src_config, dst_config)
            print(f"✅ Копиран config.py в {dist_dir}")
        
        exe_path = os.path.join(dist_dir, 'CVRP_Optimizer.exe')
        
        print("\n🎉 Създаването на EXE файла завърши успешно!")
        print("\n📋 Следващи стъпки:")
        print(f"1. Копирайте {exe_path} в желаната директория")
        print("2. Създайте data/input.xlsx файл с вашите данни в СЪЩАТА директория, където е EXE файлът")
        print("3. За да активирате SPECIAL_BUS, променете enabled=True в config.py")
        print("4. Стартирайте CVRP_Optimizer.exe или start_cvrp.bat")
        print("\n⚠️ ВАЖНО: Входният файл трябва да е в директорията 'data' в СЪЩАТА папка, където е EXE файлът")
        
    else:
        print("\n❌ Създаването на EXE файла се провали!")

if __name__ == "__main__":
    main() 