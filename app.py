import streamlit as st
import re

st.set_page_config(page_title="SCALE GridGeometry Helper", layout="centered")
st.title("Помощник SCALE: Из Geometry в GridGeometry")

placeholder_text = (
    "read geometry\n"
    "global unit 1\n"
    "  cuboid 1000 5000 0.0 2600 0.0 830.0 -470.0\n"
    "  media 0 1 1000 -999\n"
    "  hole 6 Origin x=1241 y=340 z=420\n"
    "unit 6\n"
    "  cuboid 1 10 0 60 0 200 0\n"
    "end geometry"
)

geo_text = st.text_area("Вставьте block geometry сюда:", height=300, placeholder=placeholder_text)

def parse_scale_strict_rules(text):
    x_coords = set()
    y_coords = set()
    z_coords = set()
    
    def get_axis_val(line_str, pattern):
        match = re.search(pattern, line_str, re.IGNORECASE)
        return float(match.group(1)) if match else 0.0

    # Шаг 1. Очистка от комментариев и блоков media
    cleaned_lines = []
    for line in text.split('\n'):
        # Отрезаем всё, что после одиночной кавычки (комментарии)
        if "'" in line:
            line = line.split("'")[0]
            
        # Намертво вырезаем ключевое слово media и всё, что идет после него в этой строке
        if "media" in line.lower():
            line = re.split(r"\bmedia\b", line, flags=re.IGNORECASE)[0]
            
        line_strip = line.strip()
        if line_strip:
            cleaned_lines.append(line_strip)

    # Шаг 2. Распил текста на блоки юнитов
    global_lines = []
    unit_blocks = {}
    current_unit_id = None

    for line in cleaned_lines:
        line_lower = line.lower()
        if "read geometry" in line_lower or "end geometry" in line_lower:
            continue
            
        if "unit" in line_lower and "global" not in line_lower:
            nums = [int(n) for n in re.findall(r"\d+", line_lower)]
            if nums:
                current_unit_id = nums[-1]
                unit_blocks[current_unit_id] = []
                continue
                
        if current_unit_id is not None:
            unit_blocks[current_unit_id].append(line)
        else:
            global_lines.append(line)

    def get_clean_numbers(line_str):
        parts = re.split(r"origin|rotate", line_str, re.IGNORECASE)
        return [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", parts[0])]

    def process_shape(shape_type, nums, h_ox, h_oy, h_oz, l_ox, l_oy, l_oz):
        total_x = h_ox + l_ox
        total_y = h_oy + l_oy
        total_z = h_oz + l_oz
        
        if shape_type == 'cuboid' and len(nums) >= 7:
            coords = nums[1:7]
            x_coords.update([round(coords[0] + total_x, 1), round(coords[1] + total_x, 1)])
            y_coords.update([round(coords[2] + total_y, 1), round(coords[3] + total_y, 1)])
            z_coords.update([round(coords[4] + total_z, 1), round(coords[5] + total_z, 1)])
            
        elif shape_type == 'cylinder' and len(nums) >= 4:
            r, h_max, h_min = nums[1], nums[2], nums[3]
            axis = 'z'
            if 'x' in shape_type: axis = 'x'
            elif 'y' in shape_type: axis = 'y'
            
            if axis == 'z':
                x_coords.update([round(total_x + r, 1), round(total_x - r, 1)])
                y_coords.update([round(total_y + r, 1), round(total_y - r, 1)])
                z_coords.update([round(h_max + total_z, 1), round(h_min + total_z, 1)])
            elif axis == 'x':
                x_coords.update([round(h_max + total_x, 1), round(h_min + total_x, 1)])
                y_coords.update([round(total_y + r, 1), round(total_y - r, 1)])
                z_coords.update([round(total_z + r, 1), round(total_z - r, 1)])
            elif axis == 'y':
                x_coords.update([round(total_x + r, 1), round(total_x - r, 1)])
                y_coords.update([round(h_max + total_y, 1), round(h_min + total_y, 1)])
                z_coords.update([round(total_z + r, 1), round(total_z - r, 1)])
                
        elif shape_type == 'sphere' and len(nums) >= 2:
            r = nums[1]
            x_coords.update([round(total_x + r, 1), round(total_x - r, 1)])
            y_coords.update([round(total_y + r, 1), round(total_y - r, 1)])
            z_coords.update([round(total_oz + r, 1), round(total_oz - r, 1)])

    # Шаг 3. Расчет
    for line in global_lines:
        line_lower = line.lower()
        l_ox = get_axis_val(line_lower, r"origin\s+x=([-+]?\d*\.\d+|\d+)")
        l_oy = get_axis_val(line_lower, r"origin\s+y=([-+]?\d*\.\d+|\d+)")
        l_oz = get_axis_val(line_lower, r"origin\s+z=([-+]?\d*\.\d+|\d+)")
        
        nums = get_clean_numbers(line)
        
        if "cuboid" in line_lower:
            process_shape('cuboid', nums, 0, 0, 0, l_ox, l_oy, l_oz)
        elif "cylinder" in line_lower:
            process_shape('cylinder', nums, 0, 0, 0, l_ox, l_oy, l_oz)
        elif "sphere" in line_lower:
            process_shape('sphere', nums, 0, 0, 0, l_ox, l_oy, l_oz)
            
        elif "hole" in line_lower:
            hole_match = re.search(r"hole\s+(\d+)", line_lower)
            if hole_match:
                h_id = int(hole_match.group(1))
                if h_id in unit_blocks:
                    for u_line in unit_blocks[h_id]:
                        u_line_lower = u_line.lower()
                        loc_ox = get_axis_val(u_line_lower, r"origin\s+x=([-+]?\d*\.\d+|\d+)")
                        loc_oy = get_axis_val(u_line_lower, r"origin\s+y=([-+]?\d*\.\d+|\d+)")
                        loc_oz = get_axis_val(u_line_lower, r"origin\s+z=([-+]?\d*\.\d+|\d+)")
                        
                        u_nums = get_clean_numbers(u_line)
                        if "cuboid" in u_line_lower:
                            process_shape('cuboid', u_nums, l_ox, l_oy, l_oz, loc_ox, loc_oy, loc_oz)
                        elif "cylinder" in u_line_lower:
                            process_shape('cylinder', u_nums, l_ox, l_oy, l_oz, loc_ox, loc_oy, loc_oz)
                        elif "sphere" in u_line_lower:
                            process_shape('sphere', u_nums, l_ox, l_oy, l_oz, loc_ox, loc_oy, loc_oz)

    return sorted(list(x_coords), reverse=True), sorted(list(y_coords), reverse=True), sorted(list(z_coords), reverse=True)

if geo_text:
    x_s, y_s, z_s = parse_scale_strict_rules(geo_text)
    
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
