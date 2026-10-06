import streamlit as st
import re

st.set_page_config(page_title="SCALE GridGeometry Helper", layout="centered")
st.title("Помощник SCALE: Из Geometry в GridGeometry")

placeholder_text = (
    "read geometry\n"
    "global unit 1\n"
    "  cuboid 1000 5000 0.0 2600 0.0 830.0 -470.0\n"
    "  hole 6 Origin x=1241 y=340 z=420\n"
    "unit 6\n"
    "  cuboid 1 10 0 60 0 200 0\n"
    "end geometry"
)

geo_text = st.text_area("Вставьте блок geometry сюда:", height=300, placeholder=placeholder_text)

def parse_scale_final_fixed(text):
    x_coords = set()
    y_coords = set()
    z_coords = set()
    
    lines = text.split('\n')
    
    # Хранилище объектов для каждого юнита
    # {unit_id: [ {'type': 'cuboid', 'numbers': [...]}, ... ]}
    unit_storage = {}
    current_unit = None
    
    # 1. Первый проход: собираем базу данных по всем фигурам внутри юнитов
    for line in lines:
        line_clean = line.strip()
        line_lower = line_clean.lower()
        
        if not line_clean or line_clean.startswith("'") or "read geometry" in line_lower or "end geometry" in line_lower:
            continue
            
        # Определяем границы юнитов
        if "unit" in line_lower:
            nums = [int(n) for n in re.findall(r"\d+", line_lower)]
            if nums:
                current_unit = nums[-1]
                if current_unit not in unit_storage:
                    unit_storage[current_unit] = []
            continue
            
        # Извлекаем параметры origin, если они прописаны прямо в строке фигуры
        ox = float(re.search(r"origin\s+x=([-+]?\d*\.\d+|\d+)", line_lower).group(1)) if re.search(r"origin\s+x=", line_lower) else 0.0
        oy = float(re.search(r"origin\s+y=([-+]?\d*\.\d+|\d+)", line_lower).group(1)) if re.search(r"origin\s+y=", line_lower) else 0.0
        oz = float(re.search(r"origin\s+z=([-+]?\d*\.\d+|\d+)", line_lower).group(1)) if re.search(r"origin\s+z=", line_lower) else 0.0

        # Чистим строку от параметров сдвига, чтобы извлечь только размеры фигуры
        clean_line = re.split(r"origin|rotate", line_lower)[0]
        numbers = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", clean_line)]
        
        if not numbers:
            continue

        # Безопасно сохраняем данные в текущий юнит
        u_key = current_unit if current_unit is not None else 1
        unit_storage.setdefault(u_key, [])

        if "cuboid" in line_lower and len(numbers) >= 7:
            unit_storage[u_key].append({'type': 'cuboid', 'data': numbers[1:], 'offset': (ox, oy, oz)})
        elif "cylinder" in line_lower and len(numbers) >= 4:
            axis = 'z'
            if 'x' in line_lower.split('cylinder')[0]: axis = 'x'
            elif 'y' in line_lower.split('cylinder')[0]: axis = 'y'
            unit_storage[u_key].append({'type': 'cylinder', 'data': {'axis': axis, 'r': numbers[1], 'h_max': numbers[2], 'h_min': numbers[3]}, 'offset': (ox, oy, oz)})
        elif "sphere" in line_lower and len(numbers) >= 2:
            unit_storage[u_key].append({'type': 'sphere', 'data': numbers[1], 'offset': (ox, oy, oz)})
        elif "hole" in line_lower:
            hole_id_match = re.search(r"hole\s+(\d+)", line_lower)
            if hole_id_match:
                h_id = int(hole_id_match.group(1))
                unit_storage[u_key].append({'type': 'hole', 'data': h_id, 'offset': (ox, oy, oz)})

    # 2. Функция для вычисления мировых координат объекта с учетом накопленного сдвига hole
    def calculate_shape_points(shape_type, data, total_ox, total_oy, total_oz):
        if shape_type == 'cuboid' and len(data) >= 6:
            # SCALE кубоид: X_max, X_min, Y_max, Y_min, Z_max, Z_min
            x_coords.update([round(data[0] + total_ox, 1), round(data[1] + total_ox, 1)])
            y_coords.update([round(data[2] + total_oy, 1), round(data[3] + total_oy, 1)])
            z_coords.update([round(data[4] + total_oz, 1), round(data[5] + total_oz, 1)])
            
        elif shape_type == 'cylinder':
            axis = data['axis']
            r = data['r']
            h_max = data['h_max']
            h_min = data['h_min']
            
            if axis == 'z':
                x_coords.update([round(total_ox + r, 1), round(total_ox - r, 1)])
                y_coords.update([round(total_oy + r, 1), round(total_oy - r, 1)])
                z_coords.update([round(h_max + total_oz, 1), round(h_min + total_oz, 1)])
            elif axis == 'x':
                x_coords.update([round(h_max + total_ox, 1), round(h_min + total_ox, 1)])
                y_coords.update([round(total_oy + r, 1), round(total_oy - r, 1)])
                z_coords.update([round(total_oz + r, 1), round(total_oz - r, 1)])
            elif axis == 'y':
                x_coords.update([round(total_ox + r, 1), round(total_ox - r, 1)])
                y_coords.update([round(h_max + total_oy, 1), round(h_min + total_oy, 1)])
                z_coords.update([round(total_oz + r, 1), round(total_oz - r, 1)])
                
        elif shape_type == 'sphere':
            r = data
            x_coords.update([round(total_ox + r, 1), round(total_ox - r, 1)])
            y_coords.update([round(total_oy + r, 1), round(total_oy - r, 1)])
            z_coords.update([round(total_oz + r, 1), round(total_oz - r, 1)])

    # 3. Рекурсивное разворачивание дерева строго от глобального юнита 1
    def deploy_unit(u_id, current_offset=(0.0, 0.0, 0.0)):
        if u_id not in unit_storage:
            return
        
        cum_ox, cum_oy, cum_oz = current_offset
        
        for obj in unit_storage[u_id]:
            loc_ox, loc_oy, loc_oz = obj['offset']
            total_ox = cum_ox + loc_ox
            total_oy = cum_oy + loc_oy
            total_oz = cum_oz + loc_oz
            
            if obj['type'] in ['cuboid', 'cylinder', 'sphere']:
                calculate_shape_points(obj['type'], obj['data'], total_ox, total_oy, total_oz)
            elif obj['type'] == 'hole':
                deploy_unit(obj['data'], (total_ox, total_oy, total_oz))

    # Запуск от главного global unit 1 (или любого первого, если файл поврежден)
    root_id = 1 if 1 in unit_storage else (list(unit_storage.keys())[0] if unit_storage else None)
    if root_id is not None:
        deploy_unit(root_id)

    return sorted(list(x_coords), reverse=True), sorted(list(y_coords), reverse=True), sorted(list(z_coords), reverse=True)

if geo_text:
    x_s, y_s, z_s = parse_scale_final_fixed(geo_text)
    
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
