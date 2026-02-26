"""
Централен конфигурационен файл за CVRP програма с OSRM
Съдържа всички настройки за всички модули
"""

import os
from dataclasses import dataclass, field
# from tkinter import TRUE  # Премахнато за EXE съвместимост
TRUE = True  # Заменяме tkinter.TRUE с Python True
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum


# --- Path Configuration ---
# Определяне на основната директория на проекта.
# __file__ е пътят до текущия файл (config.py).
# os.path.dirname(__file__) е директорията, в която се намира config.py.
# Това прави всички пътища независими от директорията, от която се стартира скриптът.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Helper функция за създаване на абсолютни пътища
def _abs_path(relative_path: str) -> str:
    return os.path.join(PROJECT_ROOT, relative_path)


class RoutingEngine(Enum):
    """Избор на routing engine за изчисляване на матрици."""
    OSRM = "osrm"          # Open Source Routing Machine - бърз, но без traffic
    VALHALLA = "valhalla"  # Valhalla - поддържа time-dependent routing и traffic


class VehicleType(Enum):
    """Типове превозни средства, използвани в системата."""
    INTERNAL_BUS = "internal_bus"  # Стандартен бус за вътрешни маршрути
    CENTER_BUS = "center_bus"      # Специализиран бус за централна градска част
    EXTERNAL_BUS = "external_bus"  # Бус за дълги, извънградски маршрути
    SPECIAL_BUS = "special_bus"    # Нов тип бус със специален режим на работа
    VRATZA_BUS = "vratza_bus"      # Бус от депо Враца
    WAREHOUSE = "warehouse"        # Виртуален тип за заявки, които се обработват от склад
    DISABLED = "disabled"          # Тип за изключени от употреба превозни средства


@dataclass
class VehicleConfig:
    """Конфигурация за един тип превозно средство."""
    vehicle_type: VehicleType  # Тип на превозното средство (от VehicleType enum)
    capacity: int              # Максимален капацитет/обем (в стекове, грамове или друга единица)
    count: int                 # Брой налични превозни средства от този тип
    max_distance_km: Optional[int] = None  # Максимален пробег в километри за един маршрут. None означава без лимит.
    max_time_hours: int = 8    # Максимално време за работа по един маршрут в часове (включва пътуване и обслужване).
    service_time_minutes: int = 15 # Средно време за обслужване на един клиент в минути. Добавя се към общото време на маршрута.
    enabled: bool = True       # Дали този тип превозно средство е активно и може да се използва от solver-а.
    start_location: Optional[Tuple[float, float]] = None  # Персонална начална точка (депо) за този тип. Ако е None, използва се главното депо.
    max_customers_per_route: Optional[int] = None # Максимален брой клиенти, които могат да бъдат обслужени в един маршрут. None = без ограничение.
    start_time_minutes: int = 480  # Стартово време в минути от 00:00 (8:00 = 480 минути)
    tsp_depot_location: Optional[Tuple[float, float]] = None  # Депо за TSP оптимизация. Ако е None, използва start_location или главното депо.


@dataclass
class LocationConfig:
    """GPS координати за важни локации в системата."""
    depot_location: Tuple[float, float] = (42.695785029219415, 23.23165887245312)  # Главно депо, от което тръгват повечето превозни средства.
    center_location: Tuple[float, float] = (42.69735652560932, 23.323809998750914) # Специална локация "Център", използвана за CENTER_BUS.
    vratza_depot_location: Tuple[float, float] = (43.221042895146915, 23.5344026186417)  # Депо във Враца
    center_zone_radius_km: float = 1.7  # Радиус на център зоната в километри
    enable_center_zone_priority: bool = True  # Дали да се прилага приоритет за център зоната
    
    # Параметри за глобата на останалите бусове за влизане в центъра
    external_bus_center_penalty: float = 40000  # Множител за глоба на EXTERNAL_BUS за влизане в центъра
    internal_bus_center_penalty: float = 40000   # Множител за глоба на INTERNAL_BUS за влизане в центъра
    special_bus_center_penalty: float = 40000    # Множител за глоба на SPECIAL_BUS за влизане в центъра
    vratza_bus_center_penalty: float = 40000   # Множител за глоба на VRATZA_BUS за влизане в центъра (като EXTERNAL_BUS)
    enable_center_zone_restrictions: bool = True  # Дали да се прилагат ограничения за влизане в центъра
    discount_center_bus: float = 0.5  # Отстъпка за CENTER_BUS в център зоната (намалява разходите с 90%)
    
    # Параметри за градски трафик (задръствания в София)
    city_center_coords: Tuple[float, float] = (42.6977, 23.3219)  # Център на София (площад Независимост)
    city_traffic_radius_km: float = 10.0  # Радиус на градската зона с трафик (км)
    city_traffic_duration_multiplier: float = 1.6 # Множител за време в града (1.35 = +35% заради трафик)
    enable_city_traffic_adjustment: bool = True  # Дали да се прилага корекция за градски трафик

@dataclass
class RoutingConfig:
    """Конфигурация за избор на routing engine."""
    engine: RoutingEngine = RoutingEngine.OSRM # Кой routing engine да се използва: OSRM или VALHALLA
    # Ако е VALHALLA и enable_time_dependent е True, ще се използва time-dependent routing
    enable_time_dependent: bool = True  # Дали да се използва time-dependent routing (само за Valhalla)
    departure_time: str = "08:00"  # Час на тръгване (HH:MM) за time-dependent routing


@dataclass
class ValhallaConfig:
    """Конфигурации за връзка с Valhalla сървър."""
    base_url: str = "http://localhost:8002"  # Адрес на Valhalla сървъра
    costing: str = "auto"  # Профил: "auto", "truck", "bicycle", "pedestrian"
    timeout_seconds: int = 60  # Максимално време за изчакване
    retry_attempts: int = 3  # Брой опити при неуспешна заявка
    retry_delay_seconds: int = 1  # Време за изчакване между опитите
    use_cache: bool = False  # Дали да се кешират резултатите
    cache_expiry_hours: int = 24  # Време за валидност на кеша
    
    # Time-dependent routing настройки
    date_time_type: int = 1  # 0=current, 1=depart_at, 2=arrive_by
    
    # Truck-specific настройки (ако costing="truck")
    truck_height: float = 3.5  # Височина в метри
    truck_width: float = 2.5   # Ширина в метри
    truck_weight: float = 10.0  # Тегло в тонове


@dataclass
class OSRMConfig:
    """Конфигурации за връзка с OSRM (Open Source Routing Machine) сървър за изчисляване на разстояния и времена."""
    base_url: str = "http://localhost:5000"  # Адрес на локално инсталиран OSRM сървър.
    profile: str = "driving"  # Профил за маршрутизация. Възможни: "driving", "walking", "cycling".
    chunk_size: int = 80  # Брой локации, които се изпращат в една заявка към OSRM. По-голям chunk = по-малко заявки, но повече памет.
    timeout_seconds: int = 45  # Максимално време за изчакване на отговор от OSRM сървъра.
    retry_attempts: int = 3    # Брой опити при неуспешна OSRM заявка.
    retry_delay_seconds: int = 1 # Време за изчакване между неуспешните опити.
    average_speed_kmh: float = 40.0 # Резервна средна скорост, ако OSRM не върне време за пътуване.
    use_cache: bool = False # Дали да се кешират резултатите от OSRM, за да се избегнат повторни заявки.
    cache_expiry_hours: int = 24 # Време, след което кешът се счита за невалиден.
    
    # Настройки за резервен (fallback) OSRM сървър
    fallback_to_public: bool = True  # Ако локалният сървър не отговаря, да се използва ли публичният.
    public_osrm_url: str = "http://router.project-osrm.org"  # Адрес на публичния OSRM сървър.
    
    # Настройки за оптимизация на OSRM заявките
    max_locations_for_osrm: int = 50 # Максимален брой локации, за които се прави реална заявка. Над този брой се използват приблизителни изчисления.
    enable_smart_chunking: bool = True # Интелигентно разделяне на заявките на части за по-голяма ефективност.


@dataclass
class InputConfig:
    """Конфигурации за обработка на входните данни от Excel файл."""
    excel_file_path: str = _abs_path("data/input.xlsx") # Път до входния Excel файл.
    gps_column: str = "GPS"         # Име на колоната с GPS координатите на клиентите.
    client_id_column: str = "IdCust"      # Име на колоната с ID на клиента.
    client_name_column: str = "Клиент" # Име на колоната с името на клиента.
    volume_column: str = "Брой стекове"           # Име на колоната с обема/теглото на заявката.
    sheet_name: Optional[str] = None  # Име на листа в Excel файла. Ако е None, използва се първият наличен.
    encoding: str = "utf-8"           # Кодировка на файла.


@dataclass
class WarehouseConfig:
    """Конфигурации за логиката на склада, който обработва част от заявките предварително."""
    enable_warehouse: bool = True      # Дали да се използва логиката за предварително отделяне на заявки за склада
    sort_by_volume: bool = True        # Дали заявките да се сортират по обем (от най-малък към най-голям) преди обработка
    sort_by_distance: bool = True      # Дали да се сортират по разстояние за клиенти с еднакъв обем (от най-далечен към най-близък)
    check_max_bus_capacity: bool = True # Проверява дали клиент надвишава капацитета на най-големия наличен бус
    max_bus_customer_volume: float = 120 # Максимален обем на клиент (стекове), над който се изпращат към склада, а не към бусовете
    capacity_toleranse: float = 0.90 # Толеранс на капацитета на превозните средства.
@dataclass
class CVRPConfig:
    """
    Конфигурация за CVRP (Capacitated Vehicle Routing Problem) решателя.
    Тези настройки контролират всеки аспект на процеса на оптимизация.
    Поддържа OR-Tools и PyVRP солвъри.
    """
    solver_type: str = "pyvrp"  # Тип солвър: "or_tools" или "pyvrp"
    algorithm: str = "or_tools"  # Основен алгоритъм. В момента се поддържа само "or_tools".

    # --- Основни параметри на търсенето ---
    time_limit_seconds: int = 30
    # Описание: Максимално време в секунди, което solver-ът има за намиране на решение.

    first_solution_strategy: str = "CHRISTOFIDES"
    # Описание: Стратегия за намиране на първоначално решение. SAVINGS е по-бърза от AUTOMATIC.
    # Стойности: "AUTOMATIC", "PATH_CHEAPEST_ARC", "SAVINGS", "SWEEP", и др.

    local_search_metaheuristic: str = "GUIDED_LOCAL_SEARCH"
    # Описание: SIMULATED_ANNEALING е по-добра за избягване на локални оптимуми.
    # Стойности: "AUTOMATIC", "GUIDED_LOCAL_SEARCH", "SIMULATED_ANNEALING", "TABU_SEARCH".
    
    lns_time_limit_seconds: float = 15
    # Описание: Много кратък микро-лимит принуждава solver-а да се движи бързо.
    # Употреба: 0.1 секунди е достатъчно за една стъпка, но не позволява зависване.
    
    # LNS neighborhood параметри
    lns_num_nodes: int = 120
    # Описание: Брой близки възли които LNS разглежда в една стъпка.
    
    lns_num_arcs: int = 110
    # Описание: Брой скъпи дъги които LNS разглежда в една стъпка.
    
    use_full_propagation: bool = True

    log_search: bool = True
    # Описание: Дали OR-Tools да извежда детайлен лог на процеса на търсене.

    search_lambda_coefficient: float = 0.8
    # Опция за пропускане на клиенти

    allow_customer_skipping: bool = True
    # Описание: Дали solver-ът може да пропуска клиенти.
    # False = ВСИЧКИ клиенти трябва да бъдат обслужени (НЯМА пропускане).
    # True = Solver-ът може да пропусне клиенти ако е необходимо.

    distance_penalty_disjunction: int = 45000
    # Описание: Фиксирано наказание за пропускане на клиент.
    # По-голяма стойност = по-трудно пропускане на клиенти (по-малка вероятност клиент да бъде пропуснат).

    # --- Настройки за паралелна обработка ---
    enable_parallel_solving: bool = False  # Keep disabled for PyVRP stability
    # Описание: Дали да се стартират няколко solver-а паралелно с различни стратегии.
    
    # --- Режим на solver-а ---
    use_simple_solver: bool = False
    # Описание: Дали да се използва опростеният solver, който точно следва OR-Tools примера.
    # True = само capacity constraints, False = всички ограничения (distance, time, stops)
    
    # --- Финален реконфигурация на маршрутите ---
    enable_final_depot_reconfiguration: bool = True
    # Описание: Дали след като OR-Tools намери решение, да се реконфигурират всички маршрути
    # да започват от депото, независимо от оригиналните стартови точки.
    # True = всички маршрути започват от депото, False = запазват оригиналните стартови точки.
    
    # --- Настройки за стартово време ---
    enable_start_time_tracking: bool = True
    # Описание: Дали да се проследява стартово време за всеки маршрут.
    # True = показва времето с натрупване от стартовото време, False = показва само времето на маршрута.
    
    global_start_time_minutes: int = 480
    # Описание: Глобално стартово време в минути от 00:00 (8:00 = 480 минути).
    # Използва се ако не е зададено стартово време за конкретен тип превозно средство.
    
    num_workers: int = -1
    # Описание: Брой паралелни процеси. -1 означава да се използват всички ядра без едно.

    parallel_first_solution_strategies: List[str] = field(default_factory=lambda: [
        "PARALLEL_CHEAPEST_INSERTION",
        "SAVINGS",
        "PARALLEL_CHEAPEST_INSERTION",
        "PATH_CHEAPEST_ARC",
        "SAVINGS",
        "PARALLEL_CHEAPEST_INSERTION",
        "PARALLEL_CHEAPEST_INSERTION"
    ])
    # Описание: Списък с "First Solution" стратегии, които да се състезават в паралелен режим.

    parallel_local_search_metaheuristics: List[str] = field(default_factory=lambda: [
        "GUIDED_LOCAL_SEARCH",
        "GUIDED_LOCAL_SEARCH",
        "GUIDED_LOCAL_SEARCH",
        "GUIDED_LOCAL_SEARCH",
        "SIMULATED_ANNEALING",
        "GUIDED_LOCAL_SEARCH",
        "GUIDED_LOCAL_SEARCH"
    ])
    # Описание: Списък с "Local Search" метаевристики, които да се състезават в паралелен режим.


@dataclass
class OutputConfig:
    """Конфигурации за генериране на изходни файлове (карти, Excel отчети, графики)."""
    # Интерактивна карта
    enable_interactive_map: bool = True # Дали да се генерира HTML файл с интерактивна карта на маршрутите.
    map_output_file: str = _abs_path("output/interactive_map.html") # Път и име на файла за картата.
    map_zoom_level: int = 12 # Начално приближение на картата.
    show_route_colors: bool = True # Дали различните маршрути да се оцветяват в различни цветове.
    show_vehicle_info: bool = True # Дали да се показва информация за превозното средство при клик на маршрут.
    
    # Excel файлове
    excel_output_dir: str = _abs_path("output/excel") # Директория за запис на Excel отчетите.
    warehouse_excel_file: str = "warehouse_orders.xlsx" # Име на файла с необслужените клиенти (за склада).
    routes_excel_file: str = "vehicle_routes.xlsx" # Име на файла с детайли за всеки маршрут.
    efficiency_excel_file: str = "efficiency_report.xlsx" # Име на файла с отчет за ефективността.
    
    # Графики и анализи
    enable_charts: bool = True # Дали да се генерират PNG файлове с графики.
    charts_output_dir: str = _abs_path("output/charts") # Директория за запис на графиките.
    efficiency_chart_file: str = "efficiency_analysis.png" # Графика с анализ на ефективността.
    route_comparison_file: str = "route_comparison.png" # Графика, сравняваща маршрутите.
    volume_distribution_file: str = "volume_distribution.png" # Графика с разпределението на обемите.
    
    # Детайли в изходните файлове
    include_detailed_info: bool = True # Дали да се включва допълнителна информация в отчетите.
    show_km_info: bool = True # Дали да се показва информация за километри.
    show_time_info: bool = True # Дали да се показва информация за време.
    show_volume_info: bool = True # Дали да се показва информация за обем.


@dataclass
class LoggingConfig:
    """Конфигурации за системата за логиране."""
    log_level: str = "INFO"  # Ниво на логиране: DEBUG, INFO, WARNING, ERROR, CRITICAL.
    log_file: str = _abs_path("logs/cvrp.log") # Път до лог файла.
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s" # Формат на съобщенията в лога.
    enable_console_logging: bool = True # Дали да се печатат логове в конзолата.
    enable_file_logging: bool = True # Дали да се записват логове във файл.
    max_log_size_mb: int = 10 # Максимален размер на лог файла в мегабайти, преди да се архивира.
    backup_count: int = 5 # Брой архивирани лог файлове, които да се пазят.


@dataclass
class CacheConfig:
    """Конфигурации за системата за кеширане."""
    enable_cache: bool = False # Дали кеширането е активно.
    cache_dir: str = _abs_path("cache") # Директория, в която се съхраняват кеш файловете.
    osrm_cache_file: str = "osrm_matrix_cache.json" # Файл за кеширане на OSRM матриците с разстояния.
    routes_cache_file: str = "routes_cache.json" # Файл за кеширане на готови решения.
    cache_expiry_hours: int = 24 # Време в часове, след което кешът се счита за невалиден.
    max_cache_size_mb: int = 100 # Максимален размер на кеш директорията.


@dataclass
class PerformanceConfig:
    """Конфигурации, свързани с производителността на приложението."""
    max_concurrent_requests: int = 10 # Максимален брой едновременни заявки (напр. към OSRM).
    chunk_processing_delay: float = 0.1  # Време за изчакване в секунди между обработката на отделни "chunks".
    memory_limit_mb: int = 2048 # Ограничение на паметта (информативно, не се налага стриктно).
    enable_multiprocessing: bool = True # Дали да се използва multiprocessing за ускоряване на изчисления.
    max_workers: int = 12 # Максимален брой паралелни процеси/нишки.


@dataclass
class MainConfig:
    """Главна конфигурация, която обединява всички останали модулни конфигурации."""
    # Модулни конфигурации
    locations: LocationConfig = field(default_factory=LocationConfig)
    vehicles: Optional[List[VehicleConfig]] = None
    routing: RoutingConfig = field(default_factory=RoutingConfig)  # Избор на routing engine
    osrm: OSRMConfig = field(default_factory=OSRMConfig)
    valhalla: ValhallaConfig = field(default_factory=ValhallaConfig)  # Valhalla конфигурация
    input: InputConfig = field(default_factory=InputConfig)
    warehouse: WarehouseConfig = field(default_factory=WarehouseConfig)
    cvrp: CVRPConfig = field(default_factory=CVRPConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # Глобални настройки на приложението
    debug_mode: bool = True # Включва/изключва дебъг режим с по-детайлни логове.
    verbose: bool = True # Дали да се извежда по-подробна информация в конзолата.
    dry_run: bool = False  # "Сухо" изпълнение - изпълнява се цялата логика, но без реални операции като запис на файлове.
    
    def __post_init__(self):
        """Инициализира default конфигурации за превозните средства, ако не са зададени."""
        if self.vehicles is None:
            self.vehicles = self._create_default_vehicles()
    
    def _create_default_vehicles(self) -> List[VehicleConfig]:
        """Създава стандартен set от превозни средства, ако не е дефиниран друг."""
        # --- Примерни GPS координати за различни депа ---
        depot_main = self.locations.depot_location
        depot_center = self.locations.center_location
        depot_vratza = self.locations.vratza_depot_location

        return [
            # 1. Вътрешни бусове - 4 бр, 360 ст.
            # Ограниченията за разстояние и брой клиенти са премахнати, за да се разчита
            # само на твърдите, реални лимити - ВРЕМЕ и ОБЕМ.
            VehicleConfig(
                vehicle_type=VehicleType.INTERNAL_BUS,
                capacity=385,
                count=7,
                max_distance_km=None, # Премахнато
                max_time_hours=8,
                service_time_minutes=7,
                enabled=True,
                max_customers_per_route=None,
                start_location=depot_main,  # Тръгва от центъра
                start_time_minutes=480,  # 8:00
                tsp_depot_location=depot_main  # TSP оптимизация от главното депо
            ),
            # 2. Център бус - 1 бр.
            VehicleConfig(
                vehicle_type=VehicleType.CENTER_BUS,
                capacity=320,
                count=1,
                max_distance_km=None, # Премахнато
                max_time_hours=8,
                service_time_minutes=9,
                enabled=True,
                max_customers_per_route=None,
                start_location=depot_main,  # Тръгва от център депото
                start_time_minutes=510,  # 8:30
                tsp_depot_location=depot_main  # TSP оптимизация от център депото
            ),
            # 3. Външни бусове - 3 бр, 360 ст.
            VehicleConfig(
                vehicle_type=VehicleType.EXTERNAL_BUS,
                capacity=385,
                count=3,
                max_distance_km=None, # Премахнато
                max_time_hours=20,   
                service_time_minutes=7, # КОРИГИРАНО
                enabled=False,
                max_customers_per_route=None,
                start_location=depot_center,  # Тръгва от главното депо
                start_time_minutes=450,  # 7:30
                tsp_depot_location=depot_main  # TSP оптимизация от главното депо
            ),
            # 4. Специални бусове - 
            VehicleConfig(
                vehicle_type=VehicleType.SPECIAL_BUS,
                capacity=300,
                count=2,
                max_distance_km=None,
                max_time_hours=8,
                service_time_minutes=6,
                enabled=False,  # Изключени по подразбиране
                max_customers_per_route=None,
                start_location=depot_center,  # Тръгва от главното депо
                start_time_minutes=480,  # 8:00
                tsp_depot_location=depot_main  # TSP оптимизация от главното депо
            ),
            # 5. Враца бусове
            VehicleConfig(
                vehicle_type=VehicleType.VRATZA_BUS,
                capacity=385,
                count=3,
                max_distance_km=None,
                max_time_hours=8,   
                service_time_minutes=7,
                enabled=False,  # ТЕСТ: Временно активиран
                max_customers_per_route=40,
                start_location=depot_vratza,  # Тръгва от депото във Враца
                start_time_minutes=480,  # 8:00
                tsp_depot_location=depot_vratza  # TSP оптимизация от Враца депо
            )
        ]


class ConfigManager:
    """Мениджър за зареждане и записване на конфигурации"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = _abs_path(config_file)
        self.config = MainConfig()
    
    def load_config(self, config_dict: Optional[Dict[str, Any]] = None) -> MainConfig:
        """Зарежда конфигурация от файл или речник"""
        if config_dict:
            self._update_config_from_dict(config_dict)
        elif os.path.exists(self.config_file):
            self._load_from_file()
        
        # Създаване на необходими директории
        self._create_directories()
        
        return self.config
    
    def _load_from_file(self) -> None:
        """Зарежда конфигурация от JSON файл"""
        import json
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                self._update_config_from_dict(config_data)
        except Exception as e:
            print(f"Грешка при зареждане на конфигурация: {e}")
    
    def _update_config_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """Обновява конфигурацията от речник"""
        for section, values in config_dict.items():
            if hasattr(self.config, section) and isinstance(values, dict):
                section_config = getattr(self.config, section)
                for key, value in values.items():
                    if hasattr(section_config, key):
                        setattr(section_config, key, value)
    
    def save_config(self, config: Optional[MainConfig] = None) -> None:
        """Записва конфигурацията във файл"""
        if config:
            self.config = config
        
        config_dict = self._config_to_dict()
        
        import json
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
    
    def _config_to_dict(self) -> Dict[str, Any]:
        """Преобразува конфигурацията в речник"""
        result = {}
        
        for attr_name in dir(self.config):
            if attr_name.startswith('_'):
                continue
                
            attr_value = getattr(self.config, attr_name)
            
            if hasattr(attr_value, '__dict__'):
                # Dataclass обект
                result[attr_name] = {
                    k: v for k, v in attr_value.__dict__.items() 
                    if not k.startswith('_')
                }
            elif isinstance(attr_value, list):
                # Списък с dataclass обекти
                result[attr_name] = [
                    {k: v for k, v in item.__dict__.items() if not k.startswith('_')}
                    if hasattr(item, '__dict__') else item
                    for item in attr_value
                ]
            elif not callable(attr_value):
                result[attr_name] = attr_value
        
        return result
    
    def _create_directories(self) -> None:
        """Създава необходимите директории"""
        directories = [
            os.path.dirname(self.config.input.excel_file_path),
            self.config.output.excel_output_dir,
            self.config.output.charts_output_dir,
            os.path.dirname(self.config.output.map_output_file),
            os.path.dirname(self.config.logging.log_file),
            self.config.cache.cache_dir
        ]
        
        for directory in directories:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
    
    def get_config(self) -> MainConfig:
        """Връща текущата конфигурация"""
        return self.config
    
    def get_enabled_vehicles(self) -> List[VehicleConfig]:
        """Връща само включените превозни средства"""
        if self.config.vehicles is None:
            return []
        return [v for v in self.config.vehicles if v.enabled]
    
    def get_total_vehicle_capacity(self) -> int:
        """Изчислява общия капацитет на всички включени превозни средства"""
        return sum(v.capacity * v.count for v in self.get_enabled_vehicles())
    
    def update_vehicle_status(self, vehicle_type: VehicleType, enabled: bool) -> None:
        """Включва/изключва определен тип превозно средство"""
        if self.config.vehicles is None:
            return
        for vehicle in self.config.vehicles:
            if vehicle.vehicle_type == vehicle_type:
                vehicle.enabled = enabled


# Глобална инстанция на конфигурацията
config_manager = ConfigManager()

# Функции за лесен достъп до конфигурациите
def get_config() -> MainConfig:
    """Връща главната конфигурация"""
    return config_manager.get_config()

def get_osrm_config() -> OSRMConfig:
    """Връща OSRM конфигурацията"""
    return config_manager.get_config().osrm

def get_vehicle_configs() -> List[VehicleConfig]:
    """Връща конфигурациите на превозните средства"""
    return config_manager.get_enabled_vehicles()

def get_locations() -> LocationConfig:
    """Връща GPS локациите"""
    return config_manager.get_config().locations 