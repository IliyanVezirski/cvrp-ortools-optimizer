"""
Модул за обработка на входни данни за CVRP
Чете Excel файлове с GPS данни, клиенти и обеми
"""

import pandas as pd
import re
import os
import json
import urllib.request
import ssl
from datetime import datetime, timedelta
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
    document: str = ""


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
        """Зарежда данни от файл или HTTP JSON"""
        # Ако input_source е http_json, зареждаме от URL
        if self.config.input_source == "http_json":
            return self._load_from_json_url()
        
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
            # Определяме колони които да се четат като текст (за запазване на водещи нули)
            dtype_overrides = {}
            if self.config.document_column:
                dtype_overrides[self.config.document_column] = str
            
            # Четене на Excel файла
            if self.config.sheet_name:
                df = pd.read_excel(file_path, sheet_name=self.config.sheet_name, dtype=dtype_overrides)
            else:
                df = pd.read_excel(file_path, dtype=dtype_overrides)
            
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
    
    @staticmethod
    def _next_business_date() -> str:
        """Връща следващия работен ден като YYYY-MM-DD.
        Пон-Чет → утре, Пет → понеделник, Съб → понеделник, Нед → понеделник."""
        today = datetime.now()
        weekday = today.weekday()  # 0=Mon ... 4=Fri, 5=Sat, 6=Sun
        if weekday == 4:    # петък → +3 дни (понеделник)
            delta = 3
        elif weekday == 5:  # събота → +2 дни (понеделник)
            delta = 2
        elif weekday == 6:  # неделя → +1 ден (понеделник)
            delta = 1
        else:               # пон-чет → +1 ден
            delta = 1
        return (today + timedelta(days=delta)).strftime("%Y-%m-%d")

    def _load_from_json_url(self) -> InputData:
        """Зарежда данни от HTTP JSON endpoint"""
        base_url = self.config.json_url
        if not base_url:
            raise ValueError("json_url не е зададен в InputConfig")
        
        # Ако е зададена конкретна дата (DD/MM/YYYY), конвертираме към YYYY-MM-DD за URL
        override = self.config.json_override_date.strip() if self.config.json_override_date else ""
        if override:
            parsed = datetime.strptime(override, "%d/%m/%Y")
            target_date = parsed.strftime("%Y-%m-%d")
            logger.info(f"Ръчно зададена дата: {override} → {target_date}")
        else:
            target_date = self._next_business_date()
            logger.info(f"Автоматична дата (следващ работен ден): {target_date}")
        separator = "&" if "?" in base_url else "?"
        url = f"{base_url}{separator}date={target_date}"
        
        logger.info(f"Зареждам данни от HTTP JSON: {url}  (дата: {target_date})")
        
        try:
            # Създаваме SSL контекст (позволява self-signed сертификати при нужда)
            ctx = ssl.create_default_context()
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            
            with urllib.request.urlopen(req, timeout=self.config.json_timeout_seconds, context=ctx) as response:
                raw_bytes = response.read()
                # Опитваме UTF-8, после Windows-1251 (кирилица)
                for enc in ("utf-8", "windows-1251", "latin-1"):
                    try:
                        raw = raw_bytes.decode(enc)
                        logger.info(f"JSON декодиран с {enc}")
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raw = raw_bytes.decode("utf-8", errors="replace")
            
            # Поправяме чести проблеми в JSON от сървъра:
            # 1. \r без \n
            raw = raw.replace("\r", "\n")
            # 2. GPS стойности без отваряща кавичка: "GPS": 42.676...,23.360..." → "GPS": "42.676...,23.360..."
            raw = re.sub(r'"GPS":\s*([\d.])', r'"GPS": "\1', raw)
            
            data = json.loads(raw)
            
            # Поддържаме както списък, така и обект с ключ съдържащ списъка
            if isinstance(data, dict):
                # Търсим първия ключ който съдържа списък
                for key, val in data.items():
                    if isinstance(val, list):
                        data = val
                        logger.info(f"Използвам JSON ключ '{key}' с {len(data)} записа")
                        break
                else:
                    raise ValueError("JSON обектът не съдържа списък с данни")
            
            if not isinstance(data, list):
                raise ValueError(f"Очакван е JSON списък, получен е {type(data).__name__}")
            
            logger.info(f"Получени {len(data)} записа от JSON")
            
            # Конвертиране в Customer обекти
            customers = self._process_json_records(data)
            valid_customers = [c for c in customers if c.coordinates is not None]
            
            depot_location = config.get_config().locations.depot_location
            
            return InputData(
                customers=valid_customers,
                total_volume=0,
                depot_location=depot_location
            )
            
        except urllib.error.URLError as e:
            logger.error(f"Грешка при връзка с {url}: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Невалиден JSON отговор: {e}")
            raise
    
    def _process_json_records(self, records: list) -> List[Customer]:
        """Обработва JSON записи и създава списък от клиенти"""
        customers = []
        parser = GPSParser()
        
        gps_field = self.config.json_gps_field
        id_field = self.config.json_client_id_field
        name_field = self.config.json_client_name_field
        vol_field = self.config.json_volume_field
        doc_field = self.config.json_document_field
        
        for idx, record in enumerate(records):
            try:
                gps_data = str(record.get(gps_field, "")).strip()
                client_id = str(record.get(id_field, "")).strip()
                client_name = str(record.get(name_field, "")).strip()
                volume = float(record.get(vol_field, 0))
                document = str(record.get(doc_field, "")).strip()
                
                coordinates = parser.parse_gps_string(gps_data)
                
                customer = Customer(
                    id=client_id,
                    name=client_name,
                    coordinates=coordinates,
                    volume=volume,
                    original_gps_data=gps_data,
                    document=document
                )
                customers.append(customer)
                
            except Exception as e:
                logger.error(f"Грешка при обработка на JSON запис {idx}: {e}")
                continue
        
        return customers

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
                
                # Четем номер на документ/поръчка ако колоната съществува
                document = ""
                if self.config.document_column and self.config.document_column in row.index:
                    doc_val = row[self.config.document_column]
                    if pd.notna(doc_val):
                        document = str(doc_val).strip()
                
                coordinates = parser.parse_gps_string(gps_data)
                
                customer = Customer(
                    id=client_id,
                    name=client_name,
                    coordinates=coordinates,
                    volume=volume,
                    original_gps_data=gps_data,
                    document=document
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