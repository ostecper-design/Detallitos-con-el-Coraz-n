import streamlit as st
import pandas as pd
import requests
from io import StringIO
import urllib.parse

# Configuración de la página para móvil
st.set_page_config(page_title="Cotizador Móvil", page_icon="🧮", layout="centered")

st.title("📱 Cotizador en la Nube")

# TU ENLACE CORRECTO DE GOOGLE SHEETS
URL_UNIVERSAL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTGZnZYeCUJkXq3VThyrroJYOxCHiZEgV4RiGxclb2rSjZWAe2wwx8GOjb8wlefj9YsrZpO6jZMeVAR/pub?output=csv"

# 1. Cargar base de datos de forma directa y limpia
@st.cache_data(ttl=2)
def cargar_datos():
    try:
        respuesta = requests.get(URL_UNIVERSAL)
        raw_text = respuesta.content.decode('utf-8')
        listado = pd.read_csv(StringIO(raw_text))
        
        # Limpiar espacios en blanco en los nombres de las columnas
        listado.columns = listado.columns.str.strip()
        
        # CORRECCIÓN DE MAYÚSCULAS: Convertir temporalmente las columnas a mayúsculas para no fallar
        columnas_mayus = [col.upper() for col in listado.columns]
        
        if 'PRODUCTOS' in columnas_mayus:
            # Encontrar el nombre real de la columna de productos en tu Sheets
            idx_prod = columnas_mayus.index('PRODUCTOS')
            col_real_prod = listado.columns[idx_prod]
            
            listado = listado.dropna(subset=[col_real_prod])
            listado[col_real_prod] = listado[col_real_prod].astype(str).str.strip()
            listado = listado[listado[col_real_prod] != '']
            listado = listado[~listado[col_real_prod].str.contains('TOTAL|QUESO|JAMON|MAYONESA|PAN|LECHUGA', case=False, na=False)]
            
            # Encontrar el nombre real de la columna de costos (buscando COSTO o COSTOS)
            col_real_costo = None
            for c in listado.columns:
                if c.upper() in ['COSTO', 'COSTOS', 'PRECIO', 'PRECIOS']:
                    col_real_costo = c
                    break
            
            # Si encontró la columna de costos, limpiar el símbolo de pesos y las comas
            if col_real_costo:
                listado['COSTO_LIMPIO'] = listado[col_real_costo].astype(str).str.replace('$', '', regex=False)
                listado['COSTO_LIMPIO'] = listado['COSTO_LIMPIO'].str.replace(',', '', regex=False).str.strip()
                listado['COSTO_LIMPIO'] = pd.to_numeric(listado['COSTO_LIMPIO'], errors='coerce').fillna(0.0)
            else:
                listado['COSTO_LIMPIO'] = 0.0
                
            # Renombrar la columna principal para que el resto del código funcione uniforme
            listado = listado.rename(columns={col_real_prod: 'PRODUCTOS'})
        else:
            # Plan de respaldo si por alguna razón no lee las columnas
            primera_col = listado.columns[0] if len(listado.columns) > 0 else 'PRODUCTOS'
            listado = listado.rename(columns={primera_col: 'PRODUCTOS'})
            listado['COSTO_LIMPIO'] = 0.0
            
        return listado
    except Exception as e:
        return pd.DataFrame({'PRODUCTOS': ['Error de lectura'], 'COSTO_LIMPIO': [0.0]})

df_productos = cargar_datos()

# Inicializar el carrito en la sesión
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# 2. Sección de Selección de Productos
st.header("🛒 Agregar a la Cotización")

nombre_cliente = st.text_input("👤 Nombre del Cliente (Opcional):", placeholder="Ej. María López")

lista_productos = df_productos['PRODUCTOS'].tolist()
producto_seleccionado = st.selectbox("Selecciona un producto:", lista_productos)

# Extraer el precio de forma segura
try:
    filtro_precio = df_productos[df_productos['PRODUCTOS'] == producto_seleccionado]['COSTO_LIMPIO'].values
    precio_sugerido = float(filtro_precio[0]) if len(filtro_precio) > 0 else 0.0
    # Asegurar que si el precio sugerido es 0.0 intente buscar de otra forma
    if precio_sugerido == 0.0 and len(filtro_precio) > 0:
        precio_sugerido = float(filtro_precio)
except:
    precio_sugerido = 0.0

col1, col2 = st.columns(2)
with col1:
    cantidad = st.number_input("Cantidad:", min_value=1, value=1, step=1)
with col2:
    precio_final = st.number_input("Precio Unitario ($):", min_value=0.0, value=precio_sugerido, step=1.0)

if st.button("➕ Añadir Producto", use_container_width=True):
    total_item = cantidad * precio_final
    st.session_state.carrito.append({
        'PRODUCTOS': producto_seleccionado,
        'Cantidad': cantidad,
        'Precio Unitario': precio_final,
        'Total': total_item
    })
    st.toast(f"¡{producto_seleccionado} añadido!")

# 3. Resumen de Cotización
st.header("📋 Resumen de Cotización")

if len(st.session_state.carrito) > 0:
    df_actual = pd.DataFrame(st.session_state.carrito)
    st.dataframe(df_actual[['PRODUCTOS', 'Cantidad', 'Total']], use_container_width=True, hide_index=True)
    
    gran_total = df_actual['Total'].sum()
    st.metric(label="Gran Total", value=f"${gran_total:,.2f}")
    
    # --- CONSTRUIR TEXTO PARA WHATSAPP ---
    saludo = "¡Hola! Te comparto la cotización."
    if nombre_cliente:
        saludo = f"¡Hola *{nombre_cliente}*! Te comparto tu cotización."
        
    mensaje_wa = f"{saludo}\n\n*Detalle del pedido:*\n"
    for item in st.session_state.carrito:
        mensaje_wa += f"• {item['Cantidad']}x {item['PRODUCTOS']} - ${item['Total']:,.2f}\n"
    
    mensaje_wa += f"\n*Gran Total: ${gran_total:,.2f}*"
    texto_codificado = urllib.parse.quote(mensaje_wa)
    enlace_whatsapp = f"https://wa.me{texto_codificado}"
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🗑️ Limpiar Todo", use_container_width=True):
            st.session_state.carrito = []
            st.rerun()
            
    with col_btn2:
        st.markdown(
            f'<a href="{enlace_whatsapp}" target="_blank" style="text-decoration:none;"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:8px; border-radius:4px; font-weight:bold; cursor:pointer;">💬 Enviar por WhatsApp</button></a>',
            unsafe_allow_html=True
        )
else:
    st.info("El cotizador está vacío.")
