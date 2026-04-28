# CVRP OR-Tools Optimizer

Софтуер за дневно планиране на маршрути на бусове с капацитет, работно време, различни депа, зона център, реални пътни разстояния и подробни изходни файлове.

Проектът решава CVRP задача: дадени са клиенти с GPS координати и обем в стекове, налични бусове с различен капацитет и време за обслужване, и целта е да се получат изпълними маршрути с минимално време/разстояние и удобни файлове за диспечиране.

## Какво може програмата

- Чете входни данни от Excel или HTTP JSON.
- Валидира GPS координати, обеми, клиентски номера и документи.
- Разделя заявките между бусове и складова обработка.
- Изчислява матрица с разстояния и времена през OSRM или Valhalla.
- Поддържа два решителя: OR-Tools и PyVRP.
- Поддържа индивидуално време за обслужване по тип бус.
- Поддържа различни начални депа по тип бус.
- Поддържа център зона като кръг или начертан полигон през GUI.
- Позволява при нужда solver-ът да пропуска заявки, като приоритетно по-лесни за пропускане са големи и близки до депото заявки.
- Генерира обща HTML карта, отделни HTML карти за всеки маршрут, Excel отчет, CSV файл и графики.
- В отделните route карти има сгъваем списък с клиенти: бутон `Клиенти`, избор на клиент, popup с обем и бутон за навигация.
- Показва посока на движение по маршрутите с разредени стрелки.
- Добавя дата на стартиране към имената на общата карта, Excel файловете и отделните route карти. CSV файлът остава без дата.
- Има GUI за настройки и Windows Task Scheduler интеграция.
- Може да работи като Python проект или да се build-не до `CVRP_Optimizer.exe`.

## Основни файлове

| Файл | Роля |
|---|---|
| `main.py` | Главен workflow за Python режим. |
| `main_exe.py` | Entry point за PyInstaller/EXE режим. |
| `config.py` | Основна конфигурация: вход, бусове, депа, solver, output, routing. |
| `config_gui.py` | Графичен интерфейс за настройките. |
| `input_handler.py` | Четене на Excel/HTTP JSON и парсване на GPS координати. |
| `warehouse_manager.py` | Предварително разпределение към бусове или склад. |
| `cvrp_solver.py` | OR-Tools solver. |
| `pyvrp_solver.py` | PyVRP solver. |
| `osrm_client.py` | OSRM матрици, кеш и route geometry. |
| `valhalla_client.py` | Valhalla интеграция. |
| `output_handler.py` | HTML карти, Excel, CSV и графики. |
| `build_exe.py` | Автоматизиран build с PyInstaller. |
| `start_cvrp.bat` | Стартира EXE, ако има; иначе стартира през `.venv`. |
| `Settings.bat` | Отваря настройките през EXE или `.venv`. |

## Бърз старт с Python

PowerShell:

```powershell
cd "C:\Programming\Bizant 2.0\cvrp-ortools-optimizer"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Проверка, че OR-Tools е инсталиран в правилната среда:

```powershell
.\.venv\Scripts\python.exe -c "import ortools; print(ortools.__version__)"
```

Стартиране на оптимизатора:

```powershell
.\.venv\Scripts\python.exe main.py
```

Стартиране с конкретен Excel файл:

```powershell
.\.venv\Scripts\python.exe main.py "input\input.xlsx"
```

Стартиране през batch:

```powershell
.\start_cvrp.bat
```

## GUI настройки

```powershell
.\Settings.bat
```

или:

```powershell
.\.venv\Scripts\python.exe config_gui.py
```

GUI-то има табове за:

- Входни данни.
- Превозни средства.
- Предварителна оптимизация/склад.
- Solver настройки.
- Локации и депа.
- Изходни файлове.
- Автоматично стартиране през Windows Task Scheduler.

В таб `Локации` могат да се добавят допълнителни депа във формат:

```text
Име на депо: 42.123456, 23.123456
```

След запис/презареждане тези депа могат да се избират по име за начално депо на видовете бусове.

## Входни данни

Настройките са в `config.py`, клас `InputConfig`.

Поддържани режими:

- `input_source = "excel"`
- `input_source = "http_json"`

По подразбиране Excel файлът е:

```text
input/input.xlsx
```

Основни колони:

| Поле | Примерна колона |
|---|---|
| Клиентски номер | `IdCust` |
| Име на клиент | `Клиент` |
| GPS | `GPS` |
| Обем | `Брой стекове` |
| Документ | `Документ` |

GPS стойностите се очакват като latitude/longitude, например:

```text
42.697357, 23.323810
```

HTTP JSON режимът поддържа URL с дата, декодиране на `utf-8`, `windows-1251`, `latin-1` и mapping на полетата в `InputConfig`.

## Бусове, депа и сервизно време

Всеки `VehicleConfig` има:

- `vehicle_type`
- `enabled`
- `count`
- `capacity`
- `max_time_hours`
- `service_time_minutes`
- `max_customers_per_route`
- `start_location`
- `tsp_depot_location`
- `start_time_minutes`

Важна текуща логика:

- OR-Tools използва vehicle-specific transit callbacks за време.
- PyVRP използва отделни профили по тип бус и добавя service time в edge duration.
- Времето за обслужване вече не е средна стойност за всички бусове.
- При избор на депо през GUI се записва както `start_location`, така и `tsp_depot_location`.

## Център зона

Център зоната може да работи в два режима:

```python
center_zone_mode = "circle"
center_zone_mode = "polygon"
```

При `circle` се използват:

- `center_location`
- `center_zone_radius_km`

При `polygon` се използва:

- `center_zone_polygon`

GUI бутонът `Чертай на карта` отваря локален Leaflet редактор, в който зоната може да се начертае и запише като полигон.

Зоната влияе върху:

- приоритети на center bus;
- ограничения и penalties за други бусове;
- визуализацията върху картите.

## Solver-и

### OR-Tools

Избира се с:

```python
cvrp.solver_type = "or_tools"
```

OR-Tools режимът поддържа:

- capacity dimension;
- time dimension с vehicle-specific service time;
- индивидуални депа;
- пропускане на клиенти чрез `AddDisjunction`;
- индивидуални penalties при priority dropping;
- паралелни стратегии, ако `enable_parallel_solving = True`.

### PyVRP

Избира се с:

```python
cvrp.solver_type = "pyvrp"
```

В `requirements.txt` PyVRP е pin-нат към:

```text
pyvrp>=0.5.0,<0.6.0
```

PyVRP използва същата входна матрица, същите клиенти и същата output структура. Поддържа vehicle-specific service time и priority dropping чрез prize/penalty логика.

Забележка: нито OR-Tools, нито PyVRP в този проект използват видеокарта. По-добрият резултат идва от настройки, време за търсене, матрица с по-точни времена и коректни ограничения, не от GPU.

## Приоритетно пропускане на заявки

Когато `allow_customer_skipping = True`, solver-ът може да остави част от заявките необслужени, ако всички ограничения не могат да се изпълнят.

Когато `enable_priority_dropping = True`, penalty/prize се изчислява индивидуално:

- по-голям обем означава по-лесно пропускане;
- по-близо до депо означава по-лесно пропускане;
- малки и далечни заявки получават по-висока защита.

Основни настройки:

```python
enable_priority_dropping = True
drop_volume_weight = 0.70
drop_closeness_weight = 0.30
min_customer_drop_penalty = 20000
max_customer_drop_penalty = 120000
```

Това не е строго двуфазно правило "само ако няма решение"; това е objective bias. Ако solver-ът пропуска твърде лесно, увеличи `min_customer_drop_penalty` и `max_customer_drop_penalty`.

## Routing engine

Изборът е в `config.routing.engine`:

- `osrm`
- `valhalla`

OSRM е основният режим. Използва:

- централен кеш;
- batch Table API;
- route geometry за визуализация;
- fallback логика при липсващи данни.

Важно: междублоковите връзки вече не се приемат за симетрични. A->B и B->A се попълват отделно, защото еднопосочни улици, забрани и завои могат да правят двете посоки различни.

## Изходни файлове

Основни output директории:

```text
output/
output/routes/
output/excel/
output/charts/
logs/
```

Генерирани файлове:

- обща HTML карта;
- отделна HTML карта за всеки маршрут;
- Excel отчет `cvrp_report_YYYY-MM-DD.xlsx`;
- Excel файлове за склад и маршрути, ако са активни;
- CSV `routes.csv`;
- PNG графики;
- log файл.

Дата се добавя към:

- общата карта;
- отделните route карти;
- Excel файловете.

CSV файлът не се променя по име, за да остане стабилен за външни процеси.

## Карти

Поддържат се два режима:

- Folium/OpenStreetMap/Esri tiles (`map_provider = "osm"`);
- Google Maps (`map_provider = "google"`, изисква API key).

В картите има:

- депа;
- център зона като кръг или полигон;
- цветни маршрути;
- разредени стрелки за посока на движение;
- popup-и с информация за клиенти;
- Google Maps navigation link.

В отделните route карти има сгъваем списък:

- бутон `Клиенти`;
- списък с ред на посещение;
- обем в стекове;
- бутон `Навигация`;
- клик върху клиент центрира картата и отваря popup.

## Build до EXE

Подробно е описано в [BUILD_EXE_README.md](BUILD_EXE_README.md).

Кратко:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe build_exe.py
```

Build-ът създава `CVRP_Optimizer.exe` в `..\dist`.

## Чести проблеми

### "OR-Tools не е инсталиран"

Провери, че стартираш правилния Python:

```powershell
.\.venv\Scripts\python.exe -c "import ortools; print(ortools.__version__)"
```

Ако това работи, но програмата казва, че OR-Tools липсва, стартираш с друг Python или стар стартиращ файл. Използвай:

```powershell
.\start_cvrp.bat
```

### Няма `CVRP_Optimizer.exe`

`start_cvrp.bat` и `Settings.bat` вече имат fallback към `.venv`. Можеш да работиш без EXE.

### Няма route карти или Excel

Провери:

- `output.enable_interactive_map`;
- output директориите;
- правата за запис;
- `logs/cvrp.log`.

### Няма видима посока на картата

Генерирай картите наново. Старите HTML файлове не се обновяват автоматично.

### Списъкът с клиенти не се вижда в отделните карти

Генерирай route картите наново. Новият списък е зад бутон `Клиенти`, за да не закрива картата.
