"""
EXE входна точка за CVRP програма
Този файл се използва за създаване на EXE файл с PyInstaller
"""

import sys
import os
import logging
import shutil
from pathlib import Path
import importlib.util

def setup_exe_environment():
    """Настройва средата за EXE изпълнение"""
    # Променяме работната директория към директорията на EXE файла
    if getattr(sys, 'frozen', False):
        # Ако е EXE файл, използваме директорията на EXE файла
        exe_dir = Path(sys.executable).parent
        os.chdir(exe_dir)
        print(f"📁 Работна директория: {exe_dir}")
    else:
        # Ако е Python скрипт, използваме директорията на скрипта
        script_dir = Path(__file__).parent
        os.chdir(script_dir)
        print(f"📁 Работна директория: {script_dir}")
    
    # Създаваме необходимите директории ако не съществуват
    directories = ['logs', 'output', 'cache', 'data', 'output/excel', 'output/charts']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    # Настройваме logging за EXE
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/cvrp_exe.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

# Забележка: Функцията copy_output_files е премахната, тъй като сега файловете
# се създават директно в правилните директории, без нужда от копиране

# Динамично зареждане на config.py от директорията на EXE файла
def load_config():
    if getattr(sys, 'frozen', False):
        # За EXE файл, използваме директорията на EXE файла
        exe_dir = Path(sys.executable).parent
        config_path = exe_dir / 'config.py'
    else:
        # За Python скрипт, използваме директорията на скрипта
        script_dir = Path(__file__).parent
        config_path = script_dir / 'config.py'
    
    if config_path.exists():
        spec = importlib.util.spec_from_file_location('config', str(config_path))
        if spec and spec.loader:
            config = importlib.util.module_from_spec(spec)
            sys.modules['config'] = config
            spec.loader.exec_module(config)
            
            # Важно: Тук променяме пътя до входния файл да бъде спрямо EXE директорията, а не хардкоднат
            if getattr(sys, 'frozen', False):
                exe_dir = Path(sys.executable).parent
                # Променяме пътя на входния файл
                input_config = config.get_config().input
                input_config.excel_file_path = str(exe_dir / 'data' / 'input.xlsx')
                print(f"📝 Пренасочвам входния файл към: {input_config.excel_file_path}")
                
                # Променяме и пътищата на изходните файлове
                output_config = config.get_config().output
                output_config.map_output_file = str(exe_dir / 'output' / 'interactive_map.html')
                output_config.excel_output_dir = str(exe_dir / 'output' / 'excel')
                output_config.charts_output_dir = str(exe_dir / 'output' / 'charts')
                print(f"📝 Пренасочвам изходните файлове към директория: {exe_dir / 'output'}")
            
            print(f"✅ Конфигурация заредена от: {config_path}")
        else:
            print(f"⚠️ Не мога да заредя config.py от: {config_path}")
    else:
        print(f"⚠️ config.py не е намерен в: {config_path}")

# Добавяме директорията на EXE файла към Python path
if getattr(sys, 'frozen', False):
    exe_dir = Path(sys.executable).parent
    sys.path.insert(0, str(exe_dir))
else:
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))

# Импортираме главната функция
from main import main

def main_exe():
    """Главна функция за EXE"""
    while True:  # Добавяме безкраен цикъл за повторно стартиране
        try:
            setup_exe_environment()
            load_config()
            
            print("🚀 Стартиране на CVRP оптимизация...")
            print("=" * 50)
            
            # Проверяваме дали има входен файл като аргумент
            input_file = None
            current_dir = os.getcwd()
            
            if len(sys.argv) > 1:
                input_file = sys.argv[1]
                print(f"📁 Използвам входен файл от аргумент: {input_file}")
            else:
                # Търсим подразбиращ се файл - първо проверяваме в текущата директория
                default_files = [
                    os.path.join(current_dir, 'data', 'input.xlsx'), 
                    os.path.join(current_dir, 'input.xlsx')
                ]
                
                for file_path in default_files:
                    if os.path.exists(file_path):
                        input_file = file_path
                        print(f"📁 Намерен входен файл: {input_file}")
                        break
                
                if not input_file:
                    print("⚠️ Не е намерен входен файл. Създайте data/input.xlsx или посочете файл като аргумент.")
                    print("💡 Пример: CVRP_Optimizer.exe data/my_data.xlsx")
                    input("\nНатиснете Enter за да затворите програмата...")
                    sys.exit(1)
            
            # Заменяме sys.argv с правилните аргументи
            original_argv = sys.argv.copy()
            sys.argv = [sys.argv[0]]  # Запазваме само името на програмата
            if input_file:
                sys.argv.append(input_file)
            
            # Принтираме информация за пътя на файла, за да е по-ясно къде се търси
            print(f"📁 Използвам файл: {input_file}")
            print(f"📁 Текуща директория: {current_dir}")
            
            # Изпълняваме главната функция
            main()
            
            # Възстановяваме оригиналните аргументи
            sys.argv = original_argv
            
            # Не копираме файлове, те се създават директно в правилните директории
            print("\n✅ Програмата завърши успешно!")
            print(f"📁 Резултатите са в директорията: {os.path.join(current_dir, 'output')}")
            
            # Питаме потребителя дали иска да стартира програмата отново
            restart = input("\n🔄 Искате ли да стартирате програмата отново? (да/не): ").lower().strip()
            if restart != 'да' and restart != 'y' and restart != 'yes' and restart != 'д':
                print("👋 Благодаря, че използвахте програмата! Довиждане!")
                break  # Излизаме от безкрайния цикъл
            
        except KeyboardInterrupt:
            print("\n⚠️ Програмата е прекъсната от потребителя.")
            restart = input("\n🔄 Искате ли да стартирате програмата отново? (да/не): ").lower().strip()
            if restart != 'да' and restart != 'y' and restart != 'yes' and restart != 'д':
                print("👋 Благодаря, че използвахте програмата! Довиждане!")
                break  # Излизаме от безкрайния цикъл
        except Exception as e:
            print(f"\n❌ Грешка при изпълнение: {e}")
            logging.error(f"EXE грешка: {e}", exc_info=True)
            
            # Питаме потребителя дали иска да опита отново въпреки грешката
            restart = input("\n🔄 Искате ли да стартирате програмата отново? (да/не): ").lower().strip()
            if restart != 'да' and restart != 'y' and restart != 'yes' and restart != 'д':
                print("👋 Благодаря, че използвахте програмата! Довиждане!")
                break  # Излизаме от безкрайния цикъл

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main_exe() 