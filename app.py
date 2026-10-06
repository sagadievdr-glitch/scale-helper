import streamlit as st
import re
import math

st.set_page_config(page_title="SCALE GridGeometry Helper", page_icon="", layout="centered")
st.title("Помощник SCALE: Из Geometry в GridGeometry")
st.write("Парсер учитывает параметры **hole**, **origin** и **rotate** (поворот вокруг оси Z).")

geo_text = st.text_area("Вставьте блок geometry сюда:", height=300, placeholder="unit 1\n  cuboid 102 10 0 135.4 0 383.5 0.0 rotate a1=-37.8 origin x=151 y=781\nhole 6 Origin x=646 y=100")

def parse_geometry_advanced(text):
    x_coords = set()
    y_coords = set()
    z_coords = set()
    
    # Сначала найдем все юниты (unit) и их содержимое
    units = {}
    current_unit = None
    
    lines = text.split('\n')
    for line in lines:
        line_clean = line.strip()
        line_lower = line_clean.lower()
        
        if not line_clean or line_clean.startswith("'"):
            continue
            
        # Фиксация текущего юнита
        if line_lower.startswith("unit"):
            nums = [int(n) for n in re.findall(r"\d+", line_lower)]
            if nums:
                current_unit = nums[0]
                units[current_unit] = []
            continue
        elif line_lower.startswith("end") and "geometry" not in line_lower:
            current_unit = None
            continue
            
        if current_unit is not None:
            units[current_unit].append(line_clean)
            
    # Если юниты не оформлены явно, поместим всё в глобальный виртуальный юнит 0
    if not units:
        units[0] = [l.strip() for l in lines if l.strip() and not l.strip().startswith("'")]

    def process_cuboid(numbers, origin_x=0.0, origin_y=0.0, origin_z=0.0, angle_deg=0.0):
        # cuboid обычно имеет минимум 6 координат после ID: x_max x_min y_max y_min z_max z_min
        # В SCALE: cuboid ID +x -x +y -y +z -z
        if len(numbers) < 7:
            return
        
        x_max, x_min = numbers[1], numbers[2]
        y_max, y_min = numbers[3], numbers[4]
        z_max, z_min = numbers[5], numbers[6]
        
        # 4 базовые вершины в плоскости XY для учета поворота
        vertices = [
            (x_min, y_min),
            (x_max, y_min),
            (x_max, y_max),
            (x_min, y_max)
        ]
        
        rad = math.radians(angle_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        
        # Вращаем и смещаем вершины
        for vx, vy in vertices:
            # Матрица поворота вокруг Z (обычно a1 в SCALE — это угол на плоскости XY)
            rx = vx * cos_a - vy * sin_a + origin_x
            ry = vx * sin_a + vy * cos_a + origin_y
            x_coords.add(round(rx, 2))
            y_coords.add(round(ry, 2))
            
        # Z просто смещается по origin
        z_coords.add(round(z_min + origin_z, 2))
        z_coords.add(round(z_max + origin_z, 2))

    # Парсим основной блок построчно
    for line in lines:
        line_lower = line.strip().lower()
        if not line_lower or line_lower.startswith("'") or "read" in line_lower or "end" in line_lower:
            continue
            
        # Извлекаем все числа из строки (включая отрицательные и дробные)
        numbers = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", line_lower)]
        
        # Ищем параметры смещения и вращения
        ox = float(re.search(r"origin\s+x=([-+]?\d*\.\d+|\d+)", line_lower).group(1)) if re.search(r"origin\s+x=", line_lower) else 0.0
        oy = float(re.search(r"origin\s+y=([-+]?\d*\.\d+|\d+)", line_lower).group(1)) if re.search(r"origin\s+y=", line_lower) else 0.0
        oz = float(re.search(r"origin\s+z=([-+]?\d*\.\d+|\d+)", line_lower).group(1)) if re.search(r"origin\s+z=", line_lower) else 0.0
        
        # Угол rotate a1=...
        angle = float(re.search(r"rotate\s+a1=([-+]?\d*\.\d+|\d+)", line_lower).group(1)) if re.search(r"rotate\s+a1=", line_lower) else 0.0

        if "cuboid" in line_lower:
            process_cuboid(numbers, ox, oy, oz, angle)
            
        elif "hole" in line_lower:
            # Формат: hole H_ID Origin x=... y=... z=...
            hole_id_match = re.search(r"hole\s+(\d+)", line_lower)
            if hole_id_match:
                h_id = int(hole_id_match.group(1))
                if h_id in units:
                    # Проходим по внутренностям юнита, который вызван как hole
                    for u_line in units[h_id]:
                        u_line_lower = u_line.lower()
                        u_numbers = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", u_line_lower)]
                        if "cuboid" in u_line_lower:
                            process_cuboid(u_numbers, ox, oy, oz, angle)

    return sorted(list(x_coords)), sorted(list(y_coords)), sorted(list(z_coords))

if geo_text:
    x_s, y_s, z_s = parse_geometry_advanced(geo_text)
    
    if not x_s and not y_s and not z_s:
        st.warning("⚠️ Не удалось распознать геометрию. Проверьте синтаксис тел.")
    else:
        result = "read gridGeometry\n"
        if x_s: result += f"  xgrid = {' '.join(map(str, x_s))}\n"
        if y_s: result += f"  ygrid = {' '.join(map(str, y_s))}\n"
        if z_s: result += f"  zgrid = {' '.join(map(str, z_s))}\n"
        result += "end gridGeometry"
        
        st.subheader("Сгенерированный блок:")
        st.code(result, language="text")
