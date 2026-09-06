import streamlit as st
import pandas as pd
import requests
from io import StringIO
import urllib.parse

# Configuración de la página para móvil
st.set_page_config(page_title="Cotizador Móvil", page_icon="🧮", layout="centered")

st.title("📱 Cotizador en la Nube")

# TU ENLACE CORRECTO CONFIGURADO PARA DESCARGA DIRECTA
URL_UNIVERSAL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTGZnZYeCUJkXq3VThyrroJYOxCHiZEgV4RiGxclb2rSjZWAe2wwx8GOjb8wlefj9YsrZp"
# 1. Cargar base de datos de forma directa y limpia
@st.cache_data(ttl=2)
def cargar_datos():
    try:
        # Descarga el CSV directo usando tu enlace público revisado
        respuesta = requests.get(URL_UNIVERSAL)
        raw_text = respuesta.content.decode('utf-8')
        listado = pd.read_csv(StringIO(raw_text))
        
        # Limpiar espacios en blanco en los nombres de las columnas
        listado.columns = listado.columns.str.strip()
        
        if 'PRODUCTOS' in listado.columns:
            listado = listado.dropna(subset=['PRODUCTOS'])
            listado['PRODUCTOS'] = listado['PRODUCTOS'].astype(str).str.strip()
            listado = listado[listado['PRODUCTOS'] != '']
            listado = listado[~listado['PRODUCTOS'].str.contains('TOTAL|QUESO|JAMON|MAYONESA|PAN|LECHUGA', case=False, na=False)]
            
            # Limpiar precios quitando el símbolo "$" y comas
            if 'COSTO' in listado.columns:
                listado['COSTO_LIMPIO'] = listado['COSTO'].astype(str).str.replace('$', '', regex=False)
                listado['COSTO_LIMPIO'] = listado['COSTO_LIMPIO'].str.replace(',', '', regex=False).str.strip()
                listado['COSTO_LIMPIO'] = pd.to_numeric(listado['COSTO_LIMPIO'], errors='coerce').fillna(0.0)
            else:
                listado['COSTO_LIMPIO'] = 0.0
        else:
            # Plan de respaldo por si las columnas vienen distintas
            primera_col = listado.columns if len(listado.columns) > 0 else 'PRODUCTOS'
            listado = listado.rename(columns={primera_col: 'PRODUCTOS'})
            listado['COSTO_LIMPIO'] = 0.0
            
        return listado
    except Exception as e:
        return pd.DataFrame({'PRODUCTOS': ['Error al conectar con Drive'], 'COSTO_LIMPIO': [0.0]})

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
    precio_sugerido = float(filtro_precio) if len(filtro_precio) > 0 else 0.0
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
