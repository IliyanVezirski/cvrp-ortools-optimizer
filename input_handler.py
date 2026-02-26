"""
Модул за обработка на входни данни за CVRP
Чете Excel файлове с GPS данни, клиенти и обеми
"""

import pandas as pd
import re
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging
import importlib
import config

logger = logging.getLogger(__name__)


@dataclass
class Customer:
    """Клас за представяне на клиент"""
    id: str
    name: str
    coordinates: Optional[Tuple[float, float]]  # (latitude, longitude)
    volume: float
    original_gps_data: str


@dataclass
class InputData:
    """Клас за входните данни"""
    customers: List[Customer]
    total_volume: float
    depot_location: Tuple[float, float]
    
    def __post_init__(self):
        """Изчислява общия обем"""
        self.total_volume = sum(customer.volume for customer in self.customers)


class GPSParser:
    """Парсър за GPS координати от различни формати"""
    
    @staticmethod
    def parse_gps_string(gps_string: str) -> Optional[Tuple[float, float]]:
        """Парсира GPS координати от текстов низ"""
        if not gps_string or pd.isna(gps_string):
            return None
        
        gps_string = str(gps_string).strip()
        
        # Обикновени десетични координати
        decimal_pattern = r'(-?\d+\.?\d*),?\s*(-?\d+\.?\d*)'
        match = re.search(decimal_pattern, gps_string)
        if match:
            try:
                lat = float(match.group(1))
                lon = float(match.group(2))
                
                # Валидация на координатите
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lat, lon)
            except ValueError:
                pass
        
        logger.warning(f"Не мога да парсирам GPS координати: {gps_string}")
        return None


class InputHandler:
    """Главен клас за обработка на входни данни"""
    
    def __init__(self):
        import importlib
        import config
        importlib.reload(config)
        self.config = config.get_config().input
    
    def load_data(self, file_path: Optional[str] = None) -> InputData:
        """Зарежда данни от файл"""
        # Използваме подадения път или взимаме от конфигурацията
        file_path = file_path or self.config.excel_file_path
        
        # Проверяваме дали файлът съществува, ако не опитваме да намерим файла на различни места
        if not os.path.exists(file_path):
            logger.warning(f"Файлът не съществува на път: {file_path}")
            
            # Ако пътят не е абсолютен, опитваме да го намерим в текущата директория
            if not os.path.isabs(file_path):
                current_dir = os.getcwd()
                possible_paths = [
                    os.path.join(current_dir, file_path),
                    os.path.join(current_dir, 'data', os.path.basename(file_path)),
                    os.path.join(current_dir, os.path.basename(file_path))
                ]
                
                for possible_path in possible_paths:
                    if os.path.exists(possible_path):
                        logger.info(f"Намерен файл на път: {possible_path}")
                        file_path = possible_path
                        break
        
        logger.info(f"Опитвам да заредя файл от: {file_path}")
        
        try:
            # Четене на Excel файла
            if self.config.sheet_name:
                df = pd.read_excel(file_path, sheet_name=self.config.sheet_name)
            else:
                df = pd.read_excel(file_path)
            
            logger.info(f"Успешно заредени {len(df)} реда от {file_path}")
            
            # Обработка на данните
            customers = self._process_dataframe(df)
            
            # Филтриране на валидни клиенти
            valid_customers = [c for c in customers if c.coordinates is not None]
            
            # Получаване на депо координати
            depot_location = config.get_config().locations.depot_location
            
            input_data = InputData(
                customers=valid_customers,
                total_volume=0,  # ще се изчисли в __post_init__
                depot_location=depot_location
            )
            
            return input_data
            
        except Exception as e:
            logger.error(f"Грешка при четене на файла {file_path}: {e}")
            raise
    
    def _process_dataframe(self, df: pd.DataFrame) -> List[Customer]:
        """Обработва DataFrame и създава списък от клиенти"""
        customers = []
        parser = GPSParser()
        
        for index, row in df.iterrows():
            try:
                client_id = str(row[self.config.client_id_column]).strip()
                client_name = str(row[self.config.client_name_column]).strip()
                gps_data = str(row[self.config.gps_column]).strip()
                volume = float(row[self.config.volume_column])
                
                coordinates = parser.parse_gps_string(gps_data)
                
                customer = Customer(
                    id=client_id,
                    name=client_name,
                    coordinates=coordinates,
                    volume=volume,
                    original_gps_data=gps_data
                )
                
                customers.append(customer)
                
            except Exception as e:
                # Променяме съобщението, за да работи с всякакъв тип индекс (не само числа)
                logger.error(f"Грешка при обработка на ред с индекс '{index}': {e}")
                continue
        
        return customers


# Функция за лесно използване
def load_customer_data(file_path: Optional[str] = None) -> InputData:
    """Удобна функция за зареждане на клиентски данни"""
    handler = InputHandler()
    return handler.load_data(file_path) 