import streamlit as st
import re

# Настройка страницы чата
st.set_page_config(page_title="SCALE GridGeometry Helper", page_icon="⚛️", layout="centered")

st.title("⚛️ Помощник SCALE: Из Geometry в GridGeometry")
st.write("Вставьте блок `geometry`, чтобы автоматически извлечь критические точки для сетки.")

# Поле ввода текста (как в чате)
geo_text = st.text_area("Вставьте блок geometry сюда:", height=250, placeholder="read geometry\n  cuboid 1 10.0 -10.0 5.0 -5.0 2.0 -2.0\nend geometry")

if geo_text:
    x_coords = set()
    y_coords = set()
    z_coords = set()
    
    lines = geo_text.split('\n')
    
    for line in lines:
        line_lower = line.lower().strip()
        if line_lower.startswith("'") or line_lower.startswith("read") or line_lower.startswith("end") or not line_lower:
            continue
            
        # Поиск всех чисел (включая отрицательные и дробные)
        numbers = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", line)]
        if not numbers:
            continue
            
        # Базовый парсинг стандартных примитивов SCALE
        if 'xplane' in line_lower:
            x_coords.update(numbers)
        elif 'yplane' in line_lower:
            y_coords.update(numbers)
        elif 'zplane' in line_lower:
            z_coords.update(numbers)
        elif 'cuboid' in line_lower or 'box' in line_lower:
            if len(numbers) >= 6:
                x_coords.update(numbers[-6:-4])
                y_coords.update(numbers[-4:-2])
                z_coords.update(numbers[-2:])
        elif 'cylinder' in line_lower:
            if 'z' in line_lower and len(numbers) >= 3:
                r = numbers
                x_coords.update([-r, r])
                y_coords.update([-r, r])
                z_coords.update(numbers[1:3])
            elif 'x' in line_lower and len(numbers) >= 3:
                r = numbers
                y_coords.update([-r, r])
                z_coords.update([-r, r])
                x_coords.update(numbers[1:3])
            elif 'y' in line_lower and len(numbers) >= 3:
                r = numbers
                x_coords.update([-r, r])
                z_coords.update([-r, r])
                y_coords.update(numbers[1:3])
        elif 'sphere' in line_lower and len(numbers) >= 1:
            r = numbers
            x_coords.update([-r, r])
            y_coords.update([-r, r])
            z_coords.update([-r, r])

    # Сортировка уникальных координат
    x_sorted = sorted(list(x_coords))
    y_sorted = sorted(list(y_coords))
    z_sorted = sorted(list(z_coords))
    
    if not x_sorted and not y_sorted and not z_sorted:
        st.warning("⚠️ Не удалось распознать геометрические тела. Проверьте формат ввода.")
    else:
        # Сборка блока gridGeometry
        result = "read gridGeometry\n"
        if x_sorted:
            result += f"  xgrid = {' '.join(map(str, x_sorted))}\n"
        if y_sorted:
            result += f"  ygrid = {' '.join(map(str, y_sorted))}\n"
        if z_sorted:
            result += f"  zgrid = {' '.join(map(str, z_sorted))}\n"
        result += "end gridGeometry"
        
        st.subheader("Результат:")
        st.code(result, language="text")
