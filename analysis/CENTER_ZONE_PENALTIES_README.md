# 🚫 Център Зона - Глоба за останалите бусове

## Общо описание

Добавена е функционалност за **глоба на останалите бусове за влизане в центъра**, която ограничава достъпа на **EXTERNAL_BUS** и **INTERNAL_BUS** превозните средства до клиенти в център зоната.

## Конфигурация

### LocationConfig разширения

В `config.py` са добавени нови параметри в `LocationConfig`:

```python
@dataclass
class LocationConfig:
    depot_location: Tuple[float, float] = (42.695785029219415, 23.23165887245312)
    center_location: Tuple[float, float] = (42.69735652560932, 23.323809998750914)
    center_zone_radius_km: float = 2  # Радиус на център зоната
    enable_center_zone_priority: bool = True  # Приоритет за CENTER_BUS
    
    # 🆕 Параметри за глобата на останалите бусове
    external_bus_center_penalty_multiplier: float = 10.0  # Множител за EXTERNAL_BUS
    internal_bus_center_penalty_multiplier: float = 2.0   # Множител за INTERNAL_BUS
    enable_center_zone_restrictions: bool = True  # Активиране на ограниченията
```

### Параметри

- **`external_bus_center_penalty_multiplier`**: Множител за глоба на EXTERNAL_BUS за влизане в центъра (по подразбиране: 10.0x)
- **`internal_bus_center_penalty_multiplier`**: Множител за глоба на INTERNAL_BUS за влизане в центъра (по подразбиране: 2.0x)
- **`enable_center_zone_restrictions`**: Дали да се прилагат ограничения за влизане в центъра (по подразбиране: True)

## Функционалност

### 1. Глоба за EXTERNAL_BUS

**EXTERNAL_BUS** превозните средства получават **10x увеличение на разходите** за клиенти в център зоната:

```python
# В cvrp_solver.py
def external_bus_penalty_callback(from_index, to_index):
    # Ако това е клиент в център зоната
    if customer.id in center_zone_customer_ids:
        # Увеличаваме разходите за EXTERNAL_BUS с конфигурируем множител
        multiplier = self.location_config.external_bus_center_penalty_multiplier
        return int(self.distance_matrix.distances[from_node][to_node] * multiplier)
```

### 2. Глоба за INTERNAL_BUS

**INTERNAL_BUS** превозните средства получават **2x увеличение на разходите** за клиенти в център зоната:

```python
# В cvrp_solver.py
def internal_bus_penalty_callback(from_index, to_index):
    # Ако това е клиент в център зоната
    if customer.id in center_zone_customer_ids:
        # Увеличаваме разходите за INTERNAL_BUS с конфигурируем множител
        multiplier = self.location_config.internal_bus_center_penalty_multiplier
        return int(self.distance_matrix.distances[from_node][to_node] * multiplier)
```

### 3. Приоритет за CENTER_BUS

**CENTER_BUS** превозните средства продължават да получават **30% намалени разходи** за клиенти в център зоната.

## Логика на ограниченията

### 1. Идентификация на превозните средства

В `cvrp_solver.py` се идентифицират различните типове превозни средства:

```python
# Идентифицираме различните типове превозни средства
center_bus_vehicle_ids = []
external_bus_vehicle_ids = []
internal_bus_vehicle_ids = []

for v_config in self.vehicle_configs:
    if v_config.vehicle_type == VehicleType.CENTER_BUS:
        center_bus_vehicle_ids.append(vehicle_id)
    elif v_config.vehicle_type == VehicleType.EXTERNAL_BUS:
        external_bus_vehicle_ids.append(vehicle_id)
    elif v_config.vehicle_type == VehicleType.INTERNAL_BUS:
        internal_bus_vehicle_ids.append(vehicle_id)
```

### 2. Прилагане на глобите

Глобите се прилагат чрез OR-Tools callback функции:

```python
# Регистрираме callback-а за EXTERNAL_BUS превозните средства
external_bus_callback_index = routing.RegisterTransitCallback(external_bus_penalty_callback)

for vehicle_id in data['external_bus_vehicle_ids']:
    routing.SetArcCostEvaluatorOfVehicle(external_bus_callback_index, vehicle_id)
```

## Използване

### Активиране/деактивиране

```python
from config import get_config

config = get_config()

# Активиране на ограниченията
config.locations.enable_center_zone_restrictions = True

# Настройка на глобите
config.locations.external_bus_center_penalty_multiplier = 15.0  # 15x глоба за EXTERNAL_BUS
config.locations.internal_bus_center_penalty_multiplier = 3.0   # 3x глоба за INTERNAL_BUS
```

### Деактивиране

```python
config.locations.enable_center_zone_restrictions = False
```

### Промяна на глобите

```python
# Силни ограничения
config.locations.external_bus_center_penalty_multiplier = 20.0  # Ефективна забрана
config.locations.internal_bus_center_penalty_multiplier = 5.0   # Силна глоба

# Слаби ограничения
config.locations.external_bus_center_penalty_multiplier = 5.0   # Умерена глоба
config.locations.internal_bus_center_penalty_multiplier = 1.5   # Лека глоба
```

## Тестване

Използвайте `test_center_zone_penalties.py` за тестване:

```bash
python test_center_zone_penalties.py
```

Тестът демонстрира различни сценарии:
- Стандартни глоби (EXTERNAL_BUS 10x, INTERNAL_BUS 2x)
- Силни глоби (EXTERNAL_BUS 20x, INTERNAL_BUS 5x)
- Слаби глоби (EXTERNAL_BUS 5x, INTERNAL_BUS 1.5x)
- Без ограничения

## Логове

Системата генерира детайлни логове:

```
🚫 Прилагане на глоба за EXTERNAL_BUS в център зоната
⚠️ Прилагане на глоба за INTERNAL_BUS в център зоната
🎯 Прилагане на приоритет за CENTER_BUS в център зоната
```

## Конфигурационни опции

### Пълна конфигурация

```python
@dataclass
class LocationConfig:
    depot_location: Tuple[float, float] = (42.695785029219415, 23.23165887245312)
    center_location: Tuple[float, float] = (42.69735652560932, 23.323809998750914)
    center_zone_radius_km: float = 2.0
    enable_center_zone_priority: bool = True
    external_bus_center_penalty_multiplier: float = 10.0
    internal_bus_center_penalty_multiplier: float = 2.0
    enable_center_zone_restrictions: bool = True
```

### Сценарии за използване

#### 1. Строги ограничения (забрана на EXTERNAL_BUS)
```python
config.locations.external_bus_center_penalty_multiplier = 20.0  # Ефективна забрана
config.locations.internal_bus_center_penalty_multiplier = 5.0   # Силна глоба
```

#### 2. Умерени ограничения
```python
config.locations.external_bus_center_penalty_multiplier = 10.0  # Стандартна глоба
config.locations.internal_bus_center_penalty_multiplier = 2.0   # Умерена глоба
```

#### 3. Леки ограничения
```python
config.locations.external_bus_center_penalty_multiplier = 5.0   # Лека глоба
config.locations.internal_bus_center_penalty_multiplier = 1.5   # Много лека глоба
```

#### 4. Без ограничения
```python
config.locations.enable_center_zone_restrictions = False
```

## Технически детайли

### Интеграция с OR-Tools

1. **Идентификация на различните типове превозни средства**
2. **Създаване на специални callback функции за всяка глоба**
3. **Прилагане на различни множители за различните типове**
4. **Регистриране на callback-ите за съответните превозни средства**

### Алгоритъм за прилагане на глобите

```python
def apply_penalty_callback(from_index, to_index):
    from_node = manager.IndexToNode(from_index)
    to_node = manager.IndexToNode(to_index)
    
    # Ако това е клиент в център зоната
    if to_node >= len(self.unique_depots):
        customer_index = to_node - len(self.unique_depots)
        customer = self.customers[customer_index]
        
        if customer.id in center_zone_customer_ids:
            # Прилагаме глобата
            multiplier = get_penalty_multiplier_for_vehicle_type(vehicle_type)
            return int(self.distance_matrix.distances[from_node][to_node] * multiplier)
    
    return int(self.distance_matrix.distances[from_node][to_node])
```

## Заключение

Новата функционалност позволява:

1. **Контролиран достъп** на различните типове превозни средства до център зоната
2. **Конфигурируеми глоби** за различните типове превозни средства
3. **Гъвкавост** в настройката на ограниченията
4. **Интеграция** с съществуващата логика за приоритизиране на CENTER_BUS

Това осигурява по-добър контрол върху разпределението на превозните средства и оптимизира използването на специализираните CENTER_BUS превозни средства за център зоната. 