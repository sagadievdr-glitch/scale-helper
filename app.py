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

def parse_scale_raw_fixed(text):
    x_coords = set()
    y_coords = set()
    z_coords = set()
    
    lines = text.split('\n')
    unit_storage = {}
    root_unit_id = 1
    current_unit = None
    
    def get_val(line_str, pattern):
        match = re.search(pattern, line_str, re.IGNORECASE)
        return float(match.group(1)) if match else 0.0

    # Шаг 1: Сбор данных построчно
    for line in lines:
        if "'" in line:
            line = line.split("'")[0]
        line_clean = line.strip()
        line_lower = line_clean.lower()
        
        if not line_clean or "read geometry" in line_lower or "end geometry" in line_lower:
            continue
            
        if "unit" in line_lower:
            nums = [int(n) for n in re.findall(r"\d+", line_lower)]
            if nums:
                current_unit = nums[-1]
                if "global" in line_lower:
                    root_unit_id = current_unit
                unit_storage[current_unit] = []
            continue
        elif line_lower.startswith("end ") and "geometry" not in line_lower:
            current_unit = None
            continue
            
        u_key = current_unit if current_unit is not None else 1
        unit_storage.setdefault(u_key, [])
        
        ox = get_val(line_lower, r"origin\s+x=([-+]?\d*\.\d+|\d+)")
        oy = get_val(line_lower, r"origin\s+y=([-+]?\d*\.\d+|\d+)")
        oz = get_val(line_lower, r"origin\s+z=([-+]?\d*\.\d+|\d+)")
        
        clean_part = re.split(r"origin|rotate|media", line_lower)[0]
        numbers = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", clean_part)]
        
        if not numbers:
            continue
            
        if "cuboid" in line_lower:
            coords = numbers[1:] if len(numbers) >= 7 else numbers
            if len(coords) >= 6:
                unit_storage[u_key].append({
                    'type': 'cuboid',
                    'data': coords[:6],
                    'offset': (ox, oy, oz)
                })
        elif "cylinder" in line_lower and len(numbers) >= 4:
            axis = 'z'
            if 'x' in line_lower.split('cylinder'): axis = 'x'
            elif 'y' in line_lower.split('cylinder'): axis = 'y'
            unit_storage[u_key].append({
                'type': 'cylinder',
                'data': {'axis': axis, 'r': numbers[-3], 'h_max': numbers[-2], 'h_min': numbers[-1]},
                'offset': (ox, oy, oz)
            })
        elif "sphere" in line_lower and len(numbers) >= 2:
            unit_storage[u_key].append({
                'type': 'sphere',
                'data': numbers[-1],
                'offset': (ox, oy, oz)
            })
        elif "hole" in line_lower:
            hole_match = re.search(r"hole\s+(\d+)", line_lower)
            if hole_match:
                unit_storage[u_key].append({
                    'type': 'hole',
                    'data': int(hole_match.group(1)),
                    'offset': (ox, oy, oz)
                })

    # Шаг 2: Рекурсивный обход дерева юнитов
    def deploy(u_id, cum_offset=(0.0, 0.0, 0.0)):
        if u_id not in unit_storage:
            return
        base_x, base_y, base_z = cum_offset
        
        for obj in unit_storage[u_id]:
            ox, oy, oz = obj['offset']
            total_x = base_x + ox
            total_oy = base_y + oy
            total_oz = base_z + oz
            
            if obj['type'] == 'cuboid':
                d = obj['data']
                # Извлекаем строго по индексам, чтобы не ломать сложение массивов
                x_coords.update([round(d[0] + total_x, 1), round(d[1] + total_x, 1)])
                y_coords.update([round(d[2] + total_oy, 1), round(d[3] + total_oy, 1)])
                z_coords.update([round(d[4] + total_oz, 1), round(d[5] + total_oz, 1)])
            elif obj['type'] == 'cylinder':
                c = obj['data']
                if c['axis'] == 'z':
                    x_coords.update([round(total_x + c['r'], 1), round(total_x - c['r'], 1)])
                    y_coords.update([round(total_oy + c['r'], 1), round(total_oy - c['r'], 1)])
                    z_coords.update([round(c['h_max'] + total_oz, 1), round(c['h_min'] + total_oz, 1)])
            elif obj['type'] == 'sphere':
                r = obj['data']
                x_coords.update([round(total_x + r, 1), round(total_x - r, 1)])
                y_coords.update([round(total_oy + r, 1), round(total_oy - r, 1)])
                z_coords.update([round(total_oz + r, 1), round(total_oz - r, 1)])
            elif obj['type'] == 'hole':
                deploy(obj['data'], (total_x, total_oy, total_oz))

    if root_unit_id in unit_storage:
        deploy(root_unit_id)
        
    return sorted(list(x_coords), reverse=True), sorted(list(y_coords), reverse=True), sorted(list(z_coords), reverse=True)

if geo_text:
    x_s, y_s, z_s = parse_scale_raw_fixed(geo_text)
    
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
