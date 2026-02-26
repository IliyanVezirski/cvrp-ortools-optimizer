# Анализ на модулите за оптимизация

## osrm_client.py - OSRM клиент за разстояния и маршрути

### Основни класове:

**`DistanceMatrix`**
Съдържа матрица с разстояния и времена:
- `distances` - разстояния в метри (List[List[float]])
- `durations` - времена в секунди (List[List[float]])
- `locations` - GPS координати (List[Tuple[float, float]])
- `sources` - индекси на източниците
- `destinations` - индекси на дестинациите

**`OSRMCache`**
Кеш система за OSRM заявки:
- Кешира резултати за 24 часа
- Използва MD5 хеширане за ключове
- Автоматично почиства изтекли записи

**`OSRMClient`**
Главен клиент за OSRM API:

**Ключови методи:**
- `get_distance_matrix()` - получава матрица с разстояния
- `_try_table_api_with_fallback()` - Table API с fallback
- `_build_matrix_via_routes_only()` - Route API за големи datasets
- `_build_optimized_table_batches()` - оптимизирани batch заявки

**Стратегии според размера:**
- ≤30 локации - директно Table API
- 31-500 локации - batch Table API chunks
- >500 локации - паралелни Route API заявки

**Chunking логика:**
- Chunk размер 80-90 координати
- Интелигентно batch обработване
- Retry механизъм при грешки

---

## cvrp_solver.py - OR-Tools решател за CVRP

### Основни класове:

**`Route`**
Представлява маршрут за едно превозно средство:
- `vehicle_type` - тип на превозното средство
- `customers` - списък с клиенти
- `total_distance_km` - общо разстояние
- `total_time_minutes` - общо време
- `total_volume` - общ обем
- `is_feasible` - допустимост на маршрута

**`CVRPSolution`**
Цялостно решение на CVRP проблема:
- `routes` - списък с маршрути
- `total_distance_km` - общо разстояние
- `total_vehicles_used` - използвани превозни средства
- `fitness_score` - оценка на решението
- `is_feasible` - допустимост на решението

**`ORToolsProgressTracker`**
Следи прогреса на OR-Tools оптимизация:
- Real-time progress bar с tqdm
- Отчита най-добри решения
- Threading за неблокиращо обновяване

**`RouteBuilder`**
Построява и валидира маршрути:
- Изчислява разстояния и времена
- Валидира capacity constraints
- Проверява time constraints

**`ORToolsSolver`**
OR-Tools CVRP решател:

**Основни компоненти:**
- Distance callback функции
- Capacity constraints
- Time window constraints  
- Vehicle specific constraints

**Методи:**
- `solve()` - решава CVRP проблема
- `_extract_solution()` - извлича решението
- `_fallback_solution()` - backup алгоритъм

**Fallback алгоритъм:**
- Greedy bin packing подход
- Сортиране по обем
- Първо вписване (first-fit)

**`CVRPSolver`**
Главен wrapper клас:
- Управлява OR-Tools lifecycle
- Обработва грешки
- Предоставя unified API

### OR-Tools настройки:

**First Solution Strategies:**
- `AUTOMATIC` - OR-Tools избира най-добрата
- `PATH_CHEAPEST_ARC` - евристика за най-евтин път
- `SAVINGS` - Clarke-Wright savings алгоритъм
- `PARALLEL_CHEAPEST_INSERTION` - паралелно вмъкване

**Local Search Metaheuristics:**
- `AUTOMATIC` - автоматично избиране
- `GUIDED_LOCAL_SEARCH` - насочено локално търсене
- `SIMULATED_ANNEALING` - симулирано охлаждане

**Constraints типове:**
- Capacity constraints - ограничения на капацитета
- Time window constraints - времеви прозорци
- Distance constraints - ограничения на разстоянието
- Vehicle specific constraints - специфични за превозното средство

**Timeout стратегии:**
- 60s - бързо тестване
- 300s - стандартна употреба  
- 900s - задълбочена оптимизация
- 1800s - максимална оптимизация

### Алгоритмични детайли:

**Distance Matrix:**
- Използва OSRM за реални разстояния
- Fallback към Haversine формулата
- Кеширане за performance

**Vehicle Assignment:**
- Автоматично разпределение на превозни средства
- Поддръжка на различни типове
- Capacity и distance ограничения

**Solution Extraction:**
- Mapване от OR-Tools решение
- Изчисляване на реални метрики
- Валидация на допустимостта

**Error Handling:**
- Graceful degradation при OR-Tools грешки
- Fallback към опростен алгоритъм
- Детайлно логиране на грешки 