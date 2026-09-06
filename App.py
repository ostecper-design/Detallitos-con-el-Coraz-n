import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuración de la página para móvil
st.set_page_config(page_title="Cotizador Móvil", page_icon="🧮", layout="centered")

st.title("📱 Cotizador de Productos")

# 1. Cargar base de datos adaptada a tus columnas reales
@st.cache_data
def cargar_datos():
    if os.path.exists("listado.csv"):
        # Cargamos el archivo usando codificación utf-8 o latin1 por los acentos
        try:
            listado = pd.read_csv("listado.csv", encoding='utf-8')
        except:
            listado = pd.read_csv("listado.csv", encoding='latin1')
            
        # Asegurar que elimine espacios en blanco en los nombres de las columnas
        listado.columns = listado.columns.str.strip()
        
        # Filtrar solo las filas que tengan productos válidos
        listado = listado.dropna(subset=['PRODUCTOS'])
        listado = listado[listado['PRODUCTOS'].str.strip() != '']
        
        # Limpiar el formato de precio si viene con "$" de Excel
        if 'COSTO' in listado.columns:
            listado['COSTO_LIMPIO'] = listado['COSTO'].astype(str).str.replace('$', '', regex=False)
            listado['COSTO_LIMPIO'] = listado['COSTO_LIMPIO'].str.replace(',', '', regex=False).str.strip()
            listado['COSTO_LIMPIO'] = pd.to_numeric(listado['COSTO_LIMPIO'], errors='coerce').fillna(0.0)
        else:
            listado['COSTO_LIMPIO'] = 0.0
            
        return listado
    else:
        # Respaldo si no encuentra el archivo
        return pd.DataFrame({'PRODUCTOS': ['No se encontró listado.csv'], 'COSTO_LIMPIO': [0.0]})

df_productos = cargar_datos()

# Inicializar el carrito/cotización actual en la sesión si no existe
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# 2. Sección de Selección de Productos
st.header("🛒 Agregar a la Cotización")

# Buscador/Selector con tus productos reales
lista_productos = df_productos['PRODUCTOS'].str.strip().tolist()
producto_seleccionado = st.selectbox("Selecciona un producto:", lista_productos)

# Buscar el precio limpio del producto seleccionado
filtro_precio = df_productos[df_productos['PRODUCTOS'].str.strip() == producto_seleccionado]['COSTO_LIMPIO'].values
precio_sugerido = float(filtro_precio[0]) if len(filtro_precio) > 0 else 0.0

# Campos de cantidad y precio
col1, col2 = st.columns(2)
with col1:
    cantidad = st.number_input("Cantidad:", min_value=1, value=1, step=1)
with col2:
    precio_final = st.number_input("Precio Unitario ($):", min_value=0.0, value=precio_sugerido, step=1.0)

# Botón para añadir
if st.button("➕ Añadir Producto", use_container_width=True):
    total_item = cantidad * precio_final
    st.session_state.carrito.append({
        'PRODUCTOS': producto_seleccionado,
        'Cantidad': cantidad,
        'Precio Unitario': precio_final,
        'Total': total_item
    })
    st.toast(f"¡{producto_seleccionado} añadido!")

# 3. Sección del Cotizador (Resumen)
st.header("📋 Resumen de Cotización")

if len(st.session_state.carrito) > 0:
    # Convertir el carrito actual en un DataFrame para mostrarlo limpio
    df_actual = pd.DataFrame(st.session_state.carrito)
    
    # Mostrar tabla simplificada adaptada a tus columnas
    st.dataframe(df_actual[['PRODUCTOS', 'Cantidad', 'Total']], use_container_width=True, hide_index=True)
    
    # Calcular el Gran Total
    gran_total = df_actual['Total'].sum()
    st.metric(label="Gran Total", value=f"${gran_total:,.2f}")
    
    # Botones de acción ocupando el ancho del móvil
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🗑️ Limpiar Todo", use_container_width=True):
            st.session_state.carrito = []
            st.rerun()
            
    with col_btn2:
        if st.button("💾 Guardar Cotización", use_container_width=True):
            df_actual['Fecha'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            existe_archivo = os.path.exists("cotizador.csv")
            
            # Guardar en el CSV de cotizaciones sin alterar el formato
            df_actual.to_csv("cotizador.csv", mode='a', header=not existe_archivo, index=False)
            
            st.success("¡Cotización guardada exitosamente!")
            st.session_state.carrito = []
            st.rerun()
else:
    st.info("El cotizador está vacío. Añade productos arriba.")
