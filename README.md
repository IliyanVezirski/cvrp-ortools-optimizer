# 🚛 CVRP Optimizer - Напреднал Оптимизатор за Маршрути

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![OR-Tools](https://img.shields.io/badge/OR--Tools-9.7+-green.svg)](https://developers.google.com/optimization)
[![PyVRP](https://img.shields.io/badge/PyVRP-0.5+-purple.svg)](https://pyvrp.org)
[![OSRM](https://img.shields.io/badge/OSRM-5.27+-orange.svg)](https://github.com/Project-OSRM/osrm-backend)
[![Valhalla](https://img.shields.io/badge/Valhalla-3.x-teal.svg)](https://github.com/valhalla/valhalla)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**CVRP Optimizer** е професионална софтуерна система за решаване на **Capacitated Vehicle Routing Problem (CVRP)** с интеграция на реални географски данни, математическа оптимизация и интелигентни бизнес правила. Системата поддържа **два solver-а** — **Google OR-Tools** и **PyVRP** (Iterated Local Search) — и **два routing engine-а** — **OSRM** (статичен routing) и **Valhalla** (time-dependent routing с реален трафик).

---

## 📋 Съдържание

- [🏗️ Архитектура на системата](#️-архитектура-на-системата)
- [⚡ Ключови функционалности](#-ключови-функционалности)
- [🚀 Технологичен стек](#-технологичен-стек)
- [🔧 Инсталация и настройка](#-инсталация-и-настройка)
- [📊 Подробен анализ на модулите](#-подробен-анализ-на-модулите)
- [🔬 Алгоритми и стратегии](#-алгоритми-и-стратегии)
- [🗺️ Интерактивна визуализация](#️-интерактивна-визуализация)
- [⚙️ Конфигурационна система](#️-конфигурационна-система)
- [🏁 Стартиране и използване](#-стартиране-и-използване)
- [📈 Performance и мащабиране](#-performance-и-мащабиране)
- [🔍 Troubleshooting](#-troubleshooting)
- [🔄 Dual Solver система](#-dual-solver-система)
- [🗺️ Dual Routing Engine](#️-dual-routing-engine)
- [🚦 Градски трафик симулация](#-градски-трафик-симулация)
- [📦 Компилиране в EXE](#-компилиране-в-exe)

---

## 🏗️ Архитектура на системата

CVRP Optimizer е изграден като модулна система с ясно разделение на отговорностите:

```
┌─────────────────────────────────────────────────────────────┐
│                    CVRP OPTIMIZER                           │
├─────────────────────────────────────────────────────────────┤
│                     main.py                                 │
│                 (Оркестратор)                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
┌─────────┐    ┌─────────────┐    ┌──────────────┐
│ INPUT   │    │   SOLVER    │    │   OUTPUT     │
│ LAYER   │    │   LAYER     │    │   LAYER      │
└─────────┘    └─────────────┘    └──────────────┘
    │               │                    │
    ▼               ▼                    ▼
┌─────────┐    ┌─────────────┐    ┌──────────────┐
│ input_  │    │ cvrp_       │    │ output_      │
│ handler │    │ solver      │    │ handler      │
└─────────┘    │ (OR-Tools)  │    └──────────────┘
    │          └─────────────┘         │
┌─────────┐    ┌─────────────┐    ┌──────────────┐
│ GPS     │    │ pyvrp_      │    │ Interactive  │
│ Parser  │    │ solver      │    │ Map          │
└─────────┘    │ (PyVRP)     │    │(OSRM/Valhalla│
    │          └─────────────┘    │ geometry)    │
┌─────────┐    ┌─────────────┐    └──────────────┘
│ Data    │    │ warehouse_  │    ┌──────────────┐
│ Validation   │ manager     │    │ Excel        │
└─────────┘    └─────────────┘    │ Reports      │
                    │             └──────────────┘
    ┌───────────────┼───────────────┐
    ▼                               ▼
┌─────────────┐            ┌──────────────┐
│ osrm_       │            │ valhalla_    │
│ client      │            │ client       │
│ (Static)    │            │ (Traffic)    │
└─────────────┘            └──────────────┘
```

### Централизирана конфигурационна система

```python
# config.py - Централен конфигурационен файл
MainConfig
├── vehicles: List[VehicleConfig]     # Превозни средства
├── locations: LocationConfig         # GPS локации + трафик настройки
├── routing: RoutingConfig            # Избор на routing engine (OSRM/Valhalla)
├── osrm: OSRMConfig                 # OSRM интеграция
├── valhalla: ValhallaConfig         # Valhalla интеграция (NEW)
├── warehouse: WarehouseConfig       # Складова логика
├── cvrp: CVRPConfig                 # Solver настройки (OR-Tools/PyVRP)
├── input: InputConfig               # Входни данни
├── output: OutputConfig             # Изходни файлове
├── logging: LoggingConfig           # Логиране
├── cache: CacheConfig               # Кеширане
└── performance: PerformanceConfig   # Performance настройки
```

---

## ⚡ Ключови функционалности

### 🚛 Интелигентно управление на флота

**Поддържани типове превозни средства:**
- **INTERNAL_BUS**: 7 бр. × 385 стекове, 7 мин. service time, 8ч. работно време
- **CENTER_BUS**: 1 бр. × 320 стекове, 9 мин. service time, 8ч. работно време (старт 8:30)
- **EXTERNAL_BUS**: 3 бр. × 385 стекове, 7 мин. service time (изключени по подразбиране)
- **SPECIAL_BUS**: 2 бр. × 300 стекове, 6 мин. service time (изключени по подразбиране)
- **VRATZA_BUS**: 3 бр. × 385 стекове, 7 мин. service time (изключени по подразбиране), макс. 40 клиента/маршрут

**Advance vehicle constraints:**
```python
@dataclass
class VehicleConfig:
    vehicle_type: VehicleType
    capacity: int                                    # Капацитет в стекове
    count: int                                       # Брой превозни средства
    max_distance_km: Optional[int] = None           # Максимален пробег
    max_time_hours: int = 20                        # Максимално работно време
    service_time_minutes: int = 15                  # Време за обслужване
    enabled: bool = True                            # Активен/неактивен
    start_location: Optional[Tuple[float, float]]   # Начална точка (депо)
    max_customers_per_route: Optional[int] = None   # Максимален брой клиенти
    start_time_minutes: int = 480                   # Стартово време (8:00)
    tsp_depot_location: Optional[Tuple[float, float]] = None  # TSP депо
```

### 🎯 Център зона приоритизация

**Intelligent center zone logic:**
- **Радиус**: 1.7 км от центъра на града
- **CENTER_BUS приоритет**: 50% отстъпка за център зоната
- **Глоби за други автобуси**: 40,000 единици за влизане в центъра  
- **Обратна глоба**: CENTER_BUS плаща глоба за клиенти ИЗВЪН центъра
- **Автоматично разпознаване**: GPS-базирано определяне на център зоната

```python
# Център зона логика
if customer_distance_to_center <= 1.7:  # км
    if vehicle_type == VehicleType.CENTER_BUS:
        cost = base_cost * 0.50  # 50% отстъпка
    else:
        cost = base_cost + 40000  # Глоба за влизане
else:
    if vehicle_type == VehicleType.CENTER_BUS:
        cost = base_cost + 40000  # CENTER_BUS не трябва да излиза от центъра
```

### 🧠 TSP Оптимизация с Personalized Депа

**Vehicle-specific TSP optimization:**
- **INTERNAL_BUS**: TSP от главното депо (София)
- **CENTER_BUS**: TSP от главното депо (София)
- **EXTERNAL_BUS**: TSP от главното депо (София)
- **SPECIAL_BUS**: TSP от главното депо (София)
- **VRATZA_BUS**: TSP от Враца депо

```python
def _optimize_route_from_depot(self, customers, depot_location, vehicle_config):
    """
    OR-Tools TSP решател за оптимизация от персонализирано депо
    """
    # Използва vehicle_config.tsp_depot_location
    tsp_depot = vehicle_config.tsp_depot_location or vehicle_config.start_location
    
    # Създава TSP проблем с OR-Tools
    # Минимизира разстоянието без ограничения
    # Връща оптимизиран ред на клиентите
```

### 🏭 Интелигентна складова логика

**Двуетапна стратегия за разпределение:**

1. **Филтриране по размер:**
```python
if customer.volume > max_single_bus_capacity:
    warehouse_customers.append(customer)  # Твърде голям за всички бусове
elif customer.volume > config.max_bus_customer_volume:  # 120 стекове
    warehouse_customers.append(customer)  # Над лимита за обслужване
```

2. **Интелигентно сортиране:**
```python
sorted_customers = sorted(customers, key=lambda c: (
    c.volume,  # Първо по обем (малък → голям)
    -calculate_distance_km(c.coordinates, depot_location)  # После по разстояние (далечен → близо)
))
```

### ⚡ Паралелна обработка

**Multi-strategy concurrent solving (OR-Tools mode):**

| Работник | First Solution Strategy | Local Search Metaheuristic |
|----------|-------------------------|----------------------------|
| 1 | PARALLEL_CHEAPEST_INSERTION | GUIDED_LOCAL_SEARCH |
| 2 | SAVINGS | GUIDED_LOCAL_SEARCH |
| 3 | PARALLEL_CHEAPEST_INSERTION | GUIDED_LOCAL_SEARCH |
| 4 | PATH_CHEAPEST_ARC | GUIDED_LOCAL_SEARCH |
| 5 | SAVINGS | SIMULATED_ANNEALING |
| 6 | PARALLEL_CHEAPEST_INSERTION | GUIDED_LOCAL_SEARCH |
| 7 | PARALLEL_CHEAPEST_INSERTION | GUIDED_LOCAL_SEARCH |

> **Забележка:** Паралелната обработка е изключена по подразбиране (`enable_parallel_solving: False`) за стабилност с PyVRP solver. Активира се при `solver_type: "or_tools"`.

**Automatic winner selection:**
```python
# Избира най-доброто решение по fitness score (най-малко разстояние)
best_solution = min(valid_solutions, key=lambda s: s.fitness_score)
```

---

## 🚀 Технологичен стек

### Core Dependencies

```python
# Mathematical Optimization
ortools>=9.7.2996          # Google OR-Tools optimization suite
pyvrp>=0.5.0,<0.6.0       # PyVRP - Iterated Local Search VRP solver (NEW)
scipy>=1.9.0                # Scientific computing

# Data Processing & Analysis  
pandas>=1.5.0               # DataFrame operations
numpy>=1.21.0               # Numerical arrays
openpyxl>=3.0.9             # Excel file support

# Geospatial & Routing
requests>=2.28.0            # HTTP client for OSRM/Valhalla API
urllib3>=1.26.0             # Low-level HTTP library

# Visualization & UI
folium>=0.14.0              # Interactive maps with Leaflet.js

# User Experience
tqdm>=4.65.0                # Progress bars
pyyaml>=6.0                 # YAML configuration support
```

### Dual Solver система

**OR-Tools Solver** (класически):
- **Clarke-Wright Savings Algorithm**
- **Christofides Algorithm** 
- **Guided Local Search (GLS)**
- **Simulated Annealing**
- **Tabu Search**
- **Large Neighborhood Search (LNS)**

**PyVRP Solver** (алтернативен):
- **Iterated Local Search (ILS)** — специализиран за VRP
- **Двупрофилна система**: CENTER_BUS профил + OTHER_BUS профил
- **Prize-based customer dropping** — клиенти с по-голям обем са по-трудни за пропускане
- **Двумерен капацитет**: [обем, макс_клиенти] едновременно
- **Автоматично seed** за възпроизводими резултати

### Dual Routing Engine

**OSRM Integration** (статичен routing):
- **Table Service**: Distance matrices за batch processing
- **Route Service**: Detailed routing geometries за визуализация
- **Fallback**: Public OSRM → Haversine approximation

**Valhalla Integration** (time-dependent routing) **(NEW)**:
- **Sources-to-targets API**: Distance matrices с рефлектиране на трафик
- **Route API**: Маршрутна геометрия с encoded polyline
- **Time-dependent routing**: Реални времена на пътуване по час на тръгване
- **Truck routing**: Профил за камиони (височина, ширина, тегло)
- **Costing profiles**: auto, truck, bicycle, pedestrian
- **Batch processing**: Автоматично разделяне за >50 локации

---

## 🔧 Инсталация и настройка

### Системни изисквания

- **Python**: 3.8+ (тестван до 3.11)
- **Memory**: 2GB+ RAM (4GB+ за >200 клиента)
- **Storage**: 1GB за OSRM data и cache
- **Network**: Internet за OSRM fallback (опционално)

### Бърза инсталация

```bash
# 1. Клониране на репозиторията
git clone <repository-url>
cd cvrp-optimizer

# 2. Създаване на виртуална среда
python -m venv cvrp_env
source cvrp_env/bin/activate  # Linux/Mac
# cvrp_env\Scripts\activate   # Windows

# 3. Инсталиране на зависимости
pip install -r requirements.txt

# 4. Създаване на директории
mkdir -p data output/excel output/charts logs cache

# 5. Проверка на инсталацията
python -c "import ortools; print('OR-Tools:', ortools.__version__)"
```

### OSRM сървър (опция 1 — статичен routing)

**Docker setup за България:**
```bash
# 1. Download Bulgarian OSM data
wget https://download.geofabrik.de/europe/bulgaria-latest.osm.pbf

# 2. OSRM preprocessing
docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-extract -p /opt/car.lua /data/bulgaria-latest.osm.pbf
docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-partition /data/bulgaria-latest.osrm
docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-customize /data/bulgaria-latest.osrm

# 3. Start OSRM server (port 5000)
docker run -t -i -p 5000:5000 -v "${PWD}:/data" osrm/osrm-backend osrm-routed --algorithm mld /data/bulgaria-latest.osrm
```

### Valhalla сървър (опция 2 — time-dependent routing) **(NEW)**

**Docker setup за България:**
```bash
# 1. Създайте директория за Valhalla данни
mkdir valhalla-data && cd valhalla-data

# 2. Download Bulgarian OSM data
wget https://download.geofabrik.de/europe/bulgaria-latest.osm.pbf

# 3. Start Valhalla с Docker (автоматично preprocessing)
docker run -dt --name valhalla \
  -p 8002:8002 \
  -v "${PWD}:/custom_files" \
  -e tile_urls=https://download.geofabrik.de/europe/bulgaria-latest.osm.pbf \
  ghcr.io/gis-ops/docker-valhalla/valhalla:latest

# 4. Проверка на Valhalla
curl http://localhost:8002/status
```

**Valhalla предимства пред OSRM:**
- ✅ Time-dependent routing (час на тръгване влияе на времената)
- ✅ Truck routing профил (височина, ширина, тегло)
- ✅ По-реалистични времена с трафик
- ✅ Множество costing профили (auto, truck, bicycle, pedestrian)

---

## 📊 Подробен анализ на модулите

### 📥 input_handler.py - Входни данни

**Функционалности:**
- **Excel парсиране**: .xlsx, .xls файлове
- **GPS координати извличане**: Множество формати
- **Data validation**: Проверка на валидност
- **Duplicate detection**: Намиране на дублиращи се записи

```python
class GPSParser:
    @staticmethod
    def parse_gps_string(gps_string: str) -> Optional[Tuple[float, float]]:
        """
        Поддържани формати:
        - "42.123456, 23.567890"
        - "42.123456,23.567890" 
        - "42.123456 23.567890"
        - "N42.123456 E23.567890"
        """
```

**Data structures:**
```python
@dataclass
class Customer:
    id: str                                      # Уникален идентификатор
    name: str                                    # Име на клиента
    coordinates: Optional[Tuple[float, float]]   # GPS координати
    volume: float                                # Обем на заявката
    original_gps_data: str                       # Оригинални GPS данни
```

### 🏭 warehouse_manager.py - Складова логика

**Ключови функции:**
- **Capacity calculation**: Изчисляване на общ капацитет
- **Smart sorting**: Двумерно сортиране (обем + разстояние)
- **Center zone detection**: GPS-базирано разпознаване
- **Allocation optimization**: Оптимално разпределение

```python
def _sort_customers(self, customers: List[Customer]) -> List[Customer]:
    """
    Dual-criteria sorting:
    1. Volume (ascending): от малък към голям обем
    2. Distance (descending): от далечни към близо клиенти
    """
    return sorted(customers, key=lambda c: (
        c.volume,
        -calculate_distance_km(c.coordinates, self.location_config.depot_location)
    ))
```

**Advanced allocation strategy:**
```python
def _allocate_with_warehouse(self, sorted_customers, total_capacity):
    """
    Three-tier allocation:
    1. Size filtering: > max_single_bus_capacity → warehouse
    2. Policy filtering: > max_bus_customer_volume → warehouse  
    3. Capacity filling: Fill buses to 100% capacity
    """
```

### 🧠 cvrp_solver.py - OR-Tools решаващ модул

**Архитектура на solver-а:**

```python
class ORToolsSolver:
    """
    OR-Tools CVRP решател с четири активни dimensions:
    - Capacity: Обемни ограничения
    - Distance: Разстоянни ограничения  
    - Stops: Ограничения за брой спирки
    - Time: Времеви ограничения (vehicle-specific service times)
    """
    
    def solve(self) -> CVRPSolution:
        """
        Main solving pipeline:
        1. Create data model
        2. Setup routing model  
        3. Add constraints (4 dimensions)
        4. Apply center zone logic
        5. Solve with search parameters (LNS настройки)
        6. Extract and validate solution
        7. TSP optimization (optional)
        """
```

**LNS (Large Neighborhood Search) настройки:**
```python
lns_time_limit_seconds: float = 15    # Микро-лимит за LNS стъпка
lns_num_nodes: int = 120              # Брой възли за LNS разглеждане
lns_num_arcs: int = 110               # Брой скъпи дъги за LNS разглеждане
use_full_propagation: bool = True     # Пълна пропагация на ограничения
search_lambda_coefficient: float = 0.8 # Lambda коефициент за GLS
```

### 🧬 pyvrp_solver.py - PyVRP решаващ модул **(NEW)**

**Алтернативен solver базиран на PyVRP библиотека:**

```python
class PyVRPSolver:
    """
    PyVRP CVRP решател - Iterated Local Search.
    
    Ключови разлики от OR-Tools:
    - Двупрофилна система: CENTER_BUS profile vs OTHER_BUS profile
    - Prize-based customer dropping (не penalty-based)
    - Двумерен капацитет: [обем, макс_клиенти]
    - Seed-based за възпроизводими резултати
    - Градски трафик корекция директно в edge duration
    """
    
    def solve(self) -> CVRPSolution:
        """
        PyVRP solving pipeline:
        1. Create PyVRP Model (depots, clients, profiles, edges, vehicle types)
        2. Build ProblemData
        3. Solve with MaxRuntime stop criterion
        4. Extract solution в CVRPSolution формат
        """
```

**PyVRP двупрофилна система:**
```python
# Profile 0: CENTER_BUS - отстъпка за център, глоба извън центъра
center_bus_profile = model.add_profile()

# Profile 1: OTHER_BUS - глоба за център, нормална цена извън
other_bus_profile = model.add_profile()

# Edges с различни разстояния за всеки профил:
# CENTER_BUS в центъра: distance * 0.5 (50% отстъпка)
# CENTER_BUS извън центъра: distance + 40000 (глоба)
# OTHER_BUS в центъра: distance + 40000 (глоба)
# OTHER_BUS извън центъра: distance (нормална цена)
```

**PyVRP Prize-based dropping:**
```python
# Клиенти с по-голям обем имат по-висока "награда" за обслужване
# → по-малка вероятност да бъдат пропуснати
client_prize = drop_penalty + delivery * 100  # Пропорционално на обема

model.add_client(
    delivery=[volume, 1],       # [обем, 1 спирка]
    prize=client_prize,          # Награда за обслужване
    required=not allow_dropping  # Ако dropping е забранен → required=True
)
```

**Избор между OR-Tools и PyVRP:**
```python
# config.py
solver_type: str = "pyvrp"  # "or_tools" или "pyvrp"
```

**Constraint implementation:**
```python
# 1. Capacity constraints
routing.AddDimensionWithVehicleCapacity(
    demand_callback_index, 0, vehicle_capacities, True, "Capacity"
)

# 2. Distance constraints  
routing.AddDimensionWithVehicleCapacity(
    transit_callback_index, 0, vehicle_max_distances, True, "Distance"
)

# 3. Stop count constraints
routing.AddDimensionWithVehicleCapacity(
    stop_callback_index, 0, vehicle_max_stops, True, "Stops"
)

# 4. Time constraints (vehicle-specific service times)
routing.AddDimensionWithVehicleCapacity(
    time_callback_index, 0, vehicle_max_times, False, "Time"
)
```

### 🌐 osrm_client.py - OSRM интеграция

**Multi-tier fallback system:**
```python
def get_distance_matrix(self, locations):
    """
    Intelligent chunking strategy:
    - n ≤ 30: Direct Table API
    - 30 < n ≤ 500: Batch Table API с chunking  
    - n > 500: Parallel Route API calls
    """
    
    try:
        return self._local_osrm_request(locations)
    except OSRMLocalError:
        try:
            return self._public_osrm_request(locations)
        except OSRMPublicError:
            return self._haversine_approximation(locations)
```

**Advanced caching:**
```python
class OSRMCache:
    """
    Features:
    - MD5 hashing за cache keys
    - JSON serialization
    - TTL expiration (24h default)
    - Automatic cleanup на stale entries
    - Order-independent key generation
    """
```

### 🗺️ valhalla_client.py - Valhalla интеграция **(NEW)**

**Time-dependent routing engine:**
```python
class ValhallaClient:
    """
    Valhalla клиент с поддръжка на:
    - Time-dependent routing (час на тръгване)
    - Truck routing (височина, ширина, тегло)
    - Batch processing за големи datasets
    - HTTP connection pooling с retry стратегия
    - Автоматичен fallback към Haversine
    """
```

**Routing engine избор:**
```python
class RoutingEngine(Enum):
    OSRM = "osrm"          # Бърз, статичен routing
    VALHALLA = "valhalla"   # Time-dependent, с трафик

# Конфигурация
@dataclass
class RoutingConfig:
    engine: RoutingEngine = RoutingEngine.OSRM
    enable_time_dependent: bool = True    # Само за Valhalla
    departure_time: str = "08:00"         # Час на тръгване
```

**Valhalla конфигурация:**
```python
@dataclass
class ValhallaConfig:
    base_url: str = "http://localhost:8002"
    costing: str = "auto"          # "auto", "truck", "bicycle", "pedestrian"
    timeout_seconds: int = 60
    retry_attempts: int = 3
    
    # Time-dependent routing
    date_time_type: int = 1        # 0=current, 1=depart_at, 2=arrive_by
    
    # Truck-specific (ако costing="truck")
    truck_height: float = 3.5      # метри
    truck_width: float = 2.5       # метри
    truck_weight: float = 10.0     # тонове
```

**Intelligent matrix calculation:**
```python
def get_distance_matrix(self, locations):
    """
    Стратегия:
    - ≤50 локации: Директна sources_to_targets заявка
    - >50 локации: Batch подход с tqdm прогрес бар
    - Автоматичен fallback към Haversine при грешка
    """
```

**Fallback верига (main.py):**
```python
# 1. Ако engine=VALHALLA → опитай Valhalla
# 2. Ако Valhalla не е достъпен → fallback към OSRM
# 3. Ако engine=OSRM → използвай OSRM директно
# 4. Ако OSRM кеш съществува → зареди от кеш
# 5. Ако няма кеш → нова OSRM заявка
```

### 📊 output_handler.py - Визуализация и отчети

**Интерактивна карта с реални маршрути:**
```python
def _get_osrm_route_geometry(self, waypoints):
    """
    OSRM Route API integration:
    - Real road-based routing geometry
    - Turn-by-turn navigation data
    - Fallback to straight lines
    """
    url = f"{osrm_url}/route/v1/driving/{coords_str}?geometries=geojson&overview=full"
    # Returns detailed route geometry for visualization
```

**Excel reporting:**
- **Detailed route analysis**
- **Vehicle utilization metrics**
- **Performance statistics**
- **Styled worksheets** със цветово кодиране

---

## 🔬 Алгоритми и стратегии

### Mathematical Formulation

CVRP Optimizer решава следната математическа формулация:

```
Minimize: Σ(i,j)∈A Σk∈K cij * xijk

Subject to:
- Σk∈K Σj∈V xijk = 1  ∀i ∈ C    (всеки клиент се посещава веднъж)
- Σi∈V xijk - Σi∈V xjik = 0  ∀j ∈ V, k ∈ K    (flow conservation)
- Σi∈C di * Σj∈V xijk ≤ Qk  ∀k ∈ K    (capacity constraint)
- Σi,j∈S xijk ≤ |S| - 1  ∀S ⊆ C, |S| ≥ 2    (subtour elimination)

Where:
- C = set of customers
- V = C ∪ {depots}
- K = set of vehicles  
- cij = cost (distance/time) от i до j
- di = demand на клиент i
- Qk = capacity на vehicle k
```

### Center Zone Priority Logic

```python
def apply_center_zone_logic(self, routing, manager):
    """
    Multi-callback system за center zone приоритизация:
    
    1. CENTER_BUS callback: 90% отстъпка в center zone
    2. EXTERNAL_BUS callback: 40,000 penalty в center zone  
    3. INTERNAL_BUS callback: 40,000 penalty в center zone
    4. SPECIAL_BUS callback: 40,000 penalty в center zone
    5. VRATZA_BUS callback: 40,000 penalty в center zone
    """
```

### TSP Post-optimization

```python
def _optimize_route_from_depot(self, customers, depot_location):
    """
    OR-Tools TSP решател за финална оптимизация:
    
    1. Create TSP problem (single vehicle, no constraints)
    2. Use Euclidean distance matrix
    3. Apply AUTOMATIC strategy за бързо решаване  
    4. Extract optimal customer sequence
    5. Recalculate accurate times със vehicle-specific service times
    """
```

---

## 🗺️ Интерактивна визуализация

### Advanced Folium Integration

**Features:**
- ✅ **Real route geometry** от OSRM или Valhalla — истински пътища по улиците
- ✅ **Dual routing engine** — автоматичен избор между OSRM/Valhalla за геометрия
- ✅ **Color-coded routes** - уникален цвят за всеки автобус (20 цвята)
- ✅ **Interactive popups** - детайлна информация за маршрути
- ✅ **Distance/time statistics** - реални метрики
- ✅ **Depot markers** - начални/крайни точки
- ✅ **Customer numbering** - ред на посещение
- ✅ **Warehouse visualization** - необслужени клиенти
- ✅ **Valhalla encoded polyline decoding** - декодиране на маршрутна геометрия

**Routing engine за визуализация:**
```python
# output_handler.py автоматично избира routing engine:
if routing_engine == RoutingEngine.VALHALLA:
    geometry = self._get_valhalla_route_geometry(start, end)
else:
    geometry = self._get_osrm_route_geometry(start, end)

# Fallback към прави линии ако routing engine не е достъпен
```

### Visual Features

**Map styling:**
- **Custom markers**: FontAwesome икони за различни типове
- **Route colors**: Unique colors за всеки автобус
- **Popup information**: Comprehensive route statistics
- **Layer control**: Toggle visibility на различни елементи

---

## ⚙️ Конфигурационна система

### Централизирана конфигурация

```python
# config.py структура
@dataclass
class MainConfig:
    vehicles: Optional[List[VehicleConfig]] = None
    locations: LocationConfig = field(default_factory=LocationConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)      # NEW: Избор на routing engine
    osrm: OSRMConfig = field(default_factory=OSRMConfig)
    valhalla: ValhallaConfig = field(default_factory=ValhallaConfig)    # NEW: Valhalla конфигурация
    input: InputConfig = field(default_factory=InputConfig)
    warehouse: WarehouseConfig = field(default_factory=WarehouseConfig)
    cvrp: CVRPConfig = field(default_factory=CVRPConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
```

### Ключови настройки

**CVRP Solver настройки:**
```python
@dataclass
class CVRPConfig:
    solver_type: str = "pyvrp"       # "or_tools" или "pyvrp" (NEW)
    algorithm: str = "or_tools"
    time_limit_seconds: int = 30
    first_solution_strategy: str = "CHRISTOFIDES"
    local_search_metaheuristic: str = "GUIDED_LOCAL_SEARCH"
    
    # LNS (Large Neighborhood Search) параметри (NEW)
    lns_time_limit_seconds: float = 15
    lns_num_nodes: int = 120
    lns_num_arcs: int = 110
    use_full_propagation: bool = True
    search_lambda_coefficient: float = 0.8
    
    # Паралелна обработка
    enable_parallel_solving: bool = False  # Изключено за PyVRP стабилност
    num_workers: int = -1  # -1 = all cores minus one
    
    # Финална реконфигурация
    enable_final_depot_reconfiguration: bool = True
    
    # Стартово време
    enable_start_time_tracking: bool = True
    global_start_time_minutes: int = 480  # 8:00 AM
    
    # Пропускане на клиенти
    allow_customer_skipping: bool = True
    distance_penalty_disjunction: int = 45000
```

**Routing Engine настройки (NEW):**
```python
@dataclass
class RoutingConfig:
    engine: RoutingEngine = RoutingEngine.OSRM  # OSRM или VALHALLA
    enable_time_dependent: bool = True           # Само за Valhalla
    departure_time: str = "08:00"                # HH:MM формат
```

**Градски трафик настройки (NEW):**
```python
@dataclass
class LocationConfig:
    # ... депа и център зона ...
    
    # Параметри за градски трафик (задръствания в София)
    city_center_coords: Tuple[float, float] = (42.6977, 23.3219)  # Площад Независимост
    city_traffic_radius_km: float = 10.0      # Радиус на градската зона
    city_traffic_duration_multiplier: float = 1.6  # +60% заради трафик
    enable_city_traffic_adjustment: bool = True
```

**Vehicle-specific настройки:**
```python
# Примерна конфигурация за INTERNAL_BUS
VehicleConfig(
    vehicle_type=VehicleType.INTERNAL_BUS,
    capacity=385,                    # стекове
    count=7,                         # брой автобуси
    max_distance_km=None,           # без лимит
    max_time_hours=8,               # максимално работно време
    service_time_minutes=7,         # време за обслужване
    enabled=True,                   # активен
    start_location=depot_main,      # стартова точка (главно депо)
    start_time_minutes=480,         # 8:00 AM
    tsp_depot_location=depot_main   # TSP от главното депо
)

# Примерна конфигурация за CENTER_BUS
VehicleConfig(
    vehicle_type=VehicleType.CENTER_BUS,
    capacity=320,                    # по-малък капацитет
    count=1,                         # 1 автобус за центъра
    max_time_hours=8,
    service_time_minutes=9,         # по-дълго обслужване в центъра
    start_location=depot_main,
    start_time_minutes=510,         # 8:30 AM (по-късен старт)
    tsp_depot_location=depot_main
)

# Примерна конфигурация за VRATZA_BUS
VehicleConfig(
    vehicle_type=VehicleType.VRATZA_BUS,
    capacity=385,
    count=3,
    max_time_hours=8,
    service_time_minutes=7,
    enabled=False,                   # изключен по подразбиране
    max_customers_per_route=40,     # лимит за клиенти
    start_location=depot_vratza,    # стартира от Враца
    tsp_depot_location=depot_vratza # TSP от Враца депо
)
```

---

## 🏁 Стартиране и използване

### Методи на стартиране

**1. EXE файл (препоръчително):**
```bash
# Автоматично търсене на input.xlsx
CVRP_Optimizer.exe

# С посочен файл
CVRP_Optimizer.exe data\custom_input.xlsx
CVRP_Optimizer.exe "C:\Path\To\File.xlsx"
```

**2. Python скрипт:**
```bash
python main.py                    # Търси data/input.xlsx
python main.py custom_file.xlsx   # Използва посочения файл
```

**3. Batch файл:**
```bash
start_cvrp.bat                   # Интерактивно стартиране
```

### Структура на входния файл

**Задължителни колони:**

| Колона | Описание | Пример |
|--------|----------|--------|
| Клиент | Уникален ID | "1001" |
| Име Клиент | Име на клиента | "Магазин Център" |
| GpsData | GPS координати | "42.123456, 23.567890" |
| Обем | Обем в стекове | 10.5 |

**Примерен входен файл:**
```
| Клиент | Име Клиент         | GpsData                | Обем |
|--------|-------------------|------------------------|------|
| 1001   | Магазин Център    | 42.697357, 23.323810  | 10.5 |
| 1002   | Офис Южен         | 42.684568, 23.319735  | 5.2  |
| 1003   | Склад Запад       | 42.693874, 23.301234  | 15.8 |
```

### Изходни файлове

**1. Интерактивна карта** - `output/interactive_map.html`:
- Real-time OSRM/Valhalla маршрути (автоматичен избор)
- Color-coded автобуси (20 уникални цвята)
- Interactive popups с детайли
- Distance/time статистики

**2. Excel отчет** - `output/excel/cvrp_report.xlsx`:
- Детайлни маршрути по автобуси
- Capacity utilization
- Performance метрики
- Customer sequence

**3. Лог файл** - `logs/cvrp.log`:
- Детайлна диагностика
- Routing engine информация (OSRM/Valhalla)
- Solver информация (OR-Tools/PyVRP)
- Performance статистики
- Error handling информация

---

## 📈 Performance и мащабиране

### Benchmark резултати

**Тестено на Intel i7-8700K, 16GB RAM, SSD:**

| Клиенти | First Solution | Good Solution | Best Solution | Memory |
|---------|---------------|---------------|---------------|--------|
| 25      | 5-15s         | 30-60s        | 2-5 min       | 150MB  |
| 50      | 15-30s        | 2-5 min       | 5-10 min      | 250MB  |
| 100     | 30-90s        | 5-10 min      | 10-20 min     | 400MB  |
| 200     | 90-180s       | 10-20 min     | 20-40 min     | 800MB  |
| 300     | 3-5 min       | 20-30 min     | 40-60 min     | 1.2GB  |

### OSRM Performance

- **Local server**: 100-500ms за 50×50 matrix
- **Public API**: 1-5s за същата matrix  
- **Cache hit ratio**: 85-95% при repeated runs

### Optimization strategies

**Memory optimization:**
```python
def optimize_for_large_datasets(self, num_customers):
    if num_customers > 500:
        # Enable sparse matrices
        self.use_sparse_matrices = True
        
        # Reduce cache size
        self.cache_size_limit = 50  # MB
        
        # Enable streaming processing
        self.enable_streaming = True
```

**Parallel processing:**
```python
def get_optimal_workers(self, num_customers):
    cores = os.cpu_count()
    
    if num_customers < 50:
        return 1  # Single-threaded за малки проблеми
    elif num_customers < 200:
        return max(2, cores // 2)  # Half cores
    else:
        return max(4, cores - 1)   # Most cores, leave 1 for OS
```

---

## 🔍 Troubleshooting

### Чести проблеми

**1. OR-Tools инсталация:**
```bash
# Windows: Visual C++ missing
# Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Memory error
pip install --no-cache-dir ortools

# Version conflicts  
pip install ortools==9.7.2996 --force-reinstall
```

**2. PyVRP инсталация (NEW):**
```bash
# Инсталиране на PyVRP
pip install pyvrp>=0.5.0,<0.6.0

# Ако има build грешки (Windows)
pip install pyvrp --no-build-isolation

# Проверка
python -c "from pyvrp import Model; print('PyVRP OK')"
```

**3. Valhalla connectivity (NEW):**
```python
# Проверка на Valhalla сървър
def test_valhalla():
    import requests
    try:
        response = requests.get("http://localhost:8002/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"Valhalla версия: {data.get('version', 'unknown')}")
            return True
        return False
    except:
        return False

# Ако Valhalla не е достъпен, системата автоматично fallback към OSRM
```

**4. OSRM connectivity:**
```python
# Test OSRM connection
def test_osrm():
    import requests
    try:
        response = requests.get("http://localhost:5000/route/v1/driving/23.3,42.7;23.3,42.7", timeout=10)
        return response.status_code == 200
    except:
        return False
```

**5. Memory issues:**
```python
# Memory profiling
import tracemalloc
tracemalloc.start()

# Your code here

current, peak = tracemalloc.get_traced_memory()
print(f"Memory: {current/1024/1024:.1f}MB (peak: {peak/1024/1024:.1f}MB)")
```

**6. Excel формат проблеми:**
```python
def validate_excel(file_path):
    required_columns = ['Клиент', 'Име Клиент', 'GpsData', 'Обем']
    df = pd.read_excel(file_path)
    
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
        
    if not pd.api.types.is_numeric_dtype(df['Обем']):
        raise ValueError("'Обем' must be numeric")
```

### Debug режим

**Enabling detailed debugging:**
```python
# config.py
DEBUG_CONFIG = {
    "debug_mode": True,
    "logging": {"log_level": "DEBUG"},
    "cvrp": {"log_search": True},
    "osrm": {"enable_request_logging": True}
}
```

**Performance profiling:**
```bash
python -m cProfile -o profile.prof main.py data/input.xlsx
python -c "import pstats; p=pstats.Stats('profile.prof'); p.sort_stats('cumulative'); p.print_stats(10)"
```

---

## 🚀 Advanced Features

### 🔄 Dual Solver система

Системата поддържа два VRP solver-а, които могат да се избират чрез конфигурацията:

| Характеристика | OR-Tools | PyVRP |
|---|---|---|
| **Тип алгоритъм** | Constraint Programming + метаевристики | Iterated Local Search (ILS) |
| **Център зона** | Multi-callback система | Двупрофилна система |
| **Customer dropping** | Disjunction penalty (фиксирана) | Prize-based (пропорционална на обем) |
| **Капацитет** | Единичен (обем) | Двумерен [обем, макс_клиенти] |
| **Dimensions** | 4 (Capacity, Distance, Stops, Time) | Вградени в модела |
| **Паралелна обработка** | Да (multi-strategy) | Не (seed-based) |
| **TSP пост-оптимизация** | Да | Не е необходимо |
| **Конфигурация** | `solver_type: "or_tools"` | `solver_type: "pyvrp"` |

**Превключване:**
```python
# config.py
solver_type: str = "pyvrp"  # Смени на "or_tools" за OR-Tools
```

### 🗺️ Dual Routing Engine

| Характеристика | OSRM | Valhalla |
|---|---|---|
| **Тип** | Статичен routing | Time-dependent routing |
| **Трафик** | Не | Да (по час на тръгване) |
| **Профили** | driving | auto, truck, bicycle, pedestrian |
| **Truck restrictions** | Не | Да (ш., в., т.) |
| **Speed** | Много бърз | Бърз |
| **Port** | 5000 | 8002 |
| **Fallback** | Public OSRM → Haversine | → OSRM → Haversine |

**Превключване:**
```python
# config.py
@dataclass
class RoutingConfig:
    engine: RoutingEngine = RoutingEngine.VALHALLA  # или RoutingEngine.OSRM
    enable_time_dependent: bool = True
    departure_time: str = "08:00"
```

### 🚦 Градски трафик симулация

Системата симулира градски трафик (задръствания в София) чрез прилагане на множител за времето на пътуване в градска зона:

```python
# Конфигурация
city_center_coords = (42.6977, 23.3219)     # Площад Независимост
city_traffic_radius_km = 10.0                # 10 км радиус
city_traffic_duration_multiplier = 1.6       # +60% време заради трафик
enable_city_traffic_adjustment = True

# Логика (прилага се и в OR-Tools, и в PyVRP)
if both_locations_in_city_zone:
    duration = base_duration * 1.6  # +60% за градски трафик
```

**Как работи:**
1. За всяка локация (депо/клиент) се проверява дали попада в градската зона (10 км от центъра)
2. Ако **и двете** точки (source и destination) са в градската зона, времето за пътуване се умножава
3. Множителят се прилага **само на duration**, не на distance
4. Работи и с OSRM, и с Valhalla матрици
5. В PyVRP: прилага се директно в edge duration
6. В OR-Tools: прилага се в time callback

### 📦 Компилиране в EXE

Системата поддържа компилиране в standalone EXE файл с PyInstaller:

```bash
python build_exe.py
```

**EXE Features:**
- ✅ Standalone — не изисква Python инсталация
- ✅ Поддържа и OR-Tools, и PyVRP solver
- ✅ Поддържа и OSRM, и Valhalla routing engine
- ✅ Автоматично създаване на директории (logs, output, cache, data)
- ✅ Динамично зареждане на config.py от директорията на EXE
- ✅ Повторно стартиране след завършване (потребителят избира)
- ✅ UTF-8 поддръжка за Windows конзола
- ✅ Multiprocessing freeze_support() за паралелна обработка

**EXE входна точка (main_exe.py):**
```python
def main_exe():
    while True:  # Безкраен цикъл за повторно стартиране
        setup_exe_environment()
        load_config()  # Динамично от директорията на EXE
        main()  # Основната CVRP оптимизация
        
        restart = input("Искате ли да стартирате отново? (да/не): ")
        if restart != 'да':
            break
```

---

## 📚 Заключение

CVRP Optimizer е напреднала, professional-grade система за Vehicle Routing Problem optimization, която комбинира:

- **Dual Solver система** — OR-Tools (Constraint Programming) + PyVRP (Iterated Local Search)
- **Dual Routing Engine** — OSRM (статичен) + Valhalla (time-dependent с трафик)
- **Математическа прецизност** с Google OR-Tools и PyVRP
- **Реални географски данни** с OSRM/Valhalla интеграция
- **Intelligent business logic** за център зона приоритизация (двупрофилна система)
- **Градски трафик симулация** с корекция на времена в градска зона (+60%)
- **Advanced visualization** с интерактивни карти (OSRM/Valhalla геометрия)
- **Паралелна обработка** за оптимални резултати (multi-strategy для OR-Tools)
- **Персонализирани TSP депа** за всеки тип автобус
- **Prize-based customer dropping** в PyVRP (пропорционално на обем)
- **Truck routing** с Valhalla (височина, ширина, тегло)
- **EXE компилация** с PyInstaller за standalone deployment
- **Enterprise-ready архитектура** за мащабиране

Системата е готова за production използване и може да се адаптира за различни logistics и distribution сценарии.

---

## 📂 Структура на проекта

```
CVRP_Optimizer/
├── main.py                  # Главен оркестратор
├── main_exe.py              # EXE входна точка (с повторно стартиране)
├── run_main.py              # Прост wrapper за main.py
├── config.py                # Централна конфигурация (всички настройки)
├── input_handler.py         # Входни данни (Excel, GPS парсиране)
├── warehouse_manager.py     # Складова логика (разпределение)
├── cvrp_solver.py           # OR-Tools CVRP решател
├── pyvrp_solver.py          # PyVRP CVRP решател (NEW)
├── osrm_client.py           # OSRM клиент (статичен routing)
├── valhalla_client.py       # Valhalla клиент (time-dependent) (NEW)
├── output_handler.py        # Визуализация и Excel отчети
├── build_exe.py             # Компилация в EXE (PyInstaller)
├── start_cvrp.bat           # Windows batch стартер
├── requirements.txt         # Python зависимости (вкл. pyvrp)
├── data/                    # Входни данни (input.xlsx)
├── output/                  # Изходни файлове
│   ├── interactive_map.html # Интерактивна карта
│   └── excel/               # Excel отчети
├── logs/                    # Лог файлове
├── cache/                   # Кеш (OSRM матрици)
├── osrm-data/               # OSRM данни (Bulgaria PBF)
├── valhalla-data/           # Valhalla данни (tiles, config) (NEW)
│   ├── bulgaria-latest.osm.pbf
│   ├── valhalla.json        # Valhalla сървър конфигурация
│   └── valhalla_tiles/      # Routing tiles
└── analysis/                # Документация и анализи
```

---

## 📞 Support & Contributing

- **GitHub Issues**: За bug reports и feature requests
- **Documentation**: Detailed wiki в GitHub repository  
- **Contributing**: Pull requests са добре дошли
- **License**: MIT License

**Current Version**: 4.0.0  
**Last Update**: Февруари 2026  
**Maintainer**: CVRP Optimizer Development Team
