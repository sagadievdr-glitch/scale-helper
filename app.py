import streamlit as st
import re

st.set_page_config(page_title="SCALE GridGeometry Helper", layout="centered")
st.title("Помощник SCALE: Из Geometry в GridGeometry")

# 1. Возвращаем подсказку в окно ввода с наглядной структурой
placeholder_text = (
    "read geometry\n"
    "unit 1\n"
    "  cuboid 102 135.4 0 383.5 0 151 0 origin x=151 y=781\n"
    "  hole 6 Origin x=646 y=100\n"
    "unit 6\n"
    "  cuboid 1 60 0 200 0 10 0\n"
    "end geometry"
)

geo_text = st.text_area("Вставьте блок geometry сюда:", height=300, placeholder=placeholder_text)

def parse_scale_unlimited_units(text):
    x_coords = set()
    y_coords = set()
    z_coords = set()
    
    lines = text.split('\n')
    
    # Структуры для хранения данных
    unit_bodies = {}  # Тела внутри юнитов: {unit_id: [ (type, numbers, local_origin), ... ]}
    global_holes = []  # Список всех вызовов hole в основном пространстве или глобальном юните
    
    current_unit = None
    
    # Регулярные выражения для поиска origin
    def extract_origin(line_str):
        ox = float(re.search(r"origin\s+x=([-+]?\d*\.\d+|\d+)", line_str, re.IGNORECASE).group(1)) if re.search(r"origin\s+x=", line_str, re.IGNORECASE) else 0.0
        oy = float(re.search(r"origin\s+y=([-+]?\d*\.\d+|\d+)", line_str, re.IGNORECASE).group(1)) if re.search(r"origin\s+y=", line_str, re.IGNORECASE) else 0.0
        oz = float(re.search(r"origin\s+z=([-+]?\d*\.\d+|\d+)", line_str, re.IGNORECASE).group(1)) if re.search(r"origin\s+z=", line_str, re.IGNORECASE) else 0.0
        return ox, oy, oz

    # Шаг 1: Сканируем весь текст и собираем базу данных по ВСЕМ юнитам
    for line in lines:
        line_clean = line.strip()
        line_lower = line_clean.lower()
        
        if not line_clean or line_clean.startswith("'") or "read geometry" in line_lower or "end geometry" in line_lower:
            continue
            
        # Отслеживаем объявление юнитов
        if line_lower.startswith("unit"):
            nums = [int(n) for n in re.findall(r"\d+", line_lower)]
            if nums:
                current_unit = nums[0]
                if current_unit not in unit_bodies:
                    unit_bodies[current_unit] = []
            continue
        elif line_lower.startswith("end") and "geometry" not in line_lower:
            current_unit = None
            continue
            
        # Сбор геометрических тел или hole внутри юнитов или глобально
        numbers = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", line_lower)]
        
        if "cuboid" in line_lower:
            ox, oy, oz = extract_origin(line_lower)
            if current_unit is not None:
                unit_bodies[current_unit].append(('cuboid', numbers, (ox, oy, oz)))
            else:
                # Если cuboid объявлен вне юнитов (в глобальном пространстве)
                unit_bodies.setdefault(0, []).append(('cuboid', numbers, (ox, oy, oz)))
                
        elif "hole" in line_lower:
            hole_id_match = re.search(r"hole\s+(\d+)", line_lower)
            if hole_id_match:
                h_id = int(hole_id_match.group(1))
                ox, oy, oz = extract_origin(line_lower)
                if current_unit is not None:
                    # Запоминаем, что текущий юнит ссылается на другой юнит через hole
                    unit_bodies[current_unit].append(('hole', h_id, (ox, oy, oz)))
                else:
                    global_holes.append((h_id, (ox, oy, oz)))

    # Функция для добавления координат кубоида со смещениями
    def add_cuboid_coords(numbers, total_ox, total_oy, total_oz):
        if len(numbers) < 7:
            return
        # SCALE cuboid: ID +X -X +Y -Y +Z -Z
        x_max = numbers[1] + total_ox
        x_min = numbers[2] + total_ox
        y_max = numbers[3] + total_oy
        y_min = numbers[4] + total_oy
        z_max = numbers[5] + total_oz
        z_min = numbers[6] + total_oz
        
        x_coords.update([round(x_max, 1), round(x_min, 1)])
        y_coords.update([round(y_max, 1), round(y_min, 1)])
        z_coords.update([round(z_max, 1), round(z_min, 1)])

    # Шаг 2: Рекурсивный обход юнитов для раскрытия всех вложенностей hole
    def process_unit(u_id, accumulated_origin=(0.0, 0.0, 0.0)):
        if u_id not in unit_bodies:
            return
            
        base_ox, base_oy, base_oz = accumulated_origin
        
        for item_type, data, local_orig in unit_bodies[u_id]:
            loc_ox, loc_oy, loc_oz = local_orig
            total_ox = base_ox + loc_ox
            total_oy = base_oy + loc_oy
            total_oz = base_oz + loc_oz
            
            if item_type == 'cuboid':
                add_cuboid_coords(data, total_ox, total_oy, total_oz)
            elif item_type == 'hole':
                # Рекурсивно заходим в дочерний юнит hole, передавая накопленное смещение
                child_unit_id = data
                process_unit(child_unit_id, (total_ox, total_oy, total_oz))

    # Шаг 3: Запускаем расчет для всех глобальных объектов и базовых юнитов
    # Сначала обрабатываем глобальный виртуальный юнит 0, если он есть
    if 0 in unit_bodies:
        process_unit(0)
        
    # Обрабатываем глобальные hole
    for h_id, h_orig in global_holes:
        process_unit(h_id, h_orig)
        
    # Для надежности: если какие-то юниты не были вызваны через hole, но они есть в файле, 
    # добавим их локальные координаты (как базовые опорные точки)
    for u_id in unit_bodies.keys():
        if u_id != 0:
            process_unit(u_id)

    return sorted(list(x_coords), reverse=True), sorted(list(y_coords), reverse=True), sorted(list(z_coords), reverse=True)

if geo_text:
    x_s, y_s, z_s = parse_scale_unlimited_units(geo_text)
    
    if not x_s and not y_s and not z_s:
        st.warning("Не удалось извлечь координаты. Проверьте формат блока geometry.")
    else:
        result = "    gridGeometry 2\n"
        
        if x_s:
            result += f"        xlinear {len(x_s)} {x_s[0]} {x_s[-1]}\n"
            result += f"             xplanes {' '.join(map(str, x_s))} end\n"
        if y_s:
            result += f"        ylinear {len(y_s)} {y_s[0]} {y_s[-1]}\n"
            result += f"             yplanes {' '.join(map(str, y_s))} end\n"
        if z_s:
            result += f"        zlinear {len(z_s)} {z_s[0]} {z_s[-1]}\n"
            result += f"             zplanes {' '.join(map(str, z_s))} end\n"
            
        result += "    end gridGeometry"
        
        st.subheader("Результат:")
        st.code(result, language="text")
