# Анализ на помощните модули

## create_sample_data.py - Тестови данни

**`create_sample_excel()`**
Създава примерен Excel с 25 клиента в София:
- GPS формати: различни варианти
- Обем: 10-150 стекове
- Изход: `data/sample_clients.xlsx`

---

## demo.py - Демонстрации

**Основни функции:**
- `run_demo()` - основна демонстрация
- `run_custom_demo()` - с персонализирани настройки
- `demo_vehicle_configurations()` - различни конфигурации
- `main()` - интерактивно меню

---

## large_scale_config.py - Големи проблеми

**Конфигурации:**
- `large_scale_optimization_config()` - 20 минути за 150-250 клиента
- `ultra_optimization_config()` - 30 минути максимална оптимизация
- `adaptive_config_by_client_count()` - автоматична според размера

**Performance очаквания:**
- 150 клиента: първо решение 30-60s, оптимално 20-30 мин
- 200 клиента: първо решение 45-90s, оптимално 25-40 мин  
- 250 клиента: първо решение 60-120s, оптимално 30-50 мин

---

## debug_ortools.py - OR-Tools диагностика

**`test_ortools_minimal()`**
4 теста за диагностика:
1. Само capacity ограничения
2. Увеличено време
3. SAVINGS стратегия  
4. Намален dataset

**`SimplifiedORToolsSolver`**
Опростен solver за диагностика

---

## config_timeout_examples.py - Timeout настройки

**Timeout стратегии:**
- `quick_optimization_config()` - 60s за тестване
- `standard_business_config()` - 300s стандартно
- `thorough_optimization_config()` - 900s задълбочено
- `maximum_optimization_config()` - 1800s максимално

**Препоръки по случаи:**
- Development: 60s
- Ежедневно: 300s
- Седмично: 900s
- Стратегическо: 1800s 