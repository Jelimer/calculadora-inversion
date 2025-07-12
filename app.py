import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
import json
import firebase_admin
from firebase_admin import credentials, firestore
import uuid

# --- (La clase CalculadoraInteresVariable no necesita cambios) ---
class CalculadoraInteresVariable:
    # ... (el código de la clase es idéntico al de la respuesta anterior)
    """Calculadora de interés compuesto con tasas y transacciones variables."""
    def __init__(self, capital_inicial: float, fecha_inicio: date):
        self.capital_inicial, self.fecha_inicio, self._eventos = capital_inicial, fecha_inicio, []
    def agregar_evento(self, fecha: date, tipo: str, valor: float): self._eventos.append((fecha, tipo, valor))
    def _obtener_tasa_inicial(self) -> float:
        tasas_validas = [e for e in self._eventos if e[1] == 'cambio_tasa' and e[0] <= self.fecha_inicio]
        if not tasas_validas: raise ValueError("Falta Tasa de Interés Inicial.")
        return max(tasas_validas, key=lambda x: x[0])[2]
    def calcular(self, fecha_final: date) -> (float, list, pd.DataFrame):
        historial_texto, datos_grafico = [], {'fecha': [], 'saldo': []}
        self._eventos.sort(key=lambda x: x[0])
        saldo_actual, fecha_actual, tasa_actual = self.capital_inicial, self.fecha_inicio, self._obtener_tasa_inicial()
        historial_texto.append(f"[{fecha_actual}] Inicio: ${saldo_actual:,.2f} | Tasa: {tasa_actual:.2%}")
        datos_grafico['fecha'].append(fecha_actual); datos_grafico['saldo'].append(saldo_actual)
        eventos_a_procesar = self._eventos + [(fecha_final, 'fin_calculo', 0)]
        for fecha_evento, tipo_evento, valor in eventos_a_procesar:
            if fecha_evento > fecha_actual:
                dias = (fecha_evento - fecha_actual).days
                tasa_diaria = tasa_actual / 365
                for i in range(dias):
                    saldo_actual *= (1 + tasa_diaria)
                    fecha_diaria = fecha_actual + timedelta(days=i + 1)
                    if fecha_diaria > fecha_final: break
                    datos_grafico['fecha'].append(fecha_diaria); datos_grafico['saldo'].append(saldo_actual)
            fecha_actual = fecha_evento
            if fecha_actual > fecha_final: break
            if tipo_evento == 'transaccion':
                saldo_actual += valor
                op_str = "Depósito" if valor > 0 else "Extracción"
                historial_texto.append(f"[{fecha_actual}] {op_str}: ${abs(valor):,.2f} | Saldo: ${saldo_actual:,.2f}")
                datos_grafico['fecha'].append(fecha_actual); datos_grafico['saldo'].append(saldo_actual)
            elif tipo_evento == 'cambio_tasa':
                tasa_actual = valor
                historial_texto.append(f"[{fecha_actual}] Cambio Tasa: {tasa_actual:.2%}")
        return saldo_actual, historial_texto, pd.DataFrame(datos_grafico).drop_duplicates('fecha', keep='last').sort_values('fecha')

# --- CONEXIÓN A FIREBASE ---
def init_firestore():
    """Inicializa la conexión con Firestore usando los secrets de Streamlit."""
    try:
        # Intenta usar las credenciales de los secrets
        creds_dict = st.secrets["firebase_credentials"]
        creds = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(creds)
    except Exception:
        # Si ya está inicializada (pasa en los reruns de Streamlit), no hagas nada
        if not firebase_admin._apps:
            st.error("Error al inicializar Firebase. Revisa las credenciales en los Secrets.")
            return None
    return firestore.client()

db = init_firestore()

# --- FUNCIONES DE LA BASE DE DATOS ---
def guardar_sesion(eventos):
    """Guarda la lista de eventos en Firestore y devuelve el ID único."""
    if not db or not eventos: return None
    sesion_id = str(uuid.uuid4()) # Genera un ID único
    # Convierte fechas a string para guardar en Firestore
    eventos_serializados = [{**e, 'Fecha': e['Fecha'].isoformat()} for e in eventos]
    doc_ref = db.collection('sesiones').document(sesion_id)
    doc_ref.set({'eventos': eventos_serializados})
    return sesion_id

def cargar_sesion(sesion_id):
    """Carga una lista de eventos desde Firestore usando un ID."""
    if not db or not sesion_id: return None
    doc_ref = db.collection('sesiones').document(sesion_id)
    doc = doc_ref.get()
    if doc.exists:
        eventos_cargados = doc.to_dict().get('eventos', [])
        # Convierte las fechas de string de nuevo a objetos date
        for e in eventos_cargados:
            e['Fecha'] = date.fromisoformat(e['Fecha'])
        return eventos_cargados
    return None

# --- INTERFAZ DE USUARIO ---
st.set_page_config(layout="wide", page_title="Calculadora de Inversión")
st.title("📊 Calculadora de Inversión con Interés Compuesto Variable")

# Cargar datos desde la URL si existe el parámetro 'sesion'
if 'eventos' not in st.session_state:
    query_params = st.query_params
    sesion_id = query_params.get("sesion")
    if sesion_id:
        st.session_state.eventos = cargar_sesion(sesion_id)
        if st.session_state.eventos is None:
            st.error("No se pudo cargar la sesión con el ID proporcionado.")
            st.session_state.eventos = []
    else:
        st.session_state.eventos = []

# (El resto de la UI es similar, pero adaptada para usar la DB)
col1, col2 = st.columns([1, 2])
with col1:
    st.header("1. Datos Iniciales")
    capital_inicial = st.number_input("Capital Inicial ($)", min_value=0.0, value=1000000.0, step=50000.0, format="%.2f")
    fecha_inicio = st.date_input("Fecha de Inicio", value=date.today() - timedelta(days=180))
    fecha_final = st.date_input("Fecha Final del Cálculo", value=date.today())

    st.header("2. Agregar Nuevo Evento")
    with st.form("form_nuevo_evento", clear_on_submit=True):
        tipo_evento = st.selectbox("Tipo de Evento", ["Cambio de Tasa", "Transacción (Depósito/Extracción)"])
        fecha_evento = st.date_input("Fecha del Evento", value=date.today())
        if tipo_evento == "Cambio de Tasa":
            valor_evento = st.number_input("Nueva Tasa Anual (ej: 0.40 para 40%)", min_value=0.0, value=0.40, step=0.01, format="%.2f")
            tipo_interno = 'cambio_tasa'
        else:
            valor_evento = st.number_input("Monto de la Transacción ($)", value=0.0, step=10000.0, format="%.2f", help="Usa un valor positivo para depósitos y negativo para extracciones.")
            tipo_interno = 'transaccion'
        if st.form_submit_button("➕ Agregar Evento"):
            nuevo_id = max([e.get('ID', 0) for e in st.session_state.eventos] + [0]) + 1
            st.session_state.eventos.append({"ID": nuevo_id, "Fecha": fecha_evento, "Tipo": tipo_evento, "Valor": valor_evento, "_tipo_interno": tipo_interno})
            st.rerun()

with col2:
    st.header("Eventos Registrados")
    if st.session_state.eventos:
        eventos_ordenados = sorted(st.session_state.eventos, key=lambda x: x['Fecha'])
        df_eventos = pd.DataFrame(eventos_ordenados).drop(columns=['_tipo_interno', 'ID'])
        st.dataframe(df_eventos, use_container_width=True)
    else:
        st.info("Aún no has agregado ningún evento.")

# --- BARRA LATERAL CON NUEVAS FUNCIONES DE GUARDADO ONLINE ---
st.sidebar.header("💾 Guardar Sesión en la Nube")
if st.sidebar.button("Generar Link para Guardar y Compartir"):
    if st.session_state.eventos:
        sesion_id = guardar_sesion(st.session_state.eventos)
        if sesion_id:
            share_url = f"{st.get_option('server.baseUrlPath')}?sesion={sesion_id}"
            st.sidebar.success("¡Sesión guardada! Usá este link:")
            st.sidebar.code(share_url, language=None)
        else:
            st.sidebar.error("No se pudo guardar la sesión.")
    else:
        st.sidebar.warning("Agrega al menos un evento para guardar.")

# (La lógica de cálculo y graficación no cambia, solo se la llama al final)
st.markdown("---")
if st.button("🚀 Calcular y Graficar", type="primary", use_container_width=True):
    try:
        calc = CalculadoraInteresVariable(capital_inicial, fecha_inicio)
        for ev in st.session_state.eventos:
            calc.agregar_evento(ev['Fecha'], ev['_tipo_interno'], ev['Valor'])
        saldo_final, historial, df_grafico = calc.calcular(fecha_final)
        st.header("📈 Resultados de la Simulación")
        st.metric("Saldo Final", f"${saldo_final:,.2f}")
        fig = px.line(df_grafico, x='fecha', y='saldo', title="Evolución del Saldo de la Inversión", labels={'fecha':'Fecha', 'saldo':'Saldo ($)'})
        fig.update_traces(hovertemplate='<b>%{x|%d %b %Y}</b><br>Saldo: $%{y:,.2f}')
        # ... (código de graficación de eventos omitido por brevedad, es el mismo)
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("Ver historial de cálculo detallado"):
            st.text("\n".join(historial))
    except ValueError as e:
        st.error(f"⚠️ **Error de Configuración:** {e} Por favor, agregá un evento de 'Cambio de Tasa' que cubra la 'Fecha de Inicio'.")