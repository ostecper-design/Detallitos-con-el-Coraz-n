import streamlit as st
import pandas as pd
import requests
from io import StringIO
import urllib.parse

# Configuración de la página para móvil
st.set_page_config(page_title="Cotizador Móvil", page_icon="🧮", layout="centered")

st.title("📱 Cotizador en la Nube")

# Enlace directo para descargar todo el libro de Google Sheets
URL_COMPLETA = "https://google.com"

# 1. Cargar base de datos buscando dinámicamente las columnas reales
@st.cache_data(ttl=5)
def cargar_datos():
    try:
        # Descargar los datos desde el enlace de Google
        respuesta = requests.get(URL_COMPLETA)
        raw_data = respuesta.text
        
        # Leer el CSV línea por línea para encontrar dónde dice "PRODUCTOS"
        lines = raw_data.split('\n')
        skip_rows = 0
        for i, line in enumerate(lines):
            if "PRODUCTOS" in line:
                skip_rows = i
                break
                
        # Volver a cargar el DataFrame saltando las filas basura del inicio
        listado = pd.read_csv(StringIO(raw_data), skiprows=skip_rows)
        
        # Limpiar espacios en los nombres de las columnas
        listado.columns = listado.columns.str.strip()
        
        # Verificar que la columna exista, si no, usar la primera columna disponible
        col_producto = 'PRODUCTOS' if 'PRODUCTOS' in listado.columns else listado.columns[0]
        col_costo = 'COSTO' if 'COSTO' in listado.columns else (listado.columns[1] if len(listado.columns) > 1 else listado.columns[0])
        
        # Renombrar para trabajar de forma segura
        listado = listado.rename(columns={col_producto: 'PRODUCTOS_REF', col_costo: 'COSTO_REF'})
        
        # Filtrar filas vacías, totales o notas de ingredientes abajo
        listado = listado.dropna(subset=['PRODUCTOS_REF'])
        listado['PRODUCTOS_REF'] = listado['PRODUCTOS_REF'].astype(str).str.strip()
        listado = listado[listado['PRODUCTOS_REF'] != '']
        listado = listado[~listado['PRODUCTOS_REF'].str.contains('TOTAL|QUESO|JAMON|MAYONESA|PAN|LECHUGA', case=False, na=False)]
        
        # Limpiar los precios quitando el símbolo "$" y comas
        listado['COSTO_LIMPIO'] = listado['COSTO_REF'].astype(str).str.replace('$', '', regex=False)
        listado['COSTO_LIMPIO'] = listado['COSTO_LIMPIO'].str.replace(',', '', regex=False).str.strip()
        listado['COSTO_LIMPIO'] = pd.to_numeric(listado['COSTO_LIMPIO'], errors='coerce').fillna(0.0)
            
        return listado
    except Exception as e:
        st.error(f"Error al procesar las columnas de Google Sheets: {e}")
        return pd.DataFrame({'PRODUCTOS_REF': ['Error de formato'], 'COSTO_LIMPIO': [0.0]})

df_productos = cargar_datos()

# Inicializar el carrito en la sesión
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# 2. Sección de Selección de Productos
st.header("🛒 Agregar a la Cotización")

# Campo opcional para el nombre del cliente
nombre_cliente = st.text_input("👤 Nombre del Cliente (Opcional):", placeholder="Ej. María López")

lista_productos = df_productos['PRODUCTOS_REF'].tolist()
producto_seleccionado = st.selectbox("Selecciona un producto:", lista_productos)

# Extraer el precio de forma segura
filtro_precio = df_productos[df_productos['PRODUCTOS_REF'] == producto_seleccionado]['COSTO_LIMPIO'].values
precio_sugerido = float(filtro_precio[0]) if len(filtro_precio) > 0 else 0.0

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
    
    # Botones de acción ocupando el ancho del móvil
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
