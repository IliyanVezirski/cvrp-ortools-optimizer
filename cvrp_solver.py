"""
CVRP Solver - основен модул за решаване на Vehicle Routing Problem
Използва OR-Tools за ефективна оптимизация
"""

import random
import math
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging
 

# OR-Tools импорти
try:
    from ortools.constraint_solver import routing_enums_pb2
    from ortools.constraint_solver import pywrapcp
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False
    logging.warning("OR-Tools не е инсталиран. Ще се използва опростен алгоритъм.")

from config import get_config, CVRPConfig, VehicleConfig, VehicleType, LocationConfig
from input_handler import Customer
from osrm_client import DistanceMatrix
from warehouse_manager import WarehouseAllocation

logger = logging.getLogger(__name__)

def calculate_distance_km(coord1: Optional[Tuple[float, float]], coord2: Tuple[float, float]) -> float:
    """Изчислява разстоянието между две GPS координати в километри"""
    if not coord1 or not coord2:
        return float('inf')
    
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return 6371 * c  # 6371 km е радиусът на Земята


 


@dataclass
class Route:
    """
    Представлява маршрут за едно превозно средство.

    Attributes:
        vehicle_type: Типът превозно средство (например INTERNAL_BUS, CENTER_BUS и др.).
        vehicle_id: Индекс на конкретния автобус от този тип (0..N-1 за типа).
        customers: Списък от клиенти в реда на обслужване.
        depot_location: GPS координати на депото, от което започва/завършва маршрутът.
        total_distance_km: Общо изминато разстояние по маршрута в километри.
        total_time_minutes: Общо време за маршрута (вкл. обслужване) в минути.
        total_volume: Общ обем на заявките по маршрута.
        is_feasible: Допустим ли е маршрутът спрямо твърдите ограничения.
    """
    vehicle_type: VehicleType
    vehicle_id: int
    customers: List[Customer]
    depot_location: Tuple[float, float]
    total_distance_km: float = 0.0
    total_time_minutes: float = 0.0
    total_volume: float = 0.0
    is_feasible: bool = True


@dataclass
class CVRPSolution:
    """
    Цялостно решение на CVRP проблема.

    Attributes:
        routes: Списък от маршрути (по един на използвано превозно средство).
        dropped_customers: Клиенти, които не са обслужени (ако е разрешено пропускане).
        total_distance_km: Сумарно изминато разстояние за всички маршрути в километри.
        total_time_minutes: Сумарно време за всички маршрути в минути.
        total_vehicles_used: Брой използвани превозни средства.
        fitness_score: Стойност на целевата функция (разстояние или друга метрика за ранжиране).
        is_feasible: Дали решението удовлетворява всички твърди ограничения.
        total_served_volume: Общо обслужен обем (за сравняване на решения).
    """
    routes: List[Route]
    dropped_customers: List[Customer]
    total_distance_km: float
    total_time_minutes: float
    total_vehicles_used: int
    fitness_score: float # Основната стойност, която solver-ът минимизира (разстояние)
    is_feasible: bool
    total_served_volume: float = 0.0 # Обхът обслужен обем, използван за избор на "победител"

 


class ORToolsSolver:
    """
    OR-Tools CVRP решател.

    Изгражда OR-Tools RoutingModel с размерности за обем, разстояние, брой спирки и време,
    прилага бизнес логика (мулти-депо, зони и приоритети), и извлича решение.

    Attributes:
        config: Обект `CVRPConfig` с всички настройки за решателя.
        vehicle_configs: Активни конфигурации на превозни средства (тип, капацитети, брой).
        customers: Списък клиенти, които трябва да се обслужат.
        distance_matrix: Предварително изчислена OSRM матрица (разстояния/времена).
        unique_depots: Списък уникални депа (GPS координати) в същия ред, както в матрицата.
        center_zone_customers: Клиенти, считани за “център зона”.
        location_config: Географски настройки, включително параметри за център зоната.
    """
    
    def __init__(self, config: CVRPConfig, vehicle_configs: List[VehicleConfig], 
                 customers: List[Customer], distance_matrix: DistanceMatrix, unique_depots: List[Tuple[float, float]], 
                 center_zone_customers: Optional[List[Customer]] = None, location_config: Optional[LocationConfig] = None):
        """
        Инициализира OR-Tools решателя.

        Args:
            config: Настройки на решателя.
            vehicle_configs: Активни превозни средства и техните ограничения.
            customers: Клиенти, които трябва да се обслужат.
            distance_matrix: OSRM матрица с разстояния (метри) и времена (секунди).
            unique_depots: Списък от GPS координати на депа (в реда им в матрицата).
            center_zone_customers: Клиенти в център зоната за прилагане на специални правила.
            location_config: Географски настройки (център координати, радиус, наказания/отстъпки).
        """
        self.config = config
        self.vehicle_configs = vehicle_configs
        self.customers = customers
        self.distance_matrix = distance_matrix
        self.unique_depots = unique_depots
        self.center_zone_customers = center_zone_customers or []
        self.location_config = location_config

    def solve(self) -> CVRPSolution:
        """
        Стартира OR-Tools търсенето и връща извлеченото решение.

        Минимизира разстояние и спазва твърдите ограничения:
        - Обем (capacity)
        - Разстояние (distance)
        - Брой клиенти (stops)
        - Време (time)

        Returns:
            Обект `CVRPSolution` със списък маршрути и агрегирани метрики.
        """
        if not ORTOOLS_AVAILABLE:
            logger.error("❌ OR-Tools не е инсталиран")
            return self._create_empty_solution()
        
        try:
            # 1. Създаване на data model и мениджър
            data = self._create_data_model()
            manager = pywrapcp.RoutingIndexManager(
                len(data['distance_matrix']), data['num_vehicles'], data['vehicle_starts'], data['vehicle_ends']
            )
            routing = pywrapcp.RoutingModel(manager)

            # 2. ЦЕНА НА МАРШРУТА = РАЗСТОЯНИЕ
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                # КРИТИЧЕН ФИКС: OR-Tools очаква ЦЯЛО ЧИСЛО.
                return int(self.distance_matrix.distances[from_node][to_node])
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

            # 3. ОГРАНИЧЕНИЯ (DIMENSIONS) - ВСИЧКИ СА АКТИВНИ
            # Обем
            def demand_callback(from_index):
                from_node = manager.IndexToNode(from_index)
                return int(data['demands'][from_node]) # int() за сигурност
            demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
            routing.AddDimensionWithVehicleCapacity(
                demand_callback_index, 0, data['vehicle_capacities'], True, "Capacity"
            )

            # Разстояние - АКТИВИРАНО
            routing.AddDimensionWithVehicleCapacity(
                transit_callback_index, 0, data['vehicle_max_distances'], True, "Distance"
            )

            # Брой клиенти (спирки) - АКТИВИРАНО
            def stop_callback(from_index):
                return 1 if manager.IndexToNode(from_index) not in data['depot_indices'] else 0
            stop_callback_index = routing.RegisterUnaryTransitCallback(stop_callback)
            routing.AddDimensionWithVehicleCapacity(
                stop_callback_index, 0, data['vehicle_max_stops'], True, "Stops"
            )

            # Време - АКТИВИРАНО със vehicle-specific service times
            logger.info("🕐 Създаване на vehicle-specific time callback...")
            
            # Предварително изчисляваме средния service time
            enabled_vehicles = [v for v in self.vehicle_configs if v.enabled]
            if enabled_vehicles:
                avg_service_time_seconds = int(sum(v.service_time_minutes * 60 for v in enabled_vehicles) / len(enabled_vehicles))
            else:
                avg_service_time_seconds = 15 * 60  # По подразбиране
            
            logger.info(f"📊 Средна service time за OR-Tools callback: {avg_service_time_seconds/60:.1f} минути")
            
            # Създаваме mapping от vehicle_id към service_time
            vehicle_service_times = data['vehicle_service_times']
            
            # === ГРАДСКИ ТРАФИК: Предварително определяме кои локации са в градската зона ===
            enable_city_traffic = False
            city_traffic_multiplier = 1.0
            city_center = None
            city_radius = 0
            
            if self.location_config:
                enable_city_traffic = getattr(self.location_config, 'enable_city_traffic_adjustment', False)
                city_traffic_multiplier = getattr(self.location_config, 'city_traffic_duration_multiplier', 1.0)
                city_center = getattr(self.location_config, 'city_center_coords', None)
                city_radius = getattr(self.location_config, 'city_traffic_radius_km', 12.0)
            
            # Определяме кои локации са в градската зона
            locations_in_city = []
            num_locations = len(self.distance_matrix.distances)
            for loc_idx in range(num_locations):
                if loc_idx < len(self.unique_depots):
                    # Депо
                    lat, lon = self.unique_depots[loc_idx]
                else:
                    # Клиент
                    client_idx = loc_idx - len(self.unique_depots)
                    if client_idx < len(self.customers):
                        lat, lon = self.customers[client_idx].coordinates or (0, 0)
                    else:
                        lat, lon = 0, 0
                
                # Проверяваме дали е в градската зона
                in_city = False
                if enable_city_traffic and city_center:
                    dist_to_city_center = calculate_distance_km((lat, lon), city_center)
                    in_city = dist_to_city_center <= city_radius
                locations_in_city.append(in_city)
            
            if enable_city_traffic and city_center:
                city_locations_count = sum(locations_in_city)
                logger.info(f"🚗 Градски трафик АКТИВИРАН за OR-Tools:")
                logger.info(f"  - Център: {city_center}")
                logger.info(f"  - Радиус: {city_radius} км")
                logger.info(f"  - Множител: {city_traffic_multiplier} (+{(city_traffic_multiplier-1)*100:.0f}%)")
                logger.info(f"  - Локации в градска зона: {city_locations_count}/{num_locations}")
            
            def vehicle_specific_time_callback(from_index, to_index):
                try:
                    # Проверяваме за валидни индекси преди IndexToNode
                    if from_index < 0 or to_index < 0:
                        return 0
                    
                    # Опитваме се да извлечем node-овете
                    from_node = manager.IndexToNode(from_index)
                    to_node = manager.IndexToNode(to_index)
                    
                    # Проверяваме границите на матрицата
                    if (from_node >= len(self.distance_matrix.durations) or 
                        to_node >= len(self.distance_matrix.durations[0])):
                        logger.warning(f"⚠️ Индекси извън граници: from_node={from_node}, to_node={to_node}")
                        return 0
                    
                    travel_time = self.distance_matrix.durations[from_node][to_node]
                    
                    # === ГРАДСКИ ТРАФИК: Прилагаме множител ако и двете точки са в града ===
                    if enable_city_traffic and from_node < len(locations_in_city) and to_node < len(locations_in_city):
                        if locations_in_city[from_node] and locations_in_city[to_node]:
                            travel_time = travel_time * city_traffic_multiplier
                    
                    # Service time само за клиенти (не за депа) - използваме предварително изчислената стойност
                    node_service_time = 0
                    if from_node >= len(self.unique_depots):  # Ако започваме от клиент
                        node_service_time = avg_service_time_seconds
                    
                    result = int(travel_time + node_service_time)
                    
                    # Проверяваме за разумни стойности
                    if result < 0 or result > 86400:  # Повече от 24 часа е подозрително
                        logger.warning(f"⚠️ Подозрителна time стойност: {result} сек за {from_node}->{to_node}")
                        return min(result, 86400)
                    
                    return result
                    
                except (OverflowError, IndexError, ValueError) as e:
                    logger.warning(f"⚠️ Грешка в time callback ({from_index}->{to_index}): {e}")
                    # Връщаме безопасна стойност
                    return 3600  # 1 час по подразбиране
                except Exception as e:
                    logger.error(f"❌ Неочаквана грешка в time callback: {e}")
                    return 3600
            
            time_callback_index = routing.RegisterTransitCallback(vehicle_specific_time_callback)
            
            # Добавяме Time dimension
            routing.AddDimensionWithVehicleCapacity(
                time_callback_index, 0, data['vehicle_max_times'], False, "Time"
            )
            
            # Логваме service times за информация
            enabled_vehicles = [v for v in self.vehicle_configs if v.enabled]
            if enabled_vehicles:
                avg_service_time = sum(v.service_time_minutes for v in enabled_vehicles) / len(enabled_vehicles)
                logger.info(f"📊 Service times (поради OR-Tools ограничения използваме средна стойност):")
                logger.info(f"  - Средно време: {avg_service_time:.1f} мин/клиент")
                for v in enabled_vehicles:
                    logger.info(f"  - {v.vehicle_type.value}: {v.service_time_minutes} мин/клиент (конфигурирано)")
                logger.warning("⚠️ OR-Tools не поддържа vehicle-specific service times в transit callbacks")
                logger.info("💡 Service times се прилагат по време на solution extraction с точни стойности")
            
            logger.info("✅ Time callback настроен успешно")

            # 4. ЛОГИКА ЗА ПРОПУСКАНЕ НА КЛИЕНТИ - с ДИНАМИЧНА глоба по твоята формула
            logger.info("Използва се ДИНАМИЧНА глоба за пропускане на клиенти, базирана на разстояние и обем.")
            
            # Вземаме само необходимите параметри от конфигурацията
            distance_penalty_disjunction = self.config.distance_penalty_disjunction
            
            logger.info(f"Отстъпки за далечни клиенти са премахнати - използват се реални разстояния")

            # Създаваме списък с клиенти в център зоната за бързо търсене
            center_zone_customer_ids = {c.id for c in self.center_zone_customers}
            
            logger.info(f"🎯 Прилагане на приоритет за център зоната: {len(self.center_zone_customers)} клиента")

            # Отстъпки за далечни клиенти са премахнати
            logger.info("🌟 Отстъпки за далечни клиенти са премахнати - използват се реални разстояния")
            
            # Създаваме отделен callback за всеки тип превозно средство
            
            # 1. БАЗОВ CALLBACK - запазва оригиналните разходи
            def base_distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return int(self.distance_matrix.distances[from_node][to_node])
                
            base_callback_index = routing.RegisterTransitCallback(base_distance_callback)
            
            # Първо регистрираме базовия callback за всички превозни средства
            routing.SetArcCostEvaluatorOfAllVehicles(base_callback_index)
            
            # 2. CALLBACK за EXTERNAL_BUS и INTERNAL_BUS - ОТСТЪПКИ ПРЕМАХНАТИ, ИЗПОЛЗВАМЕ РЕАЛНИТЕ РАЗСТОЯНИЯ
            def priority_non_center_callback(from_index, to_index):
                # Просто връщаме реалното разстояние без никакви отстъпки
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return int(self.distance_matrix.distances[from_node][to_node])
            
            # Регистрираме callback-а (сега без отстъпки)
            priority_non_center_callback_index = routing.RegisterTransitCallback(priority_non_center_callback)
            
            # Използваме същия регистриран callback, но вече без отстъпки за разстояния
            logger.info(f"🚛 Премахнати отстъпки за далечни клиенти - използват се реални разстояния за всички превозни средства")
            
            # Прилагаме callback-а за EXTERNAL_BUS превозни средства
            for vehicle_id in data['external_bus_vehicle_ids']:
                routing.SetArcCostEvaluatorOfVehicle(priority_non_center_callback_index, vehicle_id)
                logger.debug(f"  - Приложен callback без отстъпки за EXTERNAL_BUS #{vehicle_id}")
            
            # Прилагаме callback-а за INTERNAL_BUS превозни средства
            for vehicle_id in data['internal_bus_vehicle_ids']:
                routing.SetArcCostEvaluatorOfVehicle(priority_non_center_callback_index, vehicle_id)
                logger.debug(f"  - Приложен callback без отстъпки за INTERNAL_BUS #{vehicle_id}")
                
            # Прилагаме callback-а за SPECIAL_BUS превозни средства
            for vehicle_id in data['special_bus_vehicle_ids']:
                routing.SetArcCostEvaluatorOfVehicle(priority_non_center_callback_index, vehicle_id)
                logger.debug(f"  - Приложен callback без отстъпки за SPECIAL_BUS #{vehicle_id}")
                
            logger.info(f"✅ Отстъпки за далечни клиенти са премахнати")
            
            # Добавяме възможност за пропускане на клиенти (ако е разрешено)
            if self.config.allow_customer_skipping:
                logger.info("🔄 Добавяне на възможност за пропускане на клиенти...")
                for node_idx in range(len(self.unique_depots), len(data['distance_matrix'])):
                    # Добавяме възможността за пропускане, но с умерена глоба
                    # Ограничаваме до максимално допустимата стойност за int64
                    max_safe_penalty = 9223372036854775807  # Максимално допустима стойност за int64 (2^63-1)
                    penalty = min(distance_penalty_disjunction, max_safe_penalty)
                    routing.AddDisjunction([manager.NodeToIndex(node_idx)], penalty)
                logger.info(f"✅ Добавена възможност за пропускане на клиенти с глоба: {distance_penalty_disjunction}")
            else:
                logger.info("🚫 Пропускане на клиенти е ИЗКЛЮЧЕНО - ВСИЧКИ клиенти трябва да бъдат обслужени")
                logger.warning("⚠️ Ако няма достатъчно капацитет, solver-ът може да не намери решение!")

            # 5. ПРИОРИТИЗИРАНЕ НА CENTER_BUS ЗА ЦЕНТЪР ЗОНАТА
            if self.center_zone_customers and data['center_bus_vehicle_ids']:
                logger.info("🎯 Прилагане на приоритет за CENTER_BUS в център зоната")
                
                # Създаваме callback за приоритизиране на CENTER_BUS
                # CENTER_BUS получава САМО discount за клиенти в центъра
                # (penalty за извън центъра не се прилага, защото блокира стартирането)
                def center_bus_priority_callback(from_index, to_index):
                    from_node = manager.IndexToNode(from_index)
                    to_node = manager.IndexToNode(to_index)
                    
                    base_distance = int(self.distance_matrix.distances[from_node][to_node])
                    
                    # Ако това е клиент в център зоната - давам голям DISCOUNT
                    if to_node >= len(self.unique_depots):
                        customer_index = to_node - len(self.unique_depots)
                        customer = self.customers[customer_index]
                        
                        if customer.id in {c.id for c in self.center_zone_customers}:
                            # DISCOUNT: Намаляваме разходите за CENTER_BUS за клиенти В ЦЕНТЪРА
                            return int(base_distance * self.location_config.discount_center_bus)
                    
                    # За всички други клиенти - нормално разстояние (без penalty)
                    return base_distance
                
                # Регистрираме callback-а за CENTER_BUS превозните средства
                center_bus_callback_index = routing.RegisterTransitCallback(center_bus_priority_callback)
                
                for vehicle_id in data['center_bus_vehicle_ids']:
                    routing.SetArcCostEvaluatorOfVehicle(center_bus_callback_index, vehicle_id)
                    
                logger.info(f"  - CENTER_BUS discount for center clients: {self.location_config.discount_center_bus}")
                logger.info(f"  - Center zone customers: {len(self.center_zone_customers)}")
            
            # 6. ГЛОБА ЗА ОСТАНАЛИТЕ БУСОВЕ ЗА ВЛИЗАНЕ В ЦЕНТЪРА
            if data['external_bus_vehicle_ids'] and self.location_config and self.location_config.enable_center_zone_restrictions:
                logger.info("🚫 Прилагане на глоба за EXTERNAL_BUS в център зоната")
                
                # Създаваме callback за глоба на EXTERNAL_BUS
                def external_bus_penalty_callback(from_index, to_index):
                    from_node = manager.IndexToNode(from_index)
                    to_node = manager.IndexToNode(to_index)
                    
                    # Ако това е клиент в център зоната
                    if to_node >= len(self.unique_depots):
                        customer_index = to_node - len(self.unique_depots)
                        customer = self.customers[customer_index]
                        
                        # Проверяваме дали клиентът е в център зоната
                        if customer.coordinates and self.location_config:
                            distance_to_center = calculate_distance_km(
                                customer.coordinates, 
                                self.location_config.center_location
                            )
                            if distance_to_center <= self.location_config.center_zone_radius_km:
                                # Увеличаваме разходите за EXTERNAL_BUS с конфигурируем множител
                                multiplier = self.location_config.external_bus_center_penalty if self.location_config else 50000
                                return int(self.distance_matrix.distances[from_node][to_node] + multiplier)
                    
                    return int(self.distance_matrix.distances[from_node][to_node])
                
                # Регистрираме callback-а за EXTERNAL_BUS превозните средства
                external_bus_callback_index = routing.RegisterTransitCallback(external_bus_penalty_callback)
                
                for vehicle_id in data['external_bus_vehicle_ids']:
                    routing.SetArcCostEvaluatorOfVehicle(external_bus_callback_index, vehicle_id)
            
            # 7. ГЛОБА ЗА INTERNAL_BUS ЗА ВЛИЗАНЕ В ЦЕНТЪРА
            if data['internal_bus_vehicle_ids'] and self.location_config and self.location_config.enable_center_zone_restrictions:
                logger.info("⚠️ Прилагане на глоба за INTERNAL_BUS в център зоната")
                
                # Създаваме callback за глоба на INTERNAL_BUS
                def internal_bus_penalty_callback(from_index, to_index):
                    from_node = manager.IndexToNode(from_index)
                    to_node = manager.IndexToNode(to_index)
                    
                    # Ако това е клиент в център зоната
                    if to_node >= len(self.unique_depots):
                        customer_index = to_node - len(self.unique_depots)
                        customer = self.customers[customer_index]
                        
                        # Проверяваме дали клиентът е в център зоната
                        if customer.coordinates and self.location_config:
                            distance_to_center = calculate_distance_km(
                                customer.coordinates, 
                                self.location_config.center_location
                            )
                            if distance_to_center <= self.location_config.center_zone_radius_km:
                                # Увеличаваме разходите за INTERNAL_BUS с конфигурируем множител
                                multiplier = self.location_config.internal_bus_center_penalty if self.location_config else 50000
                                return int(self.distance_matrix.distances[from_node][to_node] + multiplier)
                    
                    return int(self.distance_matrix.distances[from_node][to_node])
                
                # Регистрираме callback-а за INTERNAL_BUS превозните средства
                internal_bus_callback_index = routing.RegisterTransitCallback(internal_bus_penalty_callback)
                
                for vehicle_id in data['internal_bus_vehicle_ids']:
                    routing.SetArcCostEvaluatorOfVehicle(internal_bus_callback_index, vehicle_id)
                    
            # 8. ГЛОБА ЗА SPECIAL_BUS ЗА ВЛИЗАНЕ В ЦЕНТЪРА
            if data['special_bus_vehicle_ids'] and self.location_config and self.location_config.enable_center_zone_restrictions:
                logger.info("🔶 Прилагане на глоба за SPECIAL_BUS в център зоната")
                
                # Създаваме callback за глоба на SPECIAL_BUS
                def special_bus_penalty_callback(from_index, to_index):
                    from_node = manager.IndexToNode(from_index)
                    to_node = manager.IndexToNode(to_index)
                    
                    # Ако това е клиент в център зоната
                    if to_node >= len(self.unique_depots):
                        customer_index = to_node - len(self.unique_depots)
                        customer = self.customers[customer_index]
                        
                        # Проверяваме дали клиентът е в център зоната
                        if customer.coordinates and self.location_config:
                            distance_to_center = calculate_distance_km(
                                customer.coordinates, 
                                self.location_config.center_location
                            )
                            if distance_to_center <= self.location_config.center_zone_radius_km:
                                # Увеличаваме разходите за SPECIAL_BUS с конфигурируем множител
                                multiplier = self.location_config.special_bus_center_penalty if self.location_config else 50000
                                return int(self.distance_matrix.distances[from_node][to_node] + multiplier)
                    
                    return int(self.distance_matrix.distances[from_node][to_node])
                
                # Регистрираме callback-а за SPECIAL_BUS превозните средства
                special_bus_callback_index = routing.RegisterTransitCallback(special_bus_penalty_callback)
                
                for vehicle_id in data['special_bus_vehicle_ids']:
                    routing.SetArcCostEvaluatorOfVehicle(special_bus_callback_index, vehicle_id)
            
            # 8.1. ГЛОБА ЗА VRATZA_BUS ЗА ВЛИЗАНЕ В ЦЕНТЪРА
            if data['vratza_bus_vehicle_ids'] and self.location_config and self.location_config.enable_center_zone_restrictions:
                logger.info("🚫 Прилагане на глоба за VRATZA_BUS в център зоната")
                
                # Създаваме callback за глоба на VRATZA_BUS
                def vratza_bus_penalty_callback(from_index, to_index):
                    from_node = manager.IndexToNode(from_index)
                    to_node = manager.IndexToNode(to_index)
                    
                    # Ако това е клиент в център зоната
                    if to_node >= len(self.unique_depots):
                        customer_index = to_node - len(self.unique_depots)
                        customer = self.customers[customer_index]
                        
                        # Проверяваме дали клиентът е в център зоната
                        if customer.coordinates and self.location_config:
                            distance_to_center = calculate_distance_km(
                                customer.coordinates, 
                                self.location_config.center_location
                            )
                            if distance_to_center <= self.location_config.center_zone_radius_km:
                                # Увеличаваме разходите за VRATZA_BUS с конфигурируем множител
                                multiplier = self.location_config.vratza_bus_center_penalty if self.location_config else 100000
                                return int(self.distance_matrix.distances[from_node][to_node] + multiplier)
                    
                    return int(self.distance_matrix.distances[from_node][to_node])
                
                # Регистрираме callback-а за VRATZA_BUS превозните средства
                vratza_bus_callback_index = routing.RegisterTransitCallback(vratza_bus_penalty_callback)
                
                for vehicle_id in data['vratza_bus_vehicle_ids']:
                    routing.SetArcCostEvaluatorOfVehicle(vratza_bus_callback_index, vehicle_id)
            
            # 9. ПАРАМЕТРИ НА ТЪРСЕНЕ (Стандартни)
            logger.info("Използват се стандартни параметри за търсене.")
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            # Устойчиво мапване на низови стратегии към enum (guard за непознати стойности)
            try:
                fs_value = str(self.config.first_solution_strategy)
                first_solution_enum = getattr(
                    routing_enums_pb2.FirstSolutionStrategy,
                    fs_value,
                    routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC,
                )
                search_parameters.first_solution_strategy = first_solution_enum
            except Exception:
                search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC

            try:
                ls_value = str(self.config.local_search_metaheuristic)
                local_search_enum = getattr(
                    routing_enums_pb2.LocalSearchMetaheuristic,
                    ls_value,
                    routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC,
                )
                search_parameters.local_search_metaheuristic = local_search_enum
            except Exception:
                search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC
            search_parameters.time_limit.seconds = self.config.time_limit_seconds
            search_parameters.log_search = self.config.log_search
            search_parameters.use_full_propagation = self.config.use_full_propagation
            search_parameters.guided_local_search_lambda_coefficient = self.config.search_lambda_coefficient
            
            # Добавяме LNS time limit за по-добър контрол на търсенето
            if hasattr(self.config, 'lns_time_limit_seconds'):
                search_parameters.lns_time_limit.seconds = self.config.lns_time_limit_seconds
            
            # Добавяме LNS neighborhood параметри за по-добър контрол
            if hasattr(self.config, 'lns_num_nodes'):
                search_parameters.heuristic_close_nodes_lns_num_nodes = self.config.lns_num_nodes
            if hasattr(self.config, 'lns_num_arcs'):
                search_parameters.heuristic_expensive_chain_lns_num_arcs_to_consider = self.config.lns_num_arcs

            # 10. РЕШАВАНЕ
            logger.info(f"🚀 Стартирам решаване с пълни ограничения (времеви лимит: {self.config.time_limit_seconds}s)...")
            solution = routing.SolveWithParameters(search_parameters)
            
            # 11. ОБРАБОТКА НА РЕШЕНИЕТО
            if solution:
                return self._extract_solution(manager, routing, solution, data)
            else:
                logger.error("❌ OR-Tools не намери решение!")
                return self._create_empty_solution()
                
        except Exception as e:
            logger.error(f"❌ Грешка в OR-Tools solver: {e}", exc_info=True)
            return self._create_empty_solution()

    def _create_data_model(self):
        """
        Изцяло пренаписана функция, за да се гарантира, че ЧЕТИРИТЕ твърди ограничения
        (Обем, Разстояние, Брой клиенти, Време) се четат и прилагат СТРИКТНО
        от конфигурационния файл, без грешки или своеволия.
        """
        logger.info("--- СЪЗДАВАНЕ НА DATA MODEL (СТРИКТЕН РЕЖИМ) ---")
        data = {}
        data['distance_matrix'] = self.distance_matrix.distances
        data['demands'] = [0] * len(self.unique_depots) + [int(c.volume * 100) for c in self.customers]
        
        # Създаваме vehicle-specific service times
        # За депата service time е 0
        service_times = [0] * len(self.unique_depots)
        
        # За клиентите, не използваме средна стойност!
        # Ще използваме vehicle-specific service times в callback-а
        enabled_vehicles = [v for v in self.vehicle_configs if v.enabled]
        if enabled_vehicles:
            logger.info(f"📊 Vehicle-specific service times:")
            logger.info(f"  - INTERNAL_BUS: {next((v.service_time_minutes for v in enabled_vehicles if v.vehicle_type == VehicleType.INTERNAL_BUS), 8)} мин")
            logger.info(f"  - CENTER_BUS: {next((v.service_time_minutes for v in enabled_vehicles if v.vehicle_type == VehicleType.CENTER_BUS), 9)} мин")
            logger.info(f"  - EXTERNAL_BUS: {next((v.service_time_minutes for v in enabled_vehicles if v.vehicle_type == VehicleType.EXTERNAL_BUS), 6)} мин")
            logger.info(f"  - SPECIAL_BUS: {next((v.service_time_minutes for v in enabled_vehicles if v.vehicle_type == VehicleType.SPECIAL_BUS), 6)} мин")
            logger.info(f"  - VRATZA_BUS: {next((v.service_time_minutes for v in enabled_vehicles if v.vehicle_type == VehicleType.VRATZA_BUS), 7)} мин")
        
        # За клиентите използваме 0 - service time ще се изчислява в callback-а
        data['service_times'] = service_times + [0] * len(self.customers)
        
        # Създаваме mapping от vehicle_id към service_time
        vehicle_service_times = {}
        vehicle_id = 0
        for v_config in self.vehicle_configs:
            if v_config.enabled:
                for _ in range(v_config.count):
                    vehicle_service_times[vehicle_id] = v_config.service_time_minutes * 60  # в секунди
                    vehicle_id += 1
        
        data['vehicle_service_times'] = vehicle_service_times

        data['num_vehicles'] = sum(v.count for v in self.vehicle_configs if v.enabled)
        logger.info(f"  - Общо превозни средства: {data['num_vehicles']}")
        logger.info(f"  - Vehicle service times mapping: {[(k, v/60) for k, v in vehicle_service_times.items()]}")
        data['depot_indices'] = list(range(len(self.unique_depots)))

        vehicle_capacities = []
        vehicle_max_distances = []
        vehicle_max_stops = []
        vehicle_max_times = []
        vehicle_starts = []
        vehicle_ends = []
        
        logger.info("  - Зареждане на твърди ограничения от конфигурацията...")
        
        # Идентифицираме CENTER_BUS превозните средства
        center_bus_vehicle_ids = []
        external_bus_vehicle_ids = []
        internal_bus_vehicle_ids = []
        special_bus_vehicle_ids = []
        vratza_bus_vehicle_ids = []
        vehicle_id = 0
        
        logger.info("  - Настройка на депа за превозните средства:")
        
        for v_config in self.vehicle_configs:
            if v_config.enabled:
                depot_index = self._get_depot_index_for_vehicle(v_config)
                depot_location = self.unique_depots[depot_index]
                
                logger.info(f"    {v_config.vehicle_type.value}: депо {depot_index} ({depot_location})")
                
                for i in range(v_config.count):
                    # Записваме ID-тата на CENTER_BUS превозните средства
                    # Използваме value сравнение вместо директно сравнение на enum-и
                    if v_config.vehicle_type.value == VehicleType.CENTER_BUS.value:
                        center_bus_vehicle_ids.append(vehicle_id)
                    elif v_config.vehicle_type.value == VehicleType.EXTERNAL_BUS.value:
                        external_bus_vehicle_ids.append(vehicle_id)
                    elif v_config.vehicle_type.value == VehicleType.INTERNAL_BUS.value:
                        internal_bus_vehicle_ids.append(vehicle_id)
                    elif v_config.vehicle_type.value == VehicleType.SPECIAL_BUS.value:
                        special_bus_vehicle_ids.append(vehicle_id)
                    elif v_config.vehicle_type.value == VehicleType.VRATZA_BUS.value:
                        vratza_bus_vehicle_ids.append(vehicle_id)
                    
                    # 1. Обем (Capacity) - стриктно
                    vehicle_capacities.append(int(v_config.capacity * 100))
                    
                    # 2. Разстояние (Distance) - стриктно
                    max_dist = int(v_config.max_distance_km * 1000) if v_config.max_distance_km else 999999999
                    vehicle_max_distances.append(max_dist)
                    
                    # 3. Брой клиенти (Stops) - стриктно
                    max_stops = v_config.max_customers_per_route if v_config.max_customers_per_route is not None else len(self.customers) + 1
                    vehicle_max_stops.append(max_stops)

                    # 4. Време (Time) - стриктно
                    vehicle_max_times.append(int(v_config.max_time_hours * 3600))
                    
                    vehicle_starts.append(depot_index)
                    vehicle_ends.append(depot_index)
                    vehicle_id += 1
        
        data['vehicle_capacities'] = vehicle_capacities
        data['vehicle_max_distances'] = vehicle_max_distances
        data['vehicle_max_stops'] = vehicle_max_stops
        data['vehicle_max_times'] = vehicle_max_times
        data['vehicle_starts'] = vehicle_starts
        data['vehicle_ends'] = vehicle_ends
        data['depot'] = 0 
        data['center_bus_vehicle_ids'] = center_bus_vehicle_ids
        data['external_bus_vehicle_ids'] = external_bus_vehicle_ids
        data['internal_bus_vehicle_ids'] = internal_bus_vehicle_ids
        data['special_bus_vehicle_ids'] = special_bus_vehicle_ids
        data['vratza_bus_vehicle_ids'] = vratza_bus_vehicle_ids
        
        logger.info(f"  - Капацитети: {data['vehicle_capacities']}")
        logger.info(f"  - Макс. разстояния (м): {data['vehicle_max_distances']}")
        logger.info(f"  - Макс. спирки: {data['vehicle_max_stops']}")
        logger.info(f"  - Макс. времена (сек): {data['vehicle_max_times']}")
        logger.info(f"  - CENTER_BUS превозни средства: {center_bus_vehicle_ids}")
        logger.info(f"  - EXTERNAL_BUS превозни средства: {external_bus_vehicle_ids}")
        logger.info(f"  - INTERNAL_BUS превозни средства: {internal_bus_vehicle_ids}")
        logger.info(f"  - SPECIAL_BUS превозни средства: {special_bus_vehicle_ids}")
        logger.info(f"  - VRATZA_BUS превозни средства: {vratza_bus_vehicle_ids}")
        logger.info(f"  - Service time за клиенти: {data['service_times'][len(self.unique_depots)]/60:.1f} мин")
        logger.info("--- DATA MODEL СЪЗДАДЕН ---")
        return data

    def _get_depot_index_for_vehicle(self, vehicle_config: VehicleConfig) -> int:
        """
        Намира индекса на депото в `unique_depots` за даденото превозно средство.

        Prefers `start_location` ако е подаденa и съществува; иначе връща главното депо (0).

        Returns:
            Индекс на депо (int).
        """
        if vehicle_config.start_location and vehicle_config.start_location in self.unique_depots:
            return self.unique_depots.index(vehicle_config.start_location)
        # Връщаме основното депо по подразбиране
        return 0

    def _calculate_accurate_route_time(self, customers: List[Customer], depot_location: Tuple[float, float], vehicle_config: VehicleConfig) -> float:
        """
        Изчислява точното време за маршрут с vehicle-specific service time.

        Args:
            customers: Списък с клиенти в маршрута.
            depot_location: Локация на депото.
            vehicle_config: Конфигурация на превозното средство.

        Returns:
            Общо време в секунди.
        """
        if not customers:
            return 0.0
        
        total_time = 0.0
        
        # Намираме индекса на депото в матрицата
        depot_index = None
        for i, depot in enumerate(self.unique_depots):
            if depot == depot_location:
                depot_index = i
                break
        
        if depot_index is None:
            logger.warning(f"⚠️ Депо {depot_location} не е намерено, използвам главното депо")
            depot_index = 0
        
        # Service time в секунди за този тип бус
        service_time_seconds = vehicle_config.service_time_minutes * 60
        
        # === ГРАДСКИ ТРАФИК: Настройки и определяне кои локации са в града ===
        enable_city_traffic = False
        city_traffic_multiplier = 1.0
        city_center = None
        city_radius = 0
        
        if self.location_config:
            enable_city_traffic = getattr(self.location_config, 'enable_city_traffic_adjustment', False)
            city_traffic_multiplier = getattr(self.location_config, 'city_traffic_duration_multiplier', 1.0)
            city_center = getattr(self.location_config, 'city_center_coords', None)
            city_radius = getattr(self.location_config, 'city_traffic_radius_km', 12.0)
        
        # Предварително определяме кои локации са в градската зона
        num_locations = len(self.distance_matrix.distances)
        locations_in_city = []
        for loc_idx in range(num_locations):
            if loc_idx < len(self.unique_depots):
                lat, lon = self.unique_depots[loc_idx]
            else:
                client_idx = loc_idx - len(self.unique_depots)
                if client_idx < len(self.customers):
                    lat, lon = self.customers[client_idx].coordinates or (0, 0)
                else:
                    lat, lon = 0, 0
            
            in_city = False
            if enable_city_traffic and city_center:
                dist_to_city_center = calculate_distance_km((lat, lon), city_center)
                in_city = dist_to_city_center <= city_radius
            locations_in_city.append(in_city)
        
        # От депо до първия клиент
        current_node = depot_index
        for customer in customers:
            # Намираме индекса на клиента в матрицата
            try:
                customer_index = len(self.unique_depots) + self._get_customer_index_by_id(customer.id)
            except ValueError:
                logger.warning(f"⚠️ Клиент {customer.id} не е намерен в customers списъка")
                continue
            
            # Travel time от текущия node до клиента с трафик корекция
            travel_time = self.distance_matrix.durations[current_node][customer_index]
            if enable_city_traffic and current_node < len(locations_in_city) and customer_index < len(locations_in_city):
                if locations_in_city[current_node] and locations_in_city[customer_index]:
                    travel_time = travel_time * city_traffic_multiplier
            total_time += travel_time
            
            # Service time за клиента (само за клиенти, не за депо)
            total_time += service_time_seconds
            
            current_node = customer_index
        
        # От последния клиент обратно в депото с трафик корекция
        travel_time_back = self.distance_matrix.durations[current_node][depot_index]
        if enable_city_traffic and current_node < len(locations_in_city) and depot_index < len(locations_in_city):
            if locations_in_city[current_node] and locations_in_city[depot_index]:
                travel_time_back = travel_time_back * city_traffic_multiplier
        total_time += travel_time_back
        
        logger.debug(f"🕐 {vehicle_config.vehicle_type.value} accurate time: "
                    f"{len(customers)} клиента × {vehicle_config.service_time_minutes}мин + travel = "
                    f"{total_time/60:.1f} минути")
        
        return total_time

    def _extract_solution(self, manager, routing, solution, data) -> CVRPSolution:
        """
        Извлича OR-Tools решение към вътрешния формат `CVRPSolution`.

        Обхожда маршрути по превозни средства, събира клиенти, изчислява разстояния и времена
        чрез Time dimension и матрицата, и връща агрегирани метрики.
        """
        logger.info("--- ИЗВЛИЧАНЕ НА РЕШЕНИЕ ---")
        start_time = time.time()
        
        # Директно взимаме "времевото измерение" от солвъра.
        # Това е "източникът на истината" за времето.
        time_dimension = routing.GetDimensionOrDie("Time")
        
        routes = []
        total_distance = 0
        total_time_seconds = 0
        
        num_depots = len(self.unique_depots)
        all_serviced_customer_indices = set()
        
        for vehicle_id in range(routing.vehicles()):
            route_customers = []
            route_distance = 0
            
            # Определяме кое е депото за този vehicle според data model
            vehicle_config = self._get_vehicle_config_for_id(vehicle_id)
            
            # Вземаме депото директно от решението на OR-Tools
            start_node = manager.IndexToNode(routing.Start(vehicle_id))
            
            if start_node >= num_depots:
                # Това не би трябвало да се случва, тъй като всички маршрути трябва да започват от депо.
                # Но за всеки случай, логваме и пропускаме този автобус.
                logger.error(f"❌ Грешка: Автобус {vehicle_id} започва от клиент (node {start_node}), а не от депо. Маршрутът се игнорира.")
                continue

            depot_location = self.unique_depots[start_node]
            
            logger.info(f"Extracting route for vehicle {vehicle_id}")

            index = routing.Start(vehicle_id)
            max_iterations = len(self.customers) + 10  # Максимум итерации: брой клиенти + малко запас
            iteration_count = 0

            while not routing.IsEnd(index):
                iteration_count += 1
                if iteration_count > max_iterations:
                    logger.error(f"❌ Безкраен цикъл открит при извличане на маршрут за vehicle {vehicle_id}. Прекратявам.")
                    break

                node_index = manager.IndexToNode(index)
                # Проверяваме дали това е клиент (не депо)
                if node_index >= num_depots:  # Клиентите са след депата в матрицата
                    # Customer index е node_index - брой депа
                    customer_index = node_index - num_depots
                    if 0 <= customer_index < len(self.customers):
                        customer = self.customers[customer_index]
                        route_customers.append(customer)
                        all_serviced_customer_indices.add(customer_index)
                
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                
                # Вземаме действителните разстояния от матрицата
                from_node = manager.IndexToNode(previous_index)
                to_node = manager.IndexToNode(index)
                actual_distance = self.distance_matrix.distances[from_node][to_node]
                
                route_distance += actual_distance
            
            if route_customers:
                # КЛЮЧОВА ПРОМЯНА: Взимаме времето директно от решението на солвъра.
                # Това гарантира 100% консистентност между оптимизация и отчет.
                route_end_index = routing.End(vehicle_id)
                ortools_time_seconds = solution.Value(time_dimension.CumulVar(route_end_index))

                # НОВА ФУНКЦИОНАЛНОСТ: Изчисляваме точното време с vehicle-specific service time
                accurate_time_seconds = self._calculate_accurate_route_time(
                    route_customers, depot_location, vehicle_config
                )
                
                # Логваме разликата за дебъг
                time_diff = abs(ortools_time_seconds - accurate_time_seconds)
                if time_diff > 60:  # Повече от 1 минута разлика
                    logger.info(f"🕐 Vehicle {vehicle_id} ({vehicle_config.vehicle_type.value}) time comparison:")
                    logger.info(f"  - OR-Tools time: {ortools_time_seconds/60:.1f} мин (средни service times)")
                    logger.info(f"  - Accurate time: {accurate_time_seconds/60:.1f} мин (specific service time: {vehicle_config.service_time_minutes} мин/клиент)")
                    logger.info(f"  - Разлика: {time_diff/60:.1f} минути")

                route = Route(
                    vehicle_type=vehicle_config.vehicle_type,
                    vehicle_id=vehicle_id,
                    customers=route_customers,
                    depot_location=depot_location,
                    total_distance_km=route_distance / 1000,
                    total_time_minutes=accurate_time_seconds / 60,  # Използваме точното време!
                    total_volume=sum(c.volume for c in route_customers),
                    is_feasible=True
                )
                
                # Връщаме валидациите, за да сме сигурни, че решението спазва правилата
                if (vehicle_config.max_distance_km and 
                    route.total_distance_km > vehicle_config.max_distance_km):
                    logger.warning(f"⚠️ Автобус {vehicle_id} ({vehicle_config.vehicle_type.value}) "
                                  f"надвишава distance лимит: {route.total_distance_km:.1f}км > "
                                  f"{vehicle_config.max_distance_km}км")
                    route.is_feasible = False
                
                if route.total_volume > vehicle_config.capacity:
                    logger.warning(f"⚠️ Автобус {vehicle_id} ({vehicle_config.vehicle_type.value}) "
                                  f"надвишава capacity лимит: {route.total_volume:.1f}ст > "
                                  f"{vehicle_config.capacity}ст")
                    route.is_feasible = False

                if (vehicle_config.max_customers_per_route and
                    len(route.customers) > vehicle_config.max_customers_per_route):
                     logger.warning(f"⚠️ Автобус {vehicle_id} ({vehicle_config.vehicle_type.value}) "
                                   f"надвишава лимита за клиенти: {len(route.customers)} > "
                                   f"{vehicle_config.max_customers_per_route}")
                     route.is_feasible = False

                if route.total_time_minutes > (vehicle_config.max_time_hours * 60) + 1: # +1 за закръгления
                    logger.warning(f"⚠️ Автобус {vehicle_id} ({vehicle_config.vehicle_type.value}) "
                                  f"надвишава time лимит: {route.total_time_minutes:.1f}мин > "
                                  f"{vehicle_config.max_time_hours * 60}мин")
                    route.is_feasible = False
                
                routes.append(route)
                total_distance += route_distance
                total_time_seconds += accurate_time_seconds
        
        logger.info(f"  - Извличане на маршрути отне: {time.time() - start_time:.2f} сек.")
        
        # НОВА ФУНКЦИОНАЛНОСТ: Финален реконфигурация на маршрутите от депото
        if self.config.enable_final_depot_reconfiguration:
            logger.info("🔄 Прилагане на финална реконфигурация на маршрутите от депото...")
            routes = self._reconfigure_routes_from_depot(routes)
        else:
            logger.info("⏭️ Пропускане на финална реконфигурация (изключена в конфигурацията)")
        
        # Намираме пропуснатите клиенти
        start_dropped_time = time.time()
        all_customer_indices = set(range(len(self.customers)))
        dropped_customer_indices = all_customer_indices - all_serviced_customer_indices
        dropped_customers = [self.customers[i] for i in dropped_customer_indices]
        
        if dropped_customers:
            logger.warning(f"⚠️ OR-Tools пропусна {len(dropped_customers)} клиента, за да намери решение:")
            # Сортираме по обем за по-ясно представяне
            dropped_customers.sort(key=lambda c: c.volume, reverse=True)
            for cust in dropped_customers[:10]: # показваме първите 10
                logger.warning(f"   - Пропуснат: {cust.name} (обем: {cust.volume:.1f} ст.)")
            if len(dropped_customers) > 10:
                logger.warning(f"   - ... и още {len(dropped_customers) - 10}")
        
        logger.info(f"  - Обработка на пропуснати клиенти отне: {time.time() - start_dropped_time:.2f} сек.")

        # ПРЕИЗЧИСЛЯВАМЕ общите стойности СЛЕД TSP оптимизацията
        total_served_volume = sum(r.total_volume for r in routes)
        total_distance_km = sum(r.total_distance_km for r in routes)
        total_time_minutes = sum(r.total_time_minutes for r in routes)

        cvrp_solution = CVRPSolution(
            routes=routes,
            dropped_customers=dropped_customers,
            total_distance_km=total_distance_km,  # ← СЛЕД TSP оптимизацията!
            total_time_minutes=total_time_minutes,  # ← СЛЕД TSP оптимизацията!
            total_vehicles_used=len(routes),
            fitness_score=float(solution.ObjectiveValue()),
            is_feasible=True, # Ще се обнови по-долу
            total_served_volume=total_served_volume
        )
        
        # Проверка на общата валидност на решението
        invalid_routes = [r for r in routes if not r.is_feasible]
        is_solution_feasible = not invalid_routes and not dropped_customers
        cvrp_solution.is_feasible = is_solution_feasible
        
        logger.info(f"--- РЕШЕНИЕТО ИЗВЛЕЧЕНО ({time.time() - start_time:.2f} сек.) ---")
        return cvrp_solution

    def _get_customer_index_by_id(self, customer_id: str) -> int:
        """Намира индекса на клиент по ID"""
        for i, customer in enumerate(self.customers):
            if customer.id == customer_id:
                return i
        raise ValueError(f"Клиент с ID {customer_id} не е намерен")
    
    def _get_vehicle_config_for_id(self, vehicle_id: int) -> VehicleConfig:
        """Намира конфигурацията за превозно средство по ID"""
        current_id = 0
        for vehicle_config in self.vehicle_configs:
            if not vehicle_config.enabled:
                continue
            if current_id <= vehicle_id < current_id + vehicle_config.count:
                return vehicle_config
            current_id += vehicle_config.count
        
        # Fallback към първото включено превозно средство
        for vehicle_config in self.vehicle_configs:
            if vehicle_config.enabled:
                return vehicle_config
        
        raise ValueError("Няма включени превозни средства")
    
    def _create_empty_solution(self) -> CVRPSolution:
        """Създава празно решение в случай на грешка."""
        return CVRPSolution(routes=[], dropped_customers=[], total_distance_km=0,
                            total_time_minutes=0, total_vehicles_used=0,
                            fitness_score=float('inf'), is_feasible=False, total_served_volume=0)

    def _reconfigure_routes_from_depot(self, routes: List[Route]) -> List[Route]:
        """
        Реконфигурира всички маршрути да започват от депото.
        Това е финална стъпка след като OR-Tools намери решение.
        """
        logger.info("🔄 Реконфигуриране на маршрутите от депото...")
        
        reconfigured_routes = []
        
        for route in routes:
            if not route.customers:
                continue
                
            # Намираме vehicle_config за този маршрут
            vehicle_config = self._get_vehicle_config_for_id(route.vehicle_id)
            
            # Определяме TSP депото за този тип превозно средство
            tsp_depot = vehicle_config.tsp_depot_location
            if not tsp_depot:
                # Ако няма TSP депо, използваме start_location
                tsp_depot = vehicle_config.start_location
            if not tsp_depot:
                # Ако няма и start_location, използваме главното депо
                tsp_depot = self.unique_depots[0]
            
            logger.info(f"🏢 TSP депо за {vehicle_config.vehicle_type.value}: {tsp_depot}")
                
            # НОВА ЛОГИКА: Преизчисляваме оптималния ред на клиентите от TSP депото
            optimized_customers = self._optimize_route_from_depot(route.customers, tsp_depot, vehicle_config)
            
            # Изчисляваме новите разстояния и времена от TSP депото
            new_distance_km, new_time_minutes = self._calculate_route_from_depot(
                optimized_customers, tsp_depot, vehicle_config
            )
            
            # Създаваме нов маршрут с TSP депото като стартова точка и оптимизиран ред
            reconfigured_route = Route(
                vehicle_type=route.vehicle_type,
                vehicle_id=route.vehicle_id,
                customers=optimized_customers,  # ОПТИМИЗИРАН ред на клиентите
                depot_location=tsp_depot,  # TSP депото за този тип автобус
                total_distance_km=new_distance_km,
                total_time_minutes=new_time_minutes,
                total_volume=sum(c.volume for c in optimized_customers),
                is_feasible=True
            )
            
            # Валидираме новия маршрут
            vehicle_config = self._get_vehicle_config_for_id(route.vehicle_id)
            
            # Сравняваме оригиналните и новите стойности
            logger.info(f"📊 Сравнение за маршрут {route.vehicle_id} ({vehicle_config.vehicle_type.value}):")
            logger.info(f"  - Оригинално: {route.total_distance_km:.1f}км, {route.total_time_minutes:.1f}мин")
            logger.info(f"  - От депото: {new_distance_km:.1f}км, {new_time_minutes:.1f}мин")
            logger.info(f"  - Разлика: +{new_distance_km - route.total_distance_km:.1f}км, +{new_time_minutes - route.total_time_minutes:.1f}мин")
            
            if not self._validate_reconfigured_route(reconfigured_route, vehicle_config):
                logger.warning(f"⚠️ Реконфигуриран маршрут {route.vehicle_id} НЕ спазва ограниченията!")
                reconfigured_route.is_feasible = False
            else:
                logger.info(f"✅ Реконфигуриран маршрут {route.vehicle_id} спазва ограниченията")
            
            reconfigured_routes.append(reconfigured_route)
        
        logger.info(f"✅ Реконфигурирани {len(reconfigured_routes)} маршрута от депото")
        return reconfigured_routes
    
    def _optimize_route_from_depot(self, customers: List[Customer], depot_location: Tuple[float, float], vehicle_config: VehicleConfig = None) -> List[Customer]:
        """
        Оптимизира реда на клиентите, започвайки от зададеното депо.
        Използва OR-Tools TSP solver за намиране на оптималния маршрут.
        НЕ спазва ограничения - само оптимизира разстоянието.
        Депото се определя от vehicle_config.tsp_depot_location или се подава като параметър.
        """
        if not customers:
            return []
        
        if not ORTOOLS_AVAILABLE:
            logger.warning("⚠️ OR-Tools не е наличен, използвам greedy алгоритъм")
            return self._optimize_route_greedy(customers, depot_location)
        
        try:
            # Филтрираме клиентите с валидни координати
            valid_customers = [c for c in customers if c.coordinates is not None]
            if len(valid_customers) != len(customers):
                logger.warning(f"⚠️ {len(customers) - len(valid_customers)} клиенти без валидни координати")
            
            if not valid_customers:
                logger.warning("⚠️ Няма клиенти с валидни координати за TSP")
                return []
            
            # Използваме подаденото депо за TSP
            tsp_depot = depot_location
            logger.info(f"🎯 TSP оптимизация от депо: {tsp_depot}")
            
            # Създаваме опростен TSP проблем - само координати
            locations = [tsp_depot] + [customer.coordinates for customer in valid_customers]
            num_locations = len(locations)
            
            # Създаваме проста distance matrix с Euclidean разстояния
            distance_matrix = []
            for i in range(num_locations):
                row = []
                for j in range(num_locations):
                    if i == j:
                        row.append(0)
                    else:
                        # Използваме Euclidean разстояние за TSP
                        dist = calculate_distance_km(locations[i], locations[j])
                        row.append(int(dist * 1000))  # Конвертираме в метри за OR-Tools
                distance_matrix.append(row)
            
            # Решаваме TSP с OR-Tools (без ограничения)
            manager = pywrapcp.RoutingIndexManager(num_locations, 1, 0)  # 1 vehicle, depot at index 0
            routing = pywrapcp.RoutingModel(manager)
            
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return distance_matrix[from_node][to_node]
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            
            # Настройки за търсене - бързи и ефективни за TSP
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC)  # Бърз greedy
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC)  # Прост local search
            search_parameters.time_limit.seconds = 10  # Кратък лимит за TSP
            search_parameters.log_search = True  # Без лог за TSP
            
            # Решаваме TSP
            solution = routing.SolveWithParameters(search_parameters)
            
            if solution:
                # Извличаме оптималния маршрут
                index = routing.Start(0)
                route_indices = []
                
                while not routing.IsEnd(index):
                    route_indices.append(manager.IndexToNode(index))
                    index = solution.Value(routing.NextVar(index))
                route_indices.append(manager.IndexToNode(index))
                
                # Преобразуваме индексите обратно в клиенти (пропускаме депото)
                optimized_customers = []
                for i in route_indices[1:-1]:  # Пропускаме първото и последното депо
                    optimized_customers.append(valid_customers[i-1])  # i-1 защото депото е на индекс 0
                
                logger.info(f"🎯 TSP оптимизиран маршрут: {[c.name for c in optimized_customers]}")
                logger.info(f"📏 TSP общо разстояние: {solution.ObjectiveValue()/1000:.1f}км")
                return optimized_customers
            else:
                logger.warning("⚠️ TSP не намери решение, използвам greedy алгоритъм")
                return self._optimize_route_greedy(customers, depot_location)
                
        except Exception as e:
            logger.error(f"❌ Грешка при TSP оптимизация: {e}")
            logger.info("🔄 Използвам greedy алгоритъм като fallback")
            return self._optimize_route_greedy(customers, depot_location)
    
    def _optimize_route_greedy(self, customers: List[Customer], depot_location: Tuple[float, float]) -> List[Customer]:
        """
        Greedy алгоритъм като fallback за TSP.
        """
        if not customers:
            return []
        
        # Намираме индекса на депото в матрицата
        depot_index = 0  # Винаги индекс 0 е главното депо
        
        optimized_customers = []
        remaining_customers = customers.copy()
        current_node = depot_index
        
        while remaining_customers:
            # Намираме най-близкия клиент от текущия node
            min_distance = float('inf')
            closest_customer = None
            closest_index = -1
            
            for i, customer in enumerate(remaining_customers):
                # Намираме индекса на клиента в матрицата по ID
                customer_index = len(self.unique_depots) + self._get_customer_index_by_id(customer.id)
                
                # Разстояние от текущия node до клиента
                distance = self.distance_matrix.distances[current_node][customer_index]
                
                if distance < min_distance:
                    min_distance = distance
                    closest_customer = customer
                    closest_index = i
            
            if closest_customer:
                optimized_customers.append(closest_customer)
                remaining_customers.pop(closest_index)
                
                # Обновяваме текущия node
                customer_index = len(self.unique_depots) + self._get_customer_index_by_id(closest_customer.id)
                current_node = customer_index
        
        logger.info(f"🔄 Greedy оптимизиран ред на клиентите от депото: {[c.name for c in optimized_customers]}")
        return optimized_customers
    
    def _calculate_route_from_depot(self, customers: List[Customer], depot_location: Tuple[float, float], vehicle_config: VehicleConfig = None) -> Tuple[float, float]:
        """
        Изчислява разстояние и време за маршрут, започващ от депото.
        
        Args:
            customers: Списък с клиенти
            depot_location: Локация на депото
            vehicle_config: Конфигурация на превозното средство (за точен service time)
        """
        if not customers:
            return 0.0, 0.0
        
        total_distance = 0.0
        total_time = 0.0
        
        # Намираме индекса на депото в матрицата
        depot_index = None
        for i, depot in enumerate(self.unique_depots):
            if depot == depot_location:
                depot_index = i
                break
        
        if depot_index is None:
            logger.warning(f"⚠️ Депо {depot_location} не е намерено, използвам главното депо")
            depot_index = 0
        
        # Service time - използваме vehicle-specific ако е зададен
        if vehicle_config:
            service_time_seconds = vehicle_config.service_time_minutes * 60
            logger.debug(f"🕐 Използвам {vehicle_config.vehicle_type.value} service time: {vehicle_config.service_time_minutes} мин/клиент")
        else:
            # Fallback към средна стойност
            enabled_vehicles = [v for v in self.vehicle_configs if v.enabled]
            if enabled_vehicles:
                avg_service_time_minutes = sum(v.service_time_minutes for v in enabled_vehicles) / len(enabled_vehicles)
                service_time_seconds = avg_service_time_minutes * 60
                logger.debug(f"🕐 Използвам средна service time: {avg_service_time_minutes:.1f} мин/клиент")
            else:
                service_time_seconds = 15 * 60  # По подразбиране
        
        # От депо до първия клиент
        current_node = depot_index
        for customer in customers:
            # Намираме индекса на клиента в матрицата по ID
            customer_index = len(self.unique_depots) + self._get_customer_index_by_id(customer.id)
            
            # Разстояние и време от текущия node до клиента
            distance = self.distance_matrix.distances[current_node][customer_index]
            duration = self.distance_matrix.durations[current_node][customer_index]
            
            total_distance += distance
            total_time += duration
            
            # Време за обслужване на клиента (само за клиенти, не за депо)
            total_time += service_time_seconds
            
            current_node = customer_index
        
        # От последния клиент обратно в депото
        distance = self.distance_matrix.distances[current_node][depot_index]
        duration = self.distance_matrix.durations[current_node][depot_index]
        
        total_distance += distance
        total_time += duration
        
        logger.debug(f"  - Изчислено от депо {depot_index}: {total_distance/1000:.1f}км, {total_time/60:.1f}мин (service time: {service_time_seconds/60:.1f}мин/клиент)")
        return total_distance / 1000, total_time / 60  # в км и минути
    
    def _validate_reconfigured_route(self, route: Route, vehicle_config: VehicleConfig) -> bool:
        """
        Валидира реконфигуриран маршрут спрямо ограниченията.
        """
        logger.info(f"🔍 Валидация на реконфигуриран маршрут {route.vehicle_id} ({vehicle_config.vehicle_type.value}):")
        logger.info(f"  - Разстояние: {route.total_distance_km:.1f}км (лимит: {vehicle_config.max_distance_km}км)")
        logger.info(f"  - Време: {route.total_time_minutes:.1f}мин (лимит: {vehicle_config.max_time_hours * 60}мин)")
        logger.info(f"  - Обем: {route.total_volume:.1f}ст (лимит: {vehicle_config.capacity}ст)")
        logger.info(f"  - Клиенти: {len(route.customers)} (лимит: {vehicle_config.max_customers_per_route})")
        
        # Проверка на капацитета
        if route.total_volume > vehicle_config.capacity:
            logger.warning(f"⚠️ Реконфигуриран маршрут {route.vehicle_id} надвишава capacity лимит")
            return False
        
        # Проверка на времето
        if route.total_time_minutes > vehicle_config.max_time_hours * 60:
            logger.warning(f"⚠️ Реконфигуриран маршрут {route.vehicle_id} надвишава time лимит")
            return False
        
        # Проверка на разстоянието (ако има ограничение)
        if vehicle_config.max_distance_km and route.total_distance_km > vehicle_config.max_distance_km:
            logger.warning(f"⚠️ Реконфигуриран маршрут {route.vehicle_id} надвишава distance лимит")
            return False
        
        # Проверка на брой клиенти
        if (vehicle_config.max_customers_per_route and 
            len(route.customers) > vehicle_config.max_customers_per_route):
            logger.warning(f"⚠️ Реконфигуриран маршрут {route.vehicle_id} надвишава лимита за клиенти")
            return False
        
        logger.info(f"✅ Маршрут {route.vehicle_id} спазва всички ограничения")
        return True

    def solve_simple(self) -> CVRPSolution:
        """
        Опростено решение, което точно следва класическия OR-Tools пример.
        Само capacity constraints, без допълнителни ограничения.
        """
        if not ORTOOLS_AVAILABLE:
            logger.error("❌ OR-Tools не е инсталиран")
            return self._create_empty_solution()
        
        try:
            # 1. Създаване на data model (опростен) - точно като в примера
            logger.info("="*60)
            logger.info("🔍 СТЪПКА 1: СЪЗДАВАНЕ НА DATA MODEL (ОПРОСТЕН)")
            logger.info("="*60)
            
            data = self._create_simple_data_model()
            
            # Подробни логове за дебъгване
            logger.info(f"📊 Опростен CVRP solver конфигурация:")
            logger.info(f"  - Превозни средства: {data['num_vehicles']}")
            logger.info(f"  - Общо локации: {len(data['distance_matrix'])}")
            logger.info(f"  - Капацитети: {data['vehicle_capacities']}")
            logger.info(f"  - Общ капацитет: {sum(data['vehicle_capacities'])}")
            logger.info(f"  - Общо търсене: {sum(data['demands'])}")
            logger.info(f"  - Среден капацитет: {sum(data['vehicle_capacities']) / len(data['vehicle_capacities']):.2f}")
            logger.info(f"  - Депо индекс: {data['depot']}")
            
            # 2. Създаване на мениджър (single depot) - точно като в примера
            logger.info("="*60)
            logger.info("🔍 СТЪПКА 2: СЪЗДАВАНЕ НА ROUTING INDEX MANAGER")
            logger.info("="*60)
            
            manager = pywrapcp.RoutingIndexManager(
                len(data['distance_matrix']), 
                data['num_vehicles'], 
                data['depot']
            )
            
            logger.info(f"✓ Routing Index Manager създаден успешно")
            logger.info(f"  - Брой възли: {len(data['distance_matrix'])}")
            logger.info(f"  - Брой превозни средства: {data['num_vehicles']}")
            logger.info(f"  - Депо индекс: {data['depot']}")
            
            # 3. Създаване на routing model - точно като в примера
            logger.info("="*60)
            logger.info("🔍 СТЪПКА 3: СЪЗДАВАНЕ НА ROUTING MODEL")
            logger.info("="*60)
            
            routing = pywrapcp.RoutingModel(manager)
            logger.info(f"✓ Routing Model създаден успешно")
            
            # Добавяме възможност да се пропускат клиенти (ако е разрешено)
            if self.config.allow_customer_skipping:
                penalty = 10000000  # Много висока стойност
                logger.info(f"🔄 Добавяне на възможност за пропускане на клиенти с голяма глоба ({penalty})")
                for node in range(1, len(data['distance_matrix'])):
                    routing.AddDisjunction([manager.NodeToIndex(node)], penalty)
                logger.info("✅ Добавена възможност за пропускане на клиенти")
            else:
                logger.info("🚫 Пропускане на клиенти е ИЗКЛЮЧЕНО - ВСИЧКИ клиенти трябва да бъдат обслужени")
                logger.warning("⚠️ Ако няма достатъчно капацитет, solver-ът може да не намери решение!")

            # 4. Distance callback - точно като в примера
            logger.info("="*60)
            logger.info("🔍 СТЪПКА 4: СЪЗДАВАНЕ НА DISTANCE CALLBACK")
            logger.info("="*60)
            
            def distance_callback(from_index, to_index):
                """Връща разстоянието между две точки."""
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return data['distance_matrix'][from_node][to_node]
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            logger.info(f"✓ Distance callback регистриран с индекс: {transit_callback_index}")
            
            # Проверка на няколко примерни разстояния за дебъг
            sample_nodes = min(5, len(data['distance_matrix']))
            logger.info(f"📏 Примерни разстояния от матрицата:")
            for i in range(sample_nodes):
                for j in range(sample_nodes):
                    if i != j:
                        logger.info(f"  - От възел {i} до възел {j}: {data['distance_matrix'][i][j]}")
            
            # 5. Дефиниране на цената за всеки маршрут - точно като в примера
            logger.info("="*60)
            logger.info("🔍 СТЪПКА 5: ЗАДАВАНЕ НА ARC COST EVALUATOR")
            logger.info("="*60)
            
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            logger.info(f"✓ Arc cost evaluator зададен за всички превозни средства")

            # 6. Добавяне на ограничение за капацитет - точно като в примера
            logger.info("="*60)
            logger.info("🔍 СТЪПКА 6: ДОБАВЯНЕ НА ОГРАНИЧЕНИЕ ЗА КАПАЦИТЕТ")
            logger.info("="*60)
            
            def demand_callback(from_index):
                """Връща заявката на възела."""
                from_node = manager.IndexToNode(from_index)
                return data['demands'][from_node]
            
            demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
            logger.info(f"✓ Demand callback регистриран с индекс: {demand_callback_index}")
            
            # Показваме няколко примерни стойности за търсенето
            sample_nodes = min(5, len(data['demands']))
            logger.info(f"📦 Примерни стойности за търсенето:")
            for i in range(sample_nodes):
                logger.info(f"  - Възел {i}: търсене = {data['demands'][i]}")
                
            logger.info(f"Добавяне на измерение за капацитет...")
            routing.AddDimensionWithVehicleCapacity(
                demand_callback_index,
                0,  # null capacity slack
                data['vehicle_capacities'],  # vehicle maximum capacities
                True,  # start cumul to zero
                "Capacity"
            )
            logger.info(f"✓ Dimension за капацитет добавено успешно")

            # 7. Задаване на параметри за търсене - точно като в примера
            logger.info("="*60)
            logger.info("🔍 СТЪПКА 7: ЗАДАВАНЕ НА ПАРАМЕТРИ ЗА ТЪРСЕНЕ")
            logger.info("="*60)
            
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            # Избираме правилната първа стратегия за решение
            first_solution_strategy = getattr(
                routing_enums_pb2.FirstSolutionStrategy, 
                self.config.first_solution_strategy
            )
            search_parameters.first_solution_strategy = first_solution_strategy
            
            # Избираме правилната метаевристика
            local_search_metaheuristic = getattr(
                routing_enums_pb2.LocalSearchMetaheuristic,
                self.config.local_search_metaheuristic
            )
            search_parameters.local_search_metaheuristic = local_search_metaheuristic
            
            # Позволяваме по-голям времеви лимит за по-сложни проблеми
            time_limit = max(60, self.config.time_limit_seconds)
            search_parameters.time_limit.seconds = time_limit
            
            # Разрешаваме лог на търсенето
            search_parameters.log_search = self.config.log_search
            
            # Добавяме LNS time limit за по-добър контрол на търсенето
            if hasattr(self.config, 'lns_time_limit_seconds'):
                search_parameters.lns_time_limit.seconds = self.config.lns_time_limit_seconds
                logger.info(f"  - LNS Time Limit: {self.config.lns_time_limit_seconds} секунди")
            
            # Добавяме LNS neighborhood параметри за по-добър контрол
            if hasattr(self.config, 'lns_num_nodes'):
                search_parameters.heuristic_close_nodes_lns_num_nodes = self.config.lns_num_nodes
                logger.info(f"  - LNS Num Nodes: {self.config.lns_num_nodes}")
            if hasattr(self.config, 'lns_num_arcs'):
                search_parameters.heuristic_expensive_chain_lns_num_arcs_to_consider = self.config.lns_num_arcs
                logger.info(f"  - LNS Num Arcs: {self.config.lns_num_arcs}")
            
            logger.info(f"📝 Параметри за търсене:")
            logger.info(f"  - First Solution Strategy: {self.config.first_solution_strategy}")
            logger.info(f"  - Local Search Metaheuristic: {self.config.local_search_metaheuristic}")
            logger.info(f"  - Time Limit: {time_limit} секунди")
            logger.info(f"  - Log Search: {self.config.log_search}")
            
            # 8. Решаване на проблема
            logger.info("="*60)
            logger.info("� СТЪПКА 8: РЕШАВАНЕ НА ПРОБЛЕМА")
            logger.info("="*60)
            
            logger.info("�🔄 Стартиране на опростен OR-Tools solver...")
            logger.info("⏱️ Моля, изчакайте до 30 секунди за решението...")
            # Записваме времето преди решаването
            start_time = time.time()
            solution = routing.SolveWithParameters(search_parameters)
            solve_time = time.time() - start_time
                
            # 9. Извличане на решението
            logger.info("="*60)
            logger.info("🔍 СТЪПКА 9: ОБРАБОТКА НА РЕЗУЛТАТИТЕ")
            logger.info("="*60)
            
            if solution:
                logger.info(f"✅ Намерено решение с опростена логика за {solve_time:.2f} секунди")
                logger.info(f"📊 Обективна стойност на решението: {solution.ObjectiveValue()}")
                
                # Отпечатване на подробна информация за маршрутите
                used_vehicles = 0
                total_distance = 0
                total_load = 0
                logger.info("🚍 ДЕТАЙЛИ ЗА МАРШРУТИТЕ:")
                
                for vehicle_id in range(data["num_vehicles"]):
                    if not routing.IsVehicleUsed(solution, vehicle_id):
                        logger.info(f"  - Превозно средство {vehicle_id}: Не се използва")
                        continue
                        
                    used_vehicles += 1
                    route_nodes = []
                    index = routing.Start(vehicle_id)
                    route_distance = 0
                    route_load = 0
                    
                    logger.info(f"  - Маршрут за превозно средство {vehicle_id}:")
                    route_info = f"    {manager.IndexToNode(index)} (депо)"
                    
                    while not routing.IsEnd(index):
                        node_index = manager.IndexToNode(index)
                        route_nodes.append(node_index)
                        route_load += data["demands"][node_index]
                        previous_index = index
                        index = solution.Value(routing.NextVar(index))
                        route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
                        
                        if not routing.IsEnd(index):
                            route_info += f" -> {manager.IndexToNode(index)}"
                    
                    route_info += f" -> {manager.IndexToNode(index)} (депо)"
                    logger.info(route_info)
                    logger.info(f"    Разстояние: {route_distance}, Товар: {route_load}/{data['vehicle_capacities'][vehicle_id]} ({route_load*100/data['vehicle_capacities'][vehicle_id]:.1f}%)")
                    total_distance += route_distance
                    total_load += route_load
                
                logger.info(f"🔢 ОБОБЩЕНИЕ НА РЕШЕНИЕТО:")
                logger.info(f"  - Използвани превозни средства: {used_vehicles}/{data['num_vehicles']} ({used_vehicles*100/data['num_vehicles']:.1f}%)")
                logger.info(f"  - Общо разстояние: {total_distance}")
                logger.info(f"  - Общ товар: {total_load}")
                capacity_utilization = total_load / sum(data['vehicle_capacities']) * 100
                logger.info(f"  - Използване на капацитета: {capacity_utilization:.1f}%")
                
                logger.info(f"Общо разстояние: {total_distance}, общ товар: {total_load}")
                
                return self._extract_simple_solution(manager, routing, solution, data)
            else:
                logger.error("❌ Опростеният solver не намери решение")
                return self._create_empty_solution()

        except Exception as e:
            logger.error(f"❌ Грешка в опростения solver: {e}", exc_info=True)
            return self._create_empty_solution()

    def _create_simple_data_model(self):
        """Създава опростен data model като в OR-Tools примера"""
        data = {}
        
        # Distance matrix - използваме OSRM данните
        # Важно: Уверяваме се, че всички стойности са цели числа, както в оригиналния пример
        distances = []
        for row in self.distance_matrix.distances:
            distances.append([int(d) for d in row])
        data['distance_matrix'] = distances
        
        # Дефинираме скала за превръщане на обемите в цели числа
        SCALE_FACTOR = 100  # Нов мащабен фактор - умножаваме всичко по 100
        logger.info(f"🔍 Използване на мащабен фактор: {SCALE_FACTOR} за превръщане на обеми в цели числа")
        
        # Demands - депо има 0, клиенти имат реални стойности
        # Конвертираме обемите към цели числа с по-голям мащаб за по-висока прецизност
        data['demands'] = [0] + [max(1, int(c.volume * SCALE_FACTOR)) for c in self.customers]
        
        # Добавяме подробна информация за дебъг
        total_demand = sum(data['demands'])
        logger.info(f"📦 Общо търсене (scaled): {total_demand}")
        logger.info(f"📊 Примерни търсения (първите 5 клиента): {data['demands'][1:6]}")
        
        # Vehicle capacities - всички превозни средства
        data['vehicle_capacities'] = []
        for v_config in self.vehicle_configs:
            if v_config.enabled:
                # Скалираме капацитета в СЪЩИЯ мащаб като изискванията
                capacity = int(v_config.capacity * SCALE_FACTOR)
                logger.info(f"🚚 Превозно средство {v_config.vehicle_type.value}: капацитет {v_config.capacity} → {capacity} (scaled)")
                for _ in range(v_config.count):
                    data['vehicle_capacities'].append(capacity)
        
        # Проверка дали имаме превозни средства
        if not data['vehicle_capacities']:
            # Ако няма конфигурирани превозни средства, добавяме едно по подразбиране с голям капацитет
            default_capacity = int(1000 * SCALE_FACTOR)
            data['vehicle_capacities'] = [default_capacity]
            logger.warning(f"⚠️ Няма конфигурирани превозни средства, добавяме по подразбиране с капацитет {default_capacity}")
        
        # Брой превозни средства
        data['num_vehicles'] = len(data['vehicle_capacities'])
        
        # Депо - винаги индекс 0
        data['depot'] = 0
        
        # Проверка дали общият капацитет е достатъчен за общото търсене
        total_capacity = sum(data['vehicle_capacities'])
        capacity_demand_ratio = total_capacity / total_demand if total_demand > 0 else float('inf')
        
        logger.info(f"📊 Опростен data model: {len(self.customers)} клиента, {data['num_vehicles']} превозни средства")
        logger.info(f"  - Vehicle capacities (scaled): {data['vehicle_capacities']}")
        logger.info(f"  - Total demand (scaled): {total_demand}")
        logger.info(f"  - Total capacity (scaled): {total_capacity}")
        logger.info(f"  - Capacity/Demand ratio: {capacity_demand_ratio:.2f}")
        
        if capacity_demand_ratio < 1.0:
            logger.warning(f"⚠️ Общият капацитет ({total_capacity}) по-малък от общото търсене ({total_demand})!")
            logger.warning(f"   Някои клиенти ще бъдат пропуснати!")
        else:
            logger.info(f"✅ Общият капацитет ({total_capacity}) е достатъчен за общото търсене ({total_demand})")
        
        return data

    def _extract_simple_solution(self, manager, routing, solution, data) -> CVRPSolution:
        """
        Извлича решението от опростения solver и го преобразува във формат,
        съвместим с останалата част от програмата
        """
        logger.info("="*60)
        logger.info("🔍 ПРЕОБРАЗУВАНЕ НА РЕШЕНИЕТО КЪМ CVRP ФОРМАТ")
        logger.info("="*60)
        
        routes = []
        total_distance = 0
        
        # Множество за проследяване на обслужените клиенти
        all_serviced_customer_indices = set()
        
        logger.info("Започвам извличане на маршрути от OR-Tools решение...")
        
        for vehicle_id in range(data['num_vehicles']):
            # Проверяваме дали маршрутът се използва
            if not routing.IsVehicleUsed(solution, vehicle_id):
                continue
                
            # Списък с клиентите в този маршрут
            route_customers = []
            route_distance = 0
            route_load = 0
            
            # Намираме конфигурацията на превозното средство
            vehicle_config = self._get_vehicle_config_for_id(vehicle_id)
            
            # Ако нямаме конфигурация, използваме първата налична
            if vehicle_config is None and self.vehicle_configs:
                for v_config in self.vehicle_configs:
                    if v_config.enabled:
                        vehicle_config = v_config
                        break
            
            # Ако още нямаме конфигурация, създаваме базова
            if vehicle_config is None:
                vehicle_config = self.vehicle_configs[0] if self.vehicle_configs else None
            
            # Проследяваме маршрута от началото до края
            index = routing.Start(vehicle_id)
            previous_node = None
            
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                route_load += data['demands'][node_index]
                
                # Ако не е депо (индекс 0), добавяме клиента
                if node_index != 0:  # 0 е индексът на депото
                    # Коригиран индекс - отчитаме че индекс 0 е депото
                    customer_index = node_index - 1
                    if 0 <= customer_index < len(self.customers):
                        customer = self.customers[customer_index]
                        route_customers.append(customer)
                        all_serviced_customer_indices.add(customer_index)
                        logger.debug(f"    + Добавен клиент: {customer.id} (индекс {customer_index}, възел {node_index})")
                
                # Запазваме предишния индекс, за да изчислим разстоянието
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                
                # Добавяме разстоянието към общото за маршрута
                route_distance += routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id
                )
            
            if route_customers:
                # Изчисляваме реалното разстояние в километри (OR-Tools връща цели числа)
                route_distance_km = route_distance / 1000  # Конвертираме в километри
                
                # Изчисляваме времето (пътуване + обслужване)
                # Приемаме средна скорост от 40 км/ч
                route_time_minutes = (route_distance_km / 40) * 60
                
                # Добавяме времето за обслужване на клиентите
                service_time = 0
                if vehicle_config and hasattr(vehicle_config, 'service_time_minutes'):
                    service_time = vehicle_config.service_time_minutes
                else:
                    service_time = 10  # По подразбиране - 10 минути за клиент
                
                route_time_minutes += len(route_customers) * service_time
                
                # Създаваме обект за маршрут
                if vehicle_config:
                    vehicle_type = vehicle_config.vehicle_type
                    depot_location = vehicle_config.start_location or self.unique_depots[0]
                else:
                    from config import VehicleType
                    vehicle_type = VehicleType.INTERNAL_BUS
                    depot_location = self.unique_depots[0]
                
                total_volume = sum(c.volume for c in route_customers)
                
                route = Route(
                    vehicle_type=vehicle_type,
                    vehicle_id=vehicle_id,
                    customers=route_customers,
                    depot_location=depot_location,
                    total_distance_km=route_distance_km,
                    total_time_minutes=route_time_minutes,
                    total_volume=total_volume,
                    is_feasible=True
                )
                
                routes.append(route)
                total_distance += route_distance
                
                logger.info(f"🚌 Маршрут {len(routes)} (ID: {vehicle_id}, Тип: {vehicle_type.value}):")
                logger.info(f"  - Клиенти: {len(route_customers)} бр.")
                logger.info(f"  - Обем: {total_volume:.2f} стекове")
                logger.info(f"  - Разстояние: {route_distance_km:.2f} км")
                logger.info(f"  - Време: {route_time_minutes:.2f} минути")
                
                # Показване на първите няколко клиента за дебъг
                sample_customers = min(5, len(route_customers))
                if sample_customers > 0:
                    logger.info(f"  - Примерни клиенти: {[c.id for c in route_customers[:sample_customers]]}")
        
        # Намираме пропуснатите клиенти (клиенти, които не са били включени в никакъв маршрут)
        all_customer_indices = set(range(len(self.customers)))
        dropped_customer_indices = all_customer_indices - all_serviced_customer_indices
        dropped_customers = [self.customers[i] for i in dropped_customer_indices]
        
        logger.info("="*60)
        logger.info("🔍 ОБОБЩЕНИЕ НА ОБРАБОТЕНИТЕ ДАННИ")
        logger.info("="*60)
        
        logger.info(f"✅ Обслужени клиенти: {len(all_serviced_customer_indices)} от {len(self.customers)} ({len(all_serviced_customer_indices)*100/len(self.customers):.1f}%)")
        logger.info(f"⚠️ Пропуснати клиенти: {len(dropped_customers)} от {len(self.customers)} ({len(dropped_customers)*100/len(self.customers):.1f}%)")
        
        if dropped_customers:
            logger.warning(f"⚠️ ВНИМАНИЕ: {len(dropped_customers)} клиента не могат да бъдат обслужени")
            # Показване на първите няколко пропуснати клиента за дебъг
            sample_dropped = min(5, len(dropped_customers))
            if sample_dropped > 0:
                logger.warning(f"  - Примерни пропуснати клиенти: {[c.id for c in dropped_customers[:sample_dropped]]}")
                logger.warning(f"  - Обем на пропуснати клиенти: {sum(c.volume for c in dropped_customers[:sample_dropped])}")
        
        # Изчисляваме общия обем, разстояние и време за всички маршрути
        total_served_volume = sum(r.total_volume for r in routes)
        total_distance_km = sum(r.total_distance_km for r in routes)
        total_time_minutes = sum(r.total_time_minutes for r in routes)
        
        logger.info("📊 Общи показатели на решението:")
        logger.info(f"  - Обслужен обем: {total_served_volume:.2f} стекове")
        logger.info(f"  - Общо разстояние: {total_distance_km:.2f} км")
        logger.info(f"  - Общо време: {total_time_minutes:.2f} минути")
        logger.info(f"  - Създадени маршрути: {len(routes)}")
        
        # Създаваме и връщаме финалното решение
        return CVRPSolution(
            routes=routes,
            dropped_customers=dropped_customers,
            total_distance_km=total_distance_km,
            total_time_minutes=sum(r.total_time_minutes for r in routes),
            total_vehicles_used=len(routes),
            fitness_score=float(solution.ObjectiveValue()),
            is_feasible=True,
            total_served_volume=total_served_volume
        )


class CVRPSolver:
    """Главен клас за решаване на CVRP - опростена версия."""
    
    def __init__(self, config: Optional[CVRPConfig] = None):
        self.config = config or get_config().cvrp
    
    def solve(self, 
              allocation: WarehouseAllocation, 
              depot_location: Tuple[float, float],
              distance_matrix: DistanceMatrix) -> CVRPSolution:
        
        enabled_vehicles = get_config().vehicles or []
        
        unique_depots = {depot_location}
        for vehicle_config in enabled_vehicles:
            if vehicle_config.enabled and vehicle_config.start_location:
                unique_depots.add(vehicle_config.start_location)
        
        # Гарантираме, че главното депо е винаги първо в списъка
        sorted_depots = [depot_location]  # Главното депо винаги първо
        other_depots = sorted([d for d in unique_depots if d != depot_location], key=lambda x: (x[0], x[1]))
        sorted_depots.extend(other_depots)
        
        # Директно използваме OR-Tools
        solver = ORToolsSolver(
            self.config, enabled_vehicles, allocation.vehicle_customers, 
            distance_matrix, sorted_depots, allocation.center_zone_customers,
            get_config().locations
        )
        
        # Добавяме лог за дебъгване
        logger.info(f"🔍 CVRPSolver: use_simple_solver = {self.config.use_simple_solver}")
        
        # Избираме кой solver да използваме
        if self.config.use_simple_solver:
            logger.info("🔧 Използване на опростен solver (само capacity constraints)")
            return solver.solve_simple()
        else:
            logger.info("🔧 Използване на пълен solver (всички constraints)")
            return solver.solve()


# Удобна функция
def solve_cvrp(allocation: WarehouseAllocation, 
               depot_location: Tuple[float, float], 
               distance_matrix: DistanceMatrix) -> CVRPSolution:
    """Удобна функция за решаване на CVRP"""
    solver = CVRPSolver()
    return solver.solve(allocation, depot_location, distance_matrix) 