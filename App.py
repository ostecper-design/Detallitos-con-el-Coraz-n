import streamlit as st
import pandas as pd
from datetime import datetime
import requests
from io import StringIO

# Configuración de la página para móvil
st.set_page_config(page_title="Cotizador Móvil", page_icon="🧮", layout="centered")

st.title("📱 Cotizador en la Nube")

# Enlace de tu Google Sheets (Formateado para exportar directamente cada pestaña)
SHEET_ID = "1k-omOWx7ycJY-Np365lCkby7O9wzTBjESdjNrE0Ple0"
URL_LISTADO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=listado"
URL_COTIZADOR = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=cotizador"

# 1. Cargar base de datos desde Google Sheets
@st.cache_data(ttl=60)  # Se actualiza cada 60 segundos si haces cambios en tu Drive
def cargar_datos():
    try:
        # Descargar los datos desde el enlace de Google
        respuesta = requests.get(URL_LISTADO)
        listado = pd.read_csv(StringIO(respuesta.text))
        
        # Limpiar espacios en los nombres de las columnas
        listado.columns = listado.columns.str.strip()
        
        # Filtrar filas vacías, totales o notas de ingredientes abajo
        listado = listado.dropna(subset=['PRODUCTOS'])
        listado = listado[listado['PRODUCTOS'].str.strip() != '']
        listado = listado[~listado['PRODUCTOS'].str.contains('TOTAL|QUESO|JAMON|MAYONESA|PAN|LECHUGA', case=False, na=False)]
        
        # Limpiar los precios quitando el símbolo "$" y comas
        if 'COSTO' in listado.columns:
            listado['COSTO_LIMPIO'] = listado['COSTO'].astype(str).str.replace('$', '', regex=False)
            listado['COSTO_LIMPIO'] = listado['COSTO_LIMPIO'].str.replace(',', '', regex=False).str.strip()
            listado['COSTO_LIMPIO'] = pd.to_numeric(listado['COSTO_LIMPIO'], errors='coerce').fillna(0.0)
        else:
            listado['COSTO_LIMPIO'] = 0.0
            
        return listado
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return pd.DataFrame({'PRODUCTOS': ['Error de conexión'], 'COSTO_LIMPIO': [0.0]})

df_productos = cargar_datos()

# Inicializar el carrito en la sesión
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# 2. Sección de Selección de Productos
st.header("🛒 Agregar a la Cotización")

lista_productos = df_productos['PRODUCTOS'].str.strip().tolist()
producto_seleccionado = st.selectbox("Selecciona un producto:", lista_productos)

# Buscar el precio sugerido
filtro_precio = df_productos[df_productos['PRODUCTOS'].str.strip() == producto_seleccionado]['COSTO_LIMPIO'].values
precio_sugerido = float(filtro_precio) if len(filtro_precio) > 0 else 0.0

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
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🗑️ Limpiar Todo", use_container_width=True):
            st.session_state.carrito = []
            st.rerun()
            
    with col_btn2:
        if st.button("💾 Guardar Cotización", use_container_width=True):
            # Nota sobre el guardado en la nube pública
            st.success("¡Estructura de cotización lista!")
            st.info("Para habilitar la escritura directa en tu Drive desde el servidor de la nube, daremos el paso final en la plataforma de Streamlit.")
            st.session_state.carrito = []
            st.rerun()
else:
    st.info("El cotizador está vacío.")

