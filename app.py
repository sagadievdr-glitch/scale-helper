import streamlit as st
import re

st.set_page_config(page_title="SCALE GridGeometry Helper", layout="centered")
st.title("Помощник SCALE: Из Geometry в GridGeometry")

geo_text = st.text_area("Вставьте блок geometry сюда:", height=300, 
                        placeholder="read geometry\nunit 1\n  cuboid 102 10 0 135.4 0 383.5 0.0 rotate a1=-37.8 origin x=151 y=781\n  hole 6 Origin x=646 y=100\n\nunit 6\n  cuboid 1 10 0 60 0 200 0\nend geometry")

def parse_scale_v2(text):
    x_coords = set()
    y_coords = set()
    z_coords = set()
    
    units = {}
    current_unit = None
    
    lines = text.split('\n')
    for line in lines:
        line_clean = line.strip()
        line_lower = line_clean.lower()
        
        if not line_clean or line_clean.startswith("'"):
            continue
            
        if line_lower.startswith("unit"):
            nums = [int(n) for n in re.findall(r"\d+", line_lower)]
            if nums:
                current_unit = nums
                units[current_unit] = []
            continue
        elif line_lower.startswith("end") and "geometry" not in line_lower:
            current_unit = None
            continue
            
        if current_unit is not None:
            units[current_unit].append(line_clean)

    def get_origin(line_str):
        ox = float(re.search(r"origin\s+x=([-+]?\d*\.\d+|\d+)", line_str, re.IGNORECASE).group(1)) if re.search(r"origin\s+x=", line_str, re.IGNORECASE) else 0.0
        oy = float(re.search(r"origin\s+y=([-+]?\d*\.\d+|\d+)", line_str, re.IGNORECASE).group(1)) if re.search(r"origin\s+y=", line_str, re.IGNORECASE) else 0.0
        oz = float(re.search(r"origin\s+z=([-+]?\d*\.\d+|\d+)", line_str, re.IGNORECASE).group(1)) if re.search(r"origin\s+z=", line_str, re.IGNORECASE) else 0.0
        return ox, oy, oz

    def add_cuboid_coords(numbers, ox=0.0, oy=0.0, oz=0.0):
        if len(numbers) < 7:
            return
        x_max, x_min = numbers + ox, numbers + ox
        y_max, y_min = numbers + oy, numbers + oy
        z_max, z_min = numbers + oz, numbers + oz
        
        x_coords.update([round(x_max, 1), round(x_min, 1)])
        y_coords.update([round(y_max, 1), round(y_min, 1)])
        z_coords.update([round(z_max, 1), round(z_min, 1)])

    for line in lines:
        line_lower = line.strip().lower()
        if not line_lower or line_lower.startswith("'") or "read geometry" in line_lower or "end geometry" in line_lower:
            continue
            
        numbers = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", line_lower)]
        
        if "cuboid" in line_lower and "unit" not in line_lower:
            ox, oy, oz = get_origin(line_lower)
            add_cuboid_coords(numbers, ox, oy, oz)
            
        elif "hole" in line_lower:
            hole_id_match = re.search(r"hole\s+(\d+)", line_lower)
            if hole_id_match:
                h_id = int(hole_id_match.group(1))
                ox, oy, oz = get_origin(line_lower)
                
                if h_id in units:
                    for u_line in units[h_id]:
                        u_line_lower = u_line.lower()
                        u_numbers = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", u_line_lower)]
                        if "cuboid" in u_line_lower:
                            add_cuboid_coords(u_numbers, ox, oy, oz)

    return sorted(list(x_coords), reverse=True), sorted(list(y_coords), reverse=True), sorted(list(z_coords), reverse=True)

if geo_text:
    x_s, y_s, z_s = parse_scale_v2(geo_text)
    
    if not x_s and not y_s and not z_s:
        st.warning("Не удалось распознать геометрию. Убедитесь, что вставили описание юнитов вместе с их телами.")
    else:
        result = "    gridGeometry 2\n"
        
        if x_s:
            result += f"        xlinear {len(x_s)} {x_s} {x_s[-1]}\n"
            result += f"             xplanes {' '.join(map(str, x_s))} end\n"
        if y_s:
            result += f"        ylinear {len(y_s)} {y_s} {y_s[-1]}\n"
            result += f"             yplanes {' '.join(map(str, y_s))} end\n"
        if z_s:
            result += f"        zlinear {len(z_s)} {z_s} {z_s[-1]}\n"
            result += f"             zplanes {' '.join(map(str, z_s))} end\n"
            
        result += "    end gridGeometry"
        
        st.subheader("Результат:")
        st.code(result, language="text")
