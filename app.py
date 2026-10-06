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

def parse_scale_precise_shapes(text):
    x_coords = set()
    y_coords = set()
    z_coords = set()
    
    def get_axis_val(line_str, prefix):
        match = re.search(r"\b" + prefix + r"\s*=\s*([-+]?\d*\.\d+|\d+)", line_str, re.IGNORECASE)
        return float(match.group(1)) if match else None

    # Шаг 1. Очистка от комментариев и блоков media
    cleaned_lines = []
    for line in text.split('\n'):
        if "'" in line:
            line = line.split("'")[0]
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
        return [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", parts)]

    # Точность расчетов изменена до сотых долей (round(..., 2))
    def add_cuboid(nums, tx, ty, tz):
        coords = nums[1:] if len(nums) >= 7 else numbers
        if len(coords) >= 6:
            x_coords.update([round(coords[0] + tx, 2), round(coords[1] + tx, 2)])
            y_coords.update([round(coords[2] + ty, 2), round(coords[3] + ty, 2)])
            z_coords.update([round(coords[4] + tz, 2), round(coords[5] + tz, 2)])

    def add_cylinder(nums, is_x, is_y, tx, ty, tz):
        if len(nums) >= 4:
            r = nums[1]
            h_max = nums[2]
            h_min = nums[3]
            
            if not is_x and not is_y: # Ось Z
                x_coords.update([round(tx + r, 2), round(tx - r, 2)])
                y_coords.update([round(ty + r, 2), round(ty - r, 2)])
                z_coords.update([round(h_max + tz, 2), round(h_min + tz, 2)])
            elif is_x:
                x_coords.update([round(h_max + tx, 2), round(h_min + tx, 2)])
                y_coords.update([round(ty + r, 2), round(ty - r, 2)])
                z_coords.update([round(tz + r, 2), round(tz - r, 2)])
            elif is_y:
                x_coords.update([round(tx + r, 2), round(tx - r, 2)])
                y_coords.update([round(h_max + ty, 2), round(h_min + ty, 2)])
                z_coords.update([round(tz + r, 2), round(tz - r, 2)])

    def add_sphere(nums, tx, ty, tz):
        if len(nums) >= 2:
            r = nums[1]
            x_coords.update([round(tx + r, 2), round(tx - r, 2)])
            y_coords.update([round(ty + r, 2), round(ty - r, 2)])
            z_coords.update([round(tz + r, 2), round(tz - r, 2)])

    def parse_line_elements(line, h_ox, h_oy, h_oz):
        line_lower = line.lower()
        val_x = get_axis_val(line_lower, 'x')
        val_y = get_axis_val(line_lower, 'y')
        val_z = get_axis_val(line_lower, 'z')
        
        l_ox = val_x if val_x is not None else 0.0
        l_oy = val_y if val_y is not None else 0.0
        l_oz = val_z if val_z is not None else 0.0
        
        tx, ty, tz = h_ox + l_ox, h_oy + l_oy, h_oz + l_oz
        nums = get_clean_numbers(line)
        
        if "cuboid" in line_lower:
            add_cuboid(nums, tx, ty, tz)
        elif "cylinder" in line_lower:
            add_cylinder(nums, 'x' in line_lower, 'y' in line_lower, tx, ty, tz)
        elif "sphere" in line_lower:
            add_sphere(nums, tx, ty, tz)
        elif "hole" in line_lower:
            hole_match = re.search(r"hole\s+(\d+)", line_lower)
            if hole_match:
                h_id = int(hole_match.group(1))
                if h_id in unit_blocks:
                    for u_line in unit_blocks[h_id]:
                        parse_line_elements(u_line, tx, ty, tz)

    for line in global_lines:
        parse_line_elements(line, 0, 0, 0)

    return sorted(list(x_coords), reverse=True), sorted(list(y_coords), reverse=True), sorted(list(z_coords), reverse=True)

if geo_text:
    x_s, y_s, z_s = parse_scale_precise_shapes(geo_text)
    
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

