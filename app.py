import streamlit as st
import re

st.set_page_config(page_title="SCALE GridGeometry Helper", layout="centered")
st.title("Помощник SCALE: Из Geometry в GridGeometry")

geo_text = st.text_area("Вставьте блок geometry сюда:", height=300)

def parse_scale_final(text):
    x_coords = set()
    y_coords = set()
    z_coords = set()
    
    lines = text.split('\n')
    
    # Будем запоминать последние встреченные смещения hole, чтобы применять их к следующим за ними cuboid
    current_ox = 0.0
    current_oy = 0.0
    current_oz = 0.0
    
    for line in lines:
        line_clean = line.strip()
        line_lower = line_clean.lower()
        
        if not line_clean or line_clean.startswith("'") or "read geometry" in line_lower or "end geometry" in line_lower:
            continue
            
        # Если встретили hole, обновляем текущие смещения для этой зоны
        if "hole" in line_lower:
            current_ox = float(re.search(r"origin\s+x=([-+]?\d*\.\d+|\d+)", line_lower).group(1)) if re.search(r"origin\s+x=", line_lower) else 0.0
            current_oy = float(re.search(r"origin\s+y=([-+]?\d*\.\d+|\d+)", line_lower).group(1)) if re.search(r"origin\s+y=", line_lower) else 0.0
            current_oz = float(re.search(r"origin\s+z=([-+]?\d*\.\d+|\d+)", line_lower).group(1)) if re.search(r"origin\s+z=", line_lower) else 0.0
            continue
            
        # Если встретили cuboid, извлекаем его числа
        if "cuboid" in line_lower:
            numbers = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", line_lower)]
            
            # SCALE cuboid: ID +X -X +Y -Y +Z -Z (всего минимум 7 чисел с учетом ID)
            if len(numbers) >= 7:
                # Извлекаем локальные origin самого кубоида, если они прописаны в его же строке
                local_ox = float(re.search(r"origin\s+x=([-+]?\d*\.\d+|\d+)", line_lower).group(1)) if re.search(r"origin\s+x=", line_lower) else 0.0
                local_oy = float(re.search(r"origin\s+y=([-+]?\d*\.\d+|\d+)", line_lower).group(1)) if re.search(r"origin\s+y=", line_lower) else 0.0
                local_oz = float(re.search(r"origin\s+z=([-+]?\d*\.\d+|\d+)", line_lower).group(1)) if re.search(r"origin\s+z=", line_lower) else 0.0
                
                # Итоговое смещение = смещение от hole + смещение самого кубоида
                total_ox = current_ox + local_ox
                total_oy = current_oy + local_oy
                total_oz = current_oz + local_oz
                
                # Применяем сдвиги к координатам кубоида (индексы 1 и 2 для X, 3 и 4 для Y, 5 и 6 для Z)
                x_max = numbers[1] + total_ox
                x_min = numbers[2] + total_ox
                y_max = numbers[3] + total_oy
                y_min = numbers[4] + total_oy
                z_max = numbers[5] + total_oz
                z_min = numbers[6] + total_oz
                
                x_coords.update([round(x_max, 1), round(x_min, 1)])
                y_coords.update([round(y_max, 1), round(y_min, 1)])
                z_coords.update([round(z_max, 1), round(z_min, 1)])

    # Сортировка от максимума к минимуму (reverse=True)
    return sorted(list(x_coords), reverse=True), sorted(list(y_coords), reverse=True), sorted(list(z_coords), reverse=True)

if geo_text:
    x_s, y_s, z_s = parse_scale_final(geo_text)
    
    if not x_s and not y_s and not z_s:
        st.warning("Не удалось извлечь координаты. Проверьте формат блока geometry.")
    else:
        # Сборка блока строго по вашему шаблону
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
