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

def parse_scale_full_geometry(text):
    x_coords = set()
    y_coords = set()
    z_coords = set()
    
    lines = text.split('\n')
    
    unit_bodies = {}
    global_elements = []
    
    root_unit_id = 1 
    current_unit = None
    
    def extract_origin(line_str):
        ox = float(re.search(r"origin\s+x=([-+]?\d*\.\d+|\d+)", line_str, re.IGNORECASE).group(1)) if re.search(r"origin\s+x=", line_str, re.IGNORECASE) else 0.0
        oy = float(re.search(r"origin\s+y=([-+]?\d*\.\d+|\d+)", line_str, re.IGNORECASE).group(1)) if re.search(r"origin\s+y=", line_str, re.IGNORECASE) else 0.0
        oz = float(re.search(r"origin\s+z=([-+]?\d*\.\d+|\d+)", line_str, re.IGNORECASE).group(1)) if re.search(r"origin\s+z=", line_str, re.IGNORECASE) else 0.0
        return ox, oy, oz

    # Шаг 1: Сбор всей базы геометрии по юнитам
    for line in lines:
        line_clean = line.strip()
        line_lower = line_clean.lower()
        
        if not line_clean or line_clean.startswith("'") or "read geometry" in line_lower or "end geometry" in line_lower:
            continue
            
        if "unit" in line_lower:
            nums = [int(n) for n in re.findall(r"\d+", line_lower)]
            if nums:
                current_unit = nums[-1]
                if "global" in line_lower:
                    root_unit_id = current_unit
                if current_unit not in unit_bodies:
                    unit_bodies[current_unit] = []
            continue
        elif line_lower.startswith("end ") and "geometry" not in line_lower:
            current_unit = None
            continue
            
        clean_body = re.split(r"origin|rotate", line_lower)[0]
        numbers = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", clean_body)]
        ox, oy, oz = extract_origin(line_lower)
        
        if "cuboid" in line_lower and len(numbers) >= 7:
            # Отбрасываем ID материала (первое число)
            element_data = ('cuboid', numbers[1:])
        elif "cylinder" in line_lower and len(numbers) >= 4:
            # Цилиндр: ID, радиус, h_max, h_min. Определяем ось по буквам x, y, z в строке
            axis = 'z'
            if 'x' in line_lower.split('cylinder')[1]: axis = 'x'
            elif 'y' in line_lower.split('cylinder')[1]: axis = 'y'
            element_data = ('cylinder', {'axis': axis, 'r': numbers[1], 'h_max': numbers[2], 'h_min': numbers[3]})
        elif "sphere" in line_lower and len(numbers) >= 2:
            # Сфера: ID, радиус
            element_data = ('sphere', numbers[1])
        elif "hole" in line_lower:
            hole_id_match = re.search(r"hole\s+(\d+)", line_lower)
            if hole_id_match:
                element_data = ('hole', int(hole_id_match.group(1)))
            else:
                continue
        else:
            continue

        if current_unit is not None:
            unit_bodies[current_unit].append((element_data[0], element_data[1], (ox, oy, oz)))
        else:
            global_elements.append((element_data[0], element_data[1], (ox, oy, oz)))

    def add_shape_coords(shape_type, data, total_ox, total_oy, total_oz):
        if shape_type == 'cuboid':
            # SCALE cuboid: X_max X_min Y_max Y_min Z_max Z_min
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

    # Шаг 2: Рекурсивный упорядоченный обход дерева юнитов
    def process_unit(u_id, accumulated_origin=(0.0, 0.0, 0.0)):
        if u_id not in unit_bodies:
            return
            
        base_ox, base_oy, base_oz = accumulated_origin
        
        for item_type, data, local_orig in unit_bodies[u_id]:
            loc_ox, loc_oy, loc_oz = local_orig
            total_ox = base_ox + loc_ox
            total_oy = base_oy + loc_oy
            total_oz = base_oz + loc_oz
            
            if item_type in ['cuboid', 'cylinder', 'sphere']:
                add_shape_coords(item_type, data, total_ox, total_oy, total_oz)
            elif item_type == 'hole':
                process_unit(data, (total_ox, total_oy, total_oz))

    # Шаг 3: Запуск расчета от корневого элемента
    for item_type, data, local_orig in global_elements:
        if item_type in ['cuboid', 'cylinder', 'sphere']:
            add_shape_coords(item_type, data, local_orig[0], local_orig[1], local_orig[2])
        elif item_type == 'hole':
            process_unit(data, local_orig)
            
    if root_unit_id in unit_bodies:
        process_unit(root_unit_id)

    return sorted(list(x_coords), reverse=True), sorted(list(y_coords), reverse=True), sorted(list(z_coords), reverse=True)

if geo_text:
    x_s, y_s, z_s = parse_scale_full_geometry(geo_text)
    
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
