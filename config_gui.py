"""
Опростен графичен интерфейс за редактиране на config.py
Позволява промяна на най-важните настройки без ръчна редакция на файла.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import importlib

# Добавяме текущата директория в path
if getattr(sys, 'frozen', False):
    _base_dir = os.path.dirname(sys.executable)
else:
    _base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _base_dir)
import config


class ConfigGUI:
    """Графичен интерфейс за config.py"""

    # Български етикети за секциите и полетата
    SECTION_LABELS = {
        "input": "📥 Входни данни",
        "vehicles": "🚐 Превозни средства",
        "warehouse": "🏭 Предварителна оптимизация",
        "cvrp": "⚙️ Солвър (CVRP)",
        "locations": "📍 Локации",
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CVRP Настройки")
        self.root.geometry("820x700")
        self.root.resizable(True, True)

        # Зареждаме текущата конфигурация
        importlib.reload(config)
        self.cfg = config.get_config()
        self.widgets = {}  # field_key → widget

        self._build_ui()

    # ── UI ────────────────────────────────────────────────────

    def _build_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Button(toolbar, text="💾  Запази и затвори", command=self._save_and_close).pack(side="left", padx=4)
        ttk.Button(toolbar, text="💾  Запази", command=self._save).pack(side="left", padx=4)
        ttk.Button(toolbar, text="🚀  Запази и стартирай", command=self._save_and_run).pack(side="left", padx=4)
        ttk.Button(toolbar, text="❌  Отказ", command=self.root.destroy).pack(side="right", padx=4)

        # Notebook (tabs)
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        # ─── Tab 1: Входни данни ───
        self._add_input_tab(nb)

        # ─── Tab 2: Превозни средства ───
        self._add_vehicles_tab(nb)

        # ─── Tab 3: Склад ───
        self._add_warehouse_tab(nb)

        # ─── Tab 4: Солвър ───
        self._add_solver_tab(nb)

        # ─── Tab 5: Локации ───
        self._add_locations_tab(nb)

        # ─── Tab 6: Изходни данни ───
        self._add_output_tab(nb)

        # ─── Tab 7: Планировчик ───
        self._add_scheduler_tab(nb)

    # ── Helpers ──────────────────────────────────────────────

    def _make_scrollable_frame(self, parent):
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)

        def _update_scroll_visibility(event=None):
            canvas.update_idletasks()
            bbox = canvas.bbox("all")
            if not bbox:
                return
            content_height = bbox[3] - bbox[1]
            canvas_height = canvas.winfo_height()
            canvas.configure(scrollregion=bbox)
            if content_height > canvas_height:
                scrollbar.pack(side="right", fill="y")
                canvas._scroll_needed = True
            else:
                scrollbar.pack_forget()
                canvas._scroll_needed = False

        frame.bind("<Configure>", _update_scroll_visibility)
        canvas.bind("<Configure>", _update_scroll_visibility)
        canvas._scroll_needed = False

        def _on_mousewheel(event):
            if canvas._scroll_needed:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_wheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_wheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)
        frame.bind("<Enter>", _bind_wheel)
        frame.bind("<Leave>", _unbind_wheel)
        return frame

    def _add_field(self, parent, row, key, label, value, field_type="str", options=None, tooltip=""):
        ttk.Label(parent, text=label, anchor="w").grid(row=row, column=0, sticky="w", padx=6, pady=3)

        if field_type == "bool":
            var = tk.BooleanVar(value=value)
            cb = ttk.Checkbutton(parent, variable=var)
            cb.grid(row=row, column=1, sticky="w", padx=6, pady=3)
            self.widgets[key] = var
        elif field_type == "combo" and options:
            var = tk.StringVar(value=str(value))
            combo = ttk.Combobox(parent, textvariable=var, values=options, state="readonly", width=30)
            combo.grid(row=row, column=1, sticky="w", padx=6, pady=3)
            self.widgets[key] = var
        else:
            var = tk.StringVar(value=str(value))
            entry = ttk.Entry(parent, textvariable=var, width=50)
            entry.grid(row=row, column=1, sticky="we", padx=6, pady=3)
            self.widgets[key] = var

        if tooltip:
            ttk.Label(parent, text=tooltip, foreground="gray", font=("", 8)).grid(
                row=row, column=2, sticky="w", padx=4, pady=3
            )

    def _add_list_field(self, parent, row, key, label, values_list, options=None, tooltip=""):
        """Добавя поле за списък от стойности (по една на ред в Text widget)"""
        ttk.Label(parent, text=label, anchor="w").grid(row=row, column=0, sticky="nw", padx=6, pady=3)
        text_val = "\n".join(str(v) for v in values_list)
        text_w = tk.Text(parent, width=40, height=max(3, len(values_list)), wrap="none")
        text_w.insert("1.0", text_val)
        text_w.grid(row=row, column=1, sticky="we", padx=6, pady=3)
        self.widgets[key] = text_w
        hint = tooltip or "По един елемент на ред"
        ttk.Label(parent, text=hint, foreground="gray", font=("", 8)).grid(
            row=row, column=2, sticky="nw", padx=4, pady=3
        )

    # ── Tab: Входни данни ────────────────────────────────────

    def _add_input_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text=" 📥 Входни данни ")
        f = self._make_scrollable_frame(tab)
        f.columnconfigure(1, weight=1)
        inp = self.cfg.input
        r = 0
        self._add_field(f, r, "input.input_source", "Източник на данни:", inp.input_source,
                         "combo", ["excel", "http_json"]); r += 1
        self._add_field(f, r, "input.excel_file_path", "Excel файл:", inp.excel_file_path); r += 1
        self._add_field(f, r, "input.json_url", "JSON URL:", inp.json_url); r += 1
        self._add_field(f, r, "input.json_override_date", "Конкретна дата (DD/MM/YYYY):", inp.json_override_date,
                         tooltip="Празно = автоматично следващ работен ден"); r += 1
        self._add_field(f, r, "input.json_timeout_seconds", "HTTP таймаут (сек):", inp.json_timeout_seconds); r += 1

        ttk.Separator(f, orient="horizontal").grid(row=r, column=0, columnspan=3, sticky="we", pady=8); r += 1
        ttk.Label(f, text="Картографиране на JSON полета:", font=("", 9, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", padx=6); r += 1
        self._add_field(f, r, "input.json_gps_field", "GPS поле:", inp.json_gps_field); r += 1
        self._add_field(f, r, "input.json_client_id_field", "Клиентски номер:", inp.json_client_id_field); r += 1
        self._add_field(f, r, "input.json_client_name_field", "Име на клиент:", inp.json_client_name_field); r += 1
        self._add_field(f, r, "input.json_volume_field", "Обем (стекове):", inp.json_volume_field); r += 1
        self._add_field(f, r, "input.json_document_field", "Номер документ:", inp.json_document_field); r += 1

        ttk.Separator(f, orient="horizontal").grid(row=r, column=0, columnspan=3, sticky="we", pady=8); r += 1
        ttk.Label(f, text="Картографиране на Excel колони:", font=("", 9, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", padx=6); r += 1
        self._add_field(f, r, "input.gps_column", "GPS колона:", inp.gps_column); r += 1
        self._add_field(f, r, "input.client_id_column", "ID колона:", inp.client_id_column); r += 1
        self._add_field(f, r, "input.client_name_column", "Име колона:", inp.client_name_column); r += 1
        self._add_field(f, r, "input.volume_column", "Обем колона:", inp.volume_column); r += 1
        self._add_field(f, r, "input.document_column", "Документ колона:", inp.document_column); r += 1

    # ── Tab: Превозни средства ───────────────────────────────

    def _add_vehicles_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text=" 🚐 Превозни средства ")
        f = self._make_scrollable_frame(tab)
        f.columnconfigure(1, weight=1)

        if not self.cfg.vehicles:
            ttk.Label(f, text="Няма конфигурирани превозни средства").grid(row=0, column=0)
            return

        r = 0
        for i, v in enumerate(self.cfg.vehicles):
            vtype = v.vehicle_type.value
            label_map = {
                "internal_bus": "🚐 Вътрешен бус",
                "center_bus": "🚐 Център бус",
                "external_bus": "🚐 Външен бус",
                "special_bus": "🚐 Специален бус",
                "vratza_bus": "🚐 Враца бус",
            }
            header = label_map.get(vtype, vtype)
            ttk.Label(f, text=f"── {header} ──", font=("", 10, "bold")).grid(
                row=r, column=0, columnspan=3, sticky="w", padx=6, pady=(10, 2)); r += 1

            prefix = f"vehicle.{i}"
            self._add_field(f, r, f"{prefix}.enabled", "Активен:", v.enabled, "bool"); r += 1
            self._add_field(f, r, f"{prefix}.count", "Брой:", v.count); r += 1
            self._add_field(f, r, f"{prefix}.capacity", "Капацитет (ст.):", v.capacity); r += 1
            self._add_field(f, r, f"{prefix}.max_time_hours", "Макс. време (ч.):", v.max_time_hours); r += 1
            self._add_field(f, r, f"{prefix}.service_time_minutes", "Обслужване (мин):", v.service_time_minutes); r += 1
            self._add_field(f, r, f"{prefix}.max_customers_per_route", "Макс. клиенти:",
                             v.max_customers_per_route if v.max_customers_per_route else "",
                             tooltip="Празно = без ограничение"); r += 1
            self._add_field(f, r, f"{prefix}.start_time_minutes", "Старт (мин от 00:00):", v.start_time_minutes,
                             tooltip="480 = 08:00"); r += 1

    # ── Tab: Склад ───────────────────────────────────────────

    def _add_warehouse_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text=" 🏭 Предварителна оптимизация")
        f = self._make_scrollable_frame(tab)
        f.columnconfigure(1, weight=1)
        wh = self.cfg.warehouse
        r = 0
        self._add_field(f, r, "warehouse.enable_warehouse", "Включен:", wh.enable_warehouse, "bool"); r += 1
        self._add_field(f, r, "warehouse.sort_by_volume", "Сортиране по обем:", wh.sort_by_volume, "bool"); r += 1
        self._add_field(f, r, "warehouse.sort_by_distance", "Сортиране по разстояние:", wh.sort_by_distance, "bool"); r += 1
        self._add_field(f, r, "warehouse.check_max_bus_capacity", "Проверка макс. капацитет:", wh.check_max_bus_capacity, "bool"); r += 1
        self._add_field(f, r, "warehouse.max_bus_customer_volume", "Макс. обем на клиент (ст.):", wh.max_bus_customer_volume); r += 1
        self._add_field(f, r, "warehouse.capacity_toleranse", "Толеранс капацитет:", wh.capacity_toleranse); r += 1

    # ── Tab: Солвър ──────────────────────────────────────────

    def _add_solver_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text=" ⚙️ Солвър ")
        f = self._make_scrollable_frame(tab)
        f.columnconfigure(1, weight=1)
        c = self.cfg.cvrp
        r = 0
        self._add_field(f, r, "cvrp.solver_type", "Тип солвър:", c.solver_type,
                         "combo", ["pyvrp", "or_tools"]); r += 1
        self._add_field(f, r, "cvrp.time_limit_seconds", "Време за решение (сек):", c.time_limit_seconds); r += 1
        self._add_field(f, r, "cvrp.allow_customer_skipping", "Пропускане на клиенти:", c.allow_customer_skipping, "bool"); r += 1
        self._add_field(f, r, "cvrp.distance_penalty_disjunction", "Глоба за пропускане:", c.distance_penalty_disjunction); r += 1

        ttk.Separator(f, orient="horizontal").grid(row=r, column=0, columnspan=3, sticky="we", pady=8); r += 1
        ttk.Label(f, text="OR-Tools настройки:", font=("", 9, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", padx=6); r += 1

        self._add_field(f, r, "cvrp.first_solution_strategy", "First solution:", c.first_solution_strategy,
                         "combo", ["AUTOMATIC", "PATH_CHEAPEST_ARC", "SAVINGS", "SWEEP", "CHRISTOFIDES",
                                   "PARALLEL_CHEAPEST_INSERTION"]); r += 1
        self._add_field(f, r, "cvrp.local_search_metaheuristic", "Метаевристика:", c.local_search_metaheuristic,
                         "combo", ["AUTOMATIC", "GUIDED_LOCAL_SEARCH", "SIMULATED_ANNEALING", "TABU_SEARCH"]); r += 1
        self._add_field(f, r, "cvrp.enable_start_time_tracking", "Проследяване старт. време:", c.enable_start_time_tracking, "bool"); r += 1
        self._add_field(f, r, "cvrp.global_start_time_minutes", "Глобално старт. време (мин):", c.global_start_time_minutes,
                         tooltip="480 = 08:00"); r += 1

        ttk.Separator(f, orient="horizontal").grid(row=r, column=0, columnspan=3, sticky="we", pady=8); r += 1
        ttk.Label(f, text="Паралелно търсене (OR-Tools):", font=("", 9, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", padx=6); r += 1

        self._add_field(f, r, "cvrp.enable_parallel_solving", "Включено:", c.enable_parallel_solving, "bool"); r += 1
        self._add_field(f, r, "cvrp.num_workers", "Брой процеси:", c.num_workers,
                         tooltip="-1 = всички ядра без едно"); r += 1
        self._add_list_field(f, r, "cvrp.parallel_first_solution_strategies",
                             "First solution стратегии:", c.parallel_first_solution_strategies); r += 1
        self._add_list_field(f, r, "cvrp.parallel_local_search_metaheuristics",
                             "Метаевристики:", c.parallel_local_search_metaheuristics); r += 1

    # ── Tab: Локации ─────────────────────────────────────────

    def _add_locations_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text=" 📍 Локации ")
        f = self._make_scrollable_frame(tab)
        f.columnconfigure(1, weight=1)
        loc = self.cfg.locations
        r = 0
        self._add_field(f, r, "locations.depot_location", "Главно депо (lat, lon):",
                         f"{loc.depot_location[0]}, {loc.depot_location[1]}"); r += 1
        self._add_field(f, r, "locations.center_location", "Център (lat, lon):",
                         f"{loc.center_location[0]}, {loc.center_location[1]}"); r += 1
        self._add_field(f, r, "locations.vratza_depot_location", "Враца депо (lat, lon):",
                         f"{loc.vratza_depot_location[0]}, {loc.vratza_depot_location[1]}"); r += 1
        self._add_field(f, r, "locations.center_zone_radius_km", "Радиус център зона (км):", loc.center_zone_radius_km); r += 1
        self._add_field(f, r, "locations.enable_center_zone_priority", "Приоритет център зона:", loc.enable_center_zone_priority, "bool"); r += 1
        self._add_field(f, r, "locations.enable_center_zone_restrictions", "Ограничения за център:", loc.enable_center_zone_restrictions, "bool"); r += 1
        self._add_field(f, r, "locations.discount_center_bus", "Отстъпка CENTER_BUS:", loc.discount_center_bus,
                         tooltip="0.5 = плаща 50% от разстоянието"); r += 1

        ttk.Separator(f, orient="horizontal").grid(row=r, column=0, columnspan=3, sticky="we", pady=8); r += 1
        ttk.Label(f, text="Глоби за влизане в център зоната:", font=("", 9, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", padx=6); r += 1
        self._add_field(f, r, "locations.internal_bus_center_penalty", "Вътрешен бус:", loc.internal_bus_center_penalty); r += 1
        self._add_field(f, r, "locations.external_bus_center_penalty", "Външен бус:", loc.external_bus_center_penalty); r += 1
        self._add_field(f, r, "locations.special_bus_center_penalty", "Специален бус:", loc.special_bus_center_penalty); r += 1
        self._add_field(f, r, "locations.vratza_bus_center_penalty", "Враца бус:", loc.vratza_bus_center_penalty); r += 1

        ttk.Separator(f, orient="horizontal").grid(row=r, column=0, columnspan=3, sticky="we", pady=8); r += 1
        ttk.Label(f, text="Градски трафик:", font=("", 9, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", padx=6); r += 1
        self._add_field(f, r, "locations.enable_city_traffic_adjustment", "Корекция за трафик:", loc.enable_city_traffic_adjustment, "bool"); r += 1
        self._add_field(f, r, "locations.city_center_coords", "Център на трафик зона (lat, lon):",
                         f"{loc.city_center_coords[0]}, {loc.city_center_coords[1]}"); r += 1
        self._add_field(f, r, "locations.city_traffic_radius_km", "Радиус трафик (км):", loc.city_traffic_radius_km); r += 1
        self._add_field(f, r, "locations.city_traffic_duration_multiplier", "Множител за време:", loc.city_traffic_duration_multiplier,
                         tooltip="1.4 = +40% заради трафик"); r += 1

    # ── Tab: Изходни данни ───────────────────────────────────

    def _add_output_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text=" 📄 Изходни данни ")
        f = self._make_scrollable_frame(tab)
        f.columnconfigure(1, weight=1)
        out = self.cfg.output
        r = 0

        ttk.Label(f, text="Карта:", font=("", 9, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", padx=6); r += 1
        self._add_field(f, r, "output.enable_interactive_map", "Генериране на карта:", out.enable_interactive_map, "bool"); r += 1
        self._add_field(f, r, "output.map_output_file", "Файл карта:", out.map_output_file); r += 1
        self._add_field(f, r, "output.routes_output_dir", "Директория HTML маршрути:", out.routes_output_dir,
                         tooltip="Отделни HTML файлове за всеки маршрут"); r += 1

        ttk.Separator(f, orient="horizontal").grid(row=r, column=0, columnspan=3, sticky="we", pady=8); r += 1
        ttk.Label(f, text="Excel:", font=("", 9, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", padx=6); r += 1
        self._add_field(f, r, "output.excel_output_dir", "Директория Excel:", out.excel_output_dir); r += 1
        self._add_field(f, r, "output.routes_excel_file", "Файл маршрути:", out.routes_excel_file); r += 1
        self._add_field(f, r, "output.warehouse_excel_file", "Файл склад:", out.warehouse_excel_file); r += 1
        self._add_field(f, r, "output.efficiency_excel_file", "Файл ефективност:", out.efficiency_excel_file); r += 1

        ttk.Separator(f, orient="horizontal").grid(row=r, column=0, columnspan=3, sticky="we", pady=8); r += 1
        ttk.Label(f, text="CSV:", font=("", 9, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", padx=6); r += 1
        self._add_field(f, r, "output.csv_output_file", "Файл CSV:", out.csv_output_file); r += 1

        ttk.Separator(f, orient="horizontal").grid(row=r, column=0, columnspan=3, sticky="we", pady=8); r += 1
        ttk.Label(f, text="Графики:", font=("", 9, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", padx=6); r += 1
        self._add_field(f, r, "output.enable_charts", "Генериране на графики:", out.enable_charts, "bool"); r += 1
        self._add_field(f, r, "output.charts_output_dir", "Директория графики:", out.charts_output_dir); r += 1

    # ── Tab: Планировчик ────────────────────────────────────

    TASK_NAME = "CVRP_Optimizer_Auto"

    def _add_scheduler_tab(self, nb):
        tab = ttk.Frame(nb)
        nb.add(tab, text=" 🕒 Автоматично стартиране ")
        f = ttk.Frame(tab)
        f.pack(fill="both", expand=True, padx=12, pady=12)
        f.columnconfigure(1, weight=1)
        r = 0

        ttk.Label(f, text="Автоматично стартиране:", font=("", 10, "bold")).grid(
            row=r, column=0, columnspan=2, sticky="w", pady=(0, 8)); r += 1

        ttk.Label(f, text="Час (ЧЧ:ММ):", anchor="w").grid(row=r, column=0, sticky="w", pady=3)
        self._sched_time = tk.StringVar(value="17:01")
        ttk.Entry(f, textvariable=self._sched_time, width=8).grid(row=r, column=1, sticky="w", pady=3)
        r += 1

        ttk.Label(f, text="Дни:", anchor="nw").grid(row=r, column=0, sticky="nw", pady=3)
        days_frame = ttk.Frame(f)
        days_frame.grid(row=r, column=1, sticky="w", pady=3)
        self._sched_days = {}
        day_names = [("ПН", "MON"), ("ВТ", "TUE"), ("СР", "WED"),
                     ("ЧТ", "THU"), ("ПТ", "FRI"), ("СБ", "SAT"), ("НД", "SUN")]
        for i, (bg, en) in enumerate(day_names):
            var = tk.BooleanVar(value=(i < 5))  # Mon-Fri by default
            cb = ttk.Checkbutton(days_frame, text=bg, variable=var)
            cb.pack(side="left", padx=3)
            self._sched_days[en] = var
        r += 1

        r += 1  # spacer
        btn_frame = ttk.Frame(f)
        btn_frame.grid(row=r, column=0, columnspan=2, sticky="w", pady=12)
        ttk.Button(btn_frame, text="✅ Създай задача", command=self._create_scheduled_task).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="🗑️ Премахни задача", command=self._remove_scheduled_task).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="🔄 Провери статус", command=self._check_task_status).pack(side="left", padx=4)
        r += 1

        ttk.Separator(f, orient="horizontal").grid(row=r, column=0, columnspan=2, sticky="we", pady=8); r += 1
        self._sched_status = tk.Text(f, width=70, height=8, wrap="word", state="disabled",
                                      background="#f5f5f5")
        self._sched_status.grid(row=r, column=0, columnspan=2, sticky="we", pady=4)
        r += 1

        ttk.Label(f, text="Използва Windows Task Scheduler (schtasks).",
                  foreground="gray", font=("", 8)).grid(row=r, column=0, columnspan=2, sticky="w")

        # Auto-check status on load
        self.root.after(300, self._check_task_status)

    def _get_program_command(self):
        """Връща команда за стартиране, подходяща за schtasks и локално изпълнение"""
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            batch_path = os.path.join(exe_dir, "start_cvrp.bat")
            if os.path.isfile(batch_path):
                return f'cmd /c ""{batch_path}""', exe_dir
            return f'"{sys.executable}"', exe_dir

        exe = os.path.abspath(os.path.join(_base_dir, "..", "dist", "CVRP_Optimizer.exe"))
        if os.path.isfile(exe):
            batch_path = os.path.join(os.path.dirname(exe), "start_cvrp.bat")
            if os.path.isfile(batch_path):
                return f'cmd /c ""{batch_path}""', os.path.dirname(exe)
            return f'"{exe}"', os.path.dirname(exe)

        main_py = os.path.join(_base_dir, "main.py")
        return f'"{sys.executable}" "{main_py}"', _base_dir

    def _set_status(self, text):
        self._sched_status.configure(state="normal")
        self._sched_status.delete("1.0", "end")
        self._sched_status.insert("1.0", text)
        self._sched_status.configure(state="disabled")

    def _create_scheduled_task(self):
        import subprocess
        time_str = self._sched_time.get().strip()
        if not time_str or ":" not in time_str:
            messagebox.showwarning("Грешка", "Въведете час във формат ЧЧ:ММ")
            return

        selected = [en for en, var in self._sched_days.items() if var.get()]
        if not selected:
            messagebox.showwarning("Грешка", "Изберете поне един ден.")
            return

        days_str = ",".join(selected)
        prog, workdir = self._get_program_command()

        # Remove existing task first (ignore errors)
        subprocess.run(
            ["schtasks", "/Delete", "/TN", self.TASK_NAME, "/F"],
            capture_output=True, creationflags=0x08000000
        )

        cmd = [
            "schtasks", "/Create",
            "/TN", self.TASK_NAME,
            "/TR", prog,
            "/SC", "WEEKLY",
            "/D", days_str,
            "/ST", time_str,
            "/F",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=0x08000000)
        if result.returncode == 0:
            self._set_status(f"Задачата е създадена.\n"
                             f"Име: {self.TASK_NAME}\n"
                             f"Час: {time_str}\n"
                             f"Дни: {days_str}\n"
                             f"Команда: {prog}")
            messagebox.showinfo("Готово", f"Задачата '{self.TASK_NAME}' е създадена.")
        else:
            err = result.stderr.strip() or result.stdout.strip()
            self._set_status(f"Грешка при създаване:\n{err}")
            messagebox.showerror("Грешка", f"Не може да се създаде задачата:\n{err}")

    def _remove_scheduled_task(self):
        import subprocess
        result = subprocess.run(
            ["schtasks", "/Delete", "/TN", self.TASK_NAME, "/F"],
            capture_output=True, text=True, creationflags=0x08000000
        )
        if result.returncode == 0:
            self._set_status("Задачата е премахната.")
            messagebox.showinfo("Готово", f"Задачата '{self.TASK_NAME}' е премахната.")
        else:
            err = result.stderr.strip() or result.stdout.strip()
            self._set_status(f"Грешка при премахване:\n{err}")

    def _check_task_status(self):
        import subprocess
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", self.TASK_NAME, "/FO", "LIST", "/V"],
            capture_output=True, text=True, creationflags=0x08000000
        )
        if result.returncode == 0:
            self._set_status(f"Задачата съществува:\n{result.stdout.strip()}")
        else:
            self._set_status("Няма създадена задача за автоматично стартиране.")

    # ── Save logic ───────────────────────────────────────────

    def _collect_values(self) -> dict:
        """Събира стойности от всички уиджети"""
        values = {}
        for key, widget in self.widgets.items():
            if isinstance(widget, tk.Text):
                values[key] = widget.get("1.0", "end-1c")
            else:
                values[key] = widget.get()
        return values

    def _apply_to_config_file(self, values: dict):
        """Записва промените директно в config.py чрез текстова замяна"""
        config_path = os.path.join(_base_dir, "config.py")
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # ─── Input fields ───
        field_map = {
            "input.input_source": ("input_source", "str"),
            "input.excel_file_path": ("excel_file_path", "path"),
            "input.json_url": ("json_url", "str"),
            "input.json_override_date": ("json_override_date", "str"),
            "input.json_timeout_seconds": ("json_timeout_seconds", "int"),
            "input.json_gps_field": ("json_gps_field", "str"),
            "input.json_client_id_field": ("json_client_id_field", "str"),
            "input.json_client_name_field": ("json_client_name_field", "str"),
            "input.json_volume_field": ("json_volume_field", "str"),
            "input.json_document_field": ("json_document_field", "str"),
            "input.gps_column": ("gps_column", "str"),
            "input.client_id_column": ("client_id_column", "str"),
            "input.client_name_column": ("client_name_column", "str"),
            "input.volume_column": ("volume_column", "str"),
            "input.document_column": ("document_column", "str"),
            # Warehouse
            "warehouse.enable_warehouse": ("enable_warehouse", "bool"),
            "warehouse.sort_by_volume": ("sort_by_volume", "bool"),
            "warehouse.sort_by_distance": ("sort_by_distance", "bool"),
            "warehouse.check_max_bus_capacity": ("check_max_bus_capacity", "bool"),
            "warehouse.max_bus_customer_volume": ("max_bus_customer_volume", "float"),
            "warehouse.capacity_toleranse": ("capacity_toleranse", "float"),
            # CVRP
            "cvrp.solver_type": ("solver_type", "str"),
            "cvrp.time_limit_seconds": ("time_limit_seconds", "int"),
            "cvrp.allow_customer_skipping": ("allow_customer_skipping", "bool"),
            "cvrp.distance_penalty_disjunction": ("distance_penalty_disjunction", "int"),
            "cvrp.first_solution_strategy": ("first_solution_strategy", "str"),
            "cvrp.local_search_metaheuristic": ("local_search_metaheuristic", "str"),
            "cvrp.enable_start_time_tracking": ("enable_start_time_tracking", "bool"),
            "cvrp.global_start_time_minutes": ("global_start_time_minutes", "int"),
            "cvrp.enable_parallel_solving": ("enable_parallel_solving", "bool"),
            "cvrp.num_workers": ("num_workers", "int"),
            # Locations
            "locations.center_zone_radius_km": ("center_zone_radius_km", "float"),
            "locations.enable_center_zone_priority": ("enable_center_zone_priority", "bool"),
            "locations.enable_center_zone_restrictions": ("enable_center_zone_restrictions", "bool"),
            "locations.discount_center_bus": ("discount_center_bus", "float"),
            "locations.internal_bus_center_penalty": ("internal_bus_center_penalty", "float"),
            "locations.external_bus_center_penalty": ("external_bus_center_penalty", "float"),
            "locations.special_bus_center_penalty": ("special_bus_center_penalty", "float"),
            "locations.vratza_bus_center_penalty": ("vratza_bus_center_penalty", "float"),
            "locations.enable_city_traffic_adjustment": ("enable_city_traffic_adjustment", "bool"),
            "locations.city_traffic_radius_km": ("city_traffic_radius_km", "float"),
            "locations.city_traffic_duration_multiplier": ("city_traffic_duration_multiplier", "float"),
            # Output
            "output.enable_interactive_map": ("enable_interactive_map", "bool"),
            "output.map_output_file": ("map_output_file", "path"),
            "output.routes_output_dir": ("routes_output_dir", "path"),
            "output.excel_output_dir": ("excel_output_dir", "path"),
            "output.routes_excel_file": ("routes_excel_file", "str"),
            "output.warehouse_excel_file": ("warehouse_excel_file", "str"),
            "output.efficiency_excel_file": ("efficiency_excel_file", "str"),
            "output.csv_output_file": ("csv_output_file", "path"),
            "output.enable_charts": ("enable_charts", "bool"),
            "output.charts_output_dir": ("charts_output_dir", "path"),
        }

        import re

        for gui_key, (field_name, ftype) in field_map.items():
            if gui_key not in values:
                continue
            raw_val = values[gui_key]
            content = self._replace_field_value(content, field_name, raw_val, ftype)

        # ─── List fields (parallel strategies) ───
        list_fields = {
            "cvrp.parallel_first_solution_strategies": "parallel_first_solution_strategies",
            "cvrp.parallel_local_search_metaheuristics": "parallel_local_search_metaheuristics",
        }
        for gui_key, field_name in list_fields.items():
            if gui_key in values:
                raw = values[gui_key]
                content = self._replace_list_field_value(content, field_name, raw)

        # ─── Location tuples ───
        for loc_key in ("depot_location", "center_location", "vratza_depot_location", "city_center_coords"):
            gui_key = f"locations.{loc_key}"
            if gui_key in values:
                raw = values[gui_key]
                content = self._replace_tuple_value(content, loc_key, raw)

        # ─── Vehicle fields ───
        if self.cfg.vehicles:
            for i, v in enumerate(self.cfg.vehicles):
                prefix = f"vehicle.{i}"
                vtype = v.vehicle_type.value
                content = self._replace_vehicle_field(content, vtype, i, values, prefix)

        if content != original:
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        return False

    def _replace_field_value(self, content, field_name, raw_val, ftype):
        """Замества стойността на поле в config.py"""
        import re

        if ftype == "bool":
            new_val = "True" if raw_val else "False"
            pattern = rf'({field_name}\s*(?::\s*bool\s*)?=\s*)(?:True|False)'
            content = re.sub(pattern, rf'\g<1>{new_val}', content)
        elif ftype == "int":
            try:
                val = int(raw_val)
                pattern = rf'({field_name}\s*(?::\s*int\s*)?=\s*)-?\d+'
                content = re.sub(pattern, rf'\g<1>{val}', content)
            except (ValueError, TypeError):
                pass
        elif ftype == "float":
            try:
                val = float(raw_val)
                pattern = rf'({field_name}\s*(?::\s*float\s*)?=\s*)[\d.]+'
                content = re.sub(pattern, rf'\g<1>{val}', content)
            except (ValueError, TypeError):
                pass
        elif ftype in ("str", "path"):
            escaped = str(raw_val).replace("\\", "\\\\").replace('"', '\\"')
            pattern = rf'({field_name}\s*(?::\s*str\s*)?=\s*(?:_abs_path\()?")[^"]*(")'
            content = re.sub(pattern, lambda match: f'{match.group(1)}{escaped}{match.group(2)}', content)
        return content

    def _replace_tuple_value(self, content, field_name, raw_val):
        """Замества tuple стойност (lat, lon) в config.py"""
        import re
        try:
            parts = [float(x.strip()) for x in raw_val.split(",")]
            if len(parts) == 2:
                new_tuple = f"({parts[0]}, {parts[1]})"
                pattern = rf'({field_name}\s*(?::\s*Tuple\[float,\s*float\]\s*)?=\s*)\([^)]+\)'
                content = re.sub(pattern, rf'\g<1>{new_tuple}', content)
        except ValueError:
            pass
        return content

    def _replace_list_field_value(self, content, field_name, raw_val):
        """Замества List[str] поле с field(default_factory=lambda: [...]) в config.py"""
        import re
        items = [line.strip() for line in raw_val.strip().splitlines() if line.strip()]
        if not items:
            return content
        items_str = ",\n        ".join(f'"{item}"' for item in items)
        new_block = f"field(default_factory=lambda: [\n        {items_str}\n    ])"
        pattern = rf'({field_name}\s*:\s*List\[str\]\s*=\s*)field\(default_factory=lambda:\s*\[.*?\]\)'
        content = re.sub(pattern, rf'\g<1>{new_block}', content, flags=re.DOTALL)
        return content

    def _replace_vehicle_field(self, content, vtype, idx, values, prefix):
        """Замества полета на превозно средство в config.py"""
        import re

        # Намираме блока на VehicleConfig за този тип
        vehicle_fields = {
            "enabled": "bool",
            "count": "int",
            "capacity": "int",
            "max_time_hours": "int",
            "service_time_minutes": "int",
            "max_customers_per_route": "optional_int",
            "start_time_minutes": "int",
        }

        # Намираме позицията на VehicleType.VTYPE в текста
        type_upper = vtype.upper()
        # Търсим VehicleConfig блока за този тип
        pattern = rf'VehicleConfig\(\s*\n\s*vehicle_type\s*=\s*VehicleType\.{type_upper}.*?(?=VehicleConfig\(|\]\s*\n|$)'
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            return content

        block_start = match.start()
        block_end = match.end()
        block = content[block_start:block_end]

        for field, ftype in vehicle_fields.items():
            gui_key = f"{prefix}.{field}"
            if gui_key not in values:
                continue
            raw = values[gui_key]

            if ftype == "bool":
                new_val = "True" if raw else "False"
                block = re.sub(rf'({field}\s*=\s*)(?:True|False)', rf'\g<1>{new_val}', block)
            elif ftype == "int":
                try:
                    val = int(raw)
                    block = re.sub(rf'({field}\s*=\s*)\d+', rf'\g<1>{val}', block)
                except (ValueError, TypeError):
                    pass
            elif ftype == "optional_int":
                raw_str = str(raw).strip()
                if raw_str == "" or raw_str.lower() == "none":
                    block = re.sub(rf'({field}\s*=\s*)(?:None|\d+)', rf'\g<1>None', block)
                else:
                    try:
                        val = int(raw_str)
                        block = re.sub(rf'({field}\s*=\s*)(?:None|\d+)', rf'\g<1>{val}', block)
                    except ValueError:
                        pass

        content = content[:block_start] + block + content[block_end:]
        return content

    # ── Actions ──────────────────────────────────────────────

    def _save(self):
        try:
            values = self._collect_values()
            changed = self._apply_to_config_file(values)
            if changed:
                messagebox.showinfo("Запазено", "Настройките са записани в config.py")
            else:
                messagebox.showinfo("Без промени", "Няма промени за записване.")
        except Exception as e:
            messagebox.showerror("Грешка", f"Грешка при запис: {e}")

    def _save_and_close(self):
        try:
            values = self._collect_values()
            self._apply_to_config_file(values)
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Грешка", f"Грешка при запис: {e}")

    def _save_and_run(self):
        try:
            values = self._collect_values()
            self._apply_to_config_file(values)
        except Exception as e:
            messagebox.showerror("Грешка", f"Грешка при запис: {e}")
            return
        
        # Стартираме програмата ПРЕДИ да затворим GUI
        import subprocess
        try:
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                exe_dir = os.path.dirname(exe_path)
                env = os.environ.copy()
                env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
                env.pop("_MEIPASS2", None)
                subprocess.Popen(
                    [exe_path],
                    cwd=exe_dir,
                    env=env,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                main_py = os.path.join(_base_dir, "main.py")
                subprocess.Popen(
                    [sys.executable, main_py],
                    cwd=_base_dir,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
        except Exception as e:
            messagebox.showerror("Грешка", f"Не мога да стартирам програмата: {e}")
            return
        
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    app = ConfigGUI()
    app.run()


if __name__ == "__main__":
    main()
