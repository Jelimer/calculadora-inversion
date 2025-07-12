import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import uuid

# --- CLASE DE LA CALCULADORA (CON VALIDACIÓN DE TASAS NEGATIVAS) ---
class CalculadoraInteresVariable:
    """Calculadora de interés compuesto con tasas y transacciones variables."""
    def __init__(self, capital_inicial: float, fecha_inicio: date):
        self.capital_inicial, self.fecha_inicio, self._eventos = capital_inicial, fecha_inicio, []
    
    def agregar_evento(self, fecha: date, tipo: str, valor: float):
        if tipo == 'cambio_tasa' and valor < 0:
            raise ValueError("La tasa de interés no puede ser negativa.")
        self._eventos.append((fecha, tipo, valor))
    
    def _obtener_tasa_inicial(self) -> float:
        tasas_validas = [e for e in self._eventos if e[1] == 'cambio_tasa' and e[0] <= self.fecha_inicio]
        if not tasas_validas:
            raise ValueError("Falta Tasa de Interés Inicial.")
        return max(tasas_validas, key=lambda x: x[0])[2]
    
    def calcular(self, fecha_final: date) -> (float, list, pd.DataFrame):
        historial_texto, datos_grafico = [], {'fecha': [], 'saldo': []}
        # Ordenar eventos por fecha y luego por tipo (transacciones antes que cambios de tasa)
        self._eventos.sort(key=lambda x: (x[0], x[1] == 'cambio_tasa'))
        saldo_actual, fecha_actual, tasa_actual = self.capital_inicial, self.fecha_inicio, self._obtener_tasa_inicial()
        historial_texto.append(f"[{fecha_actual}] Inicio: ${saldo_actual:,.2f} | Tasa: {tasa_actual:.2%}")
        datos_grafico['fecha'].append(fecha_actual)
        datos_grafico['saldo'].append(saldo_actual)
        eventos_a_procesar = self._eventos + [(fecha_final, 'fin_calculo', 0)]
        for fecha_evento, tipo_evento, valor in eventos_a_procesar:
            if fecha_evento > fecha_actual:
                dias = (fecha_evento - fecha_actual).days
                tasa_diaria = tasa_actual / 365
                for i in range(dias):
                    saldo_actual *= (1 + tasa_diaria)
                    fecha_diaria = fecha_actual + timedelta(days=i + 1)
                    if fecha_diaria > fecha_final:
                        break
                    datos_grafico['fecha'].append(fecha_diaria)
                    datos_grafico['saldo'].append(saldo_actual)
            fecha_actual = fecha_evento
            if fecha_actual > fecha_final:
                break
            if tipo_evento == 'transaccion':
                saldo_actual += valor
                op_str = "Depósito" if valor > 0 else "Extracción"
                historial_texto.append(f"[{fecha_actual}] {op_str}: ${abs(valor):,.2f} | Saldo: ${saldo_actual:,.2f}")
                datos_grafico['fecha'].append(fecha_actual)
                datos_grafico['saldo'].append(saldo_actual)
            elif tipo_evento == 'cambio_tasa':
                tasa_actual = valor
                historial_texto.append(f"[{fecha_actual}] Cambio Tasa: {tasa_actual:.2%}")
        df_grafico = pd.DataFrame(datos_grafico).drop_duplicates('fecha', keep='last').sort_values('fecha')
        df_grafico['fecha'] = pd.to_datetime(df_grafico['fecha']) # Asegurar formato datetime
        return saldo_final, historial_texto, df_grafico

# --- CONEXIÓN A FIREBASE Y FUNCIONES DE LA DB ---
def init_firestore():
    """Inicializa la conexión con Firestore usando los secrets de Streamlit."""
    try:
        # LA CORRECCIÓN ESTÁ AQUÍ: Convertimos explícitamente a un dict.
        creds_dict = dict(st.secrets["firebase_credentials"])
        creds = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(creds)
    except Exception as e:
        if not firebase_admin._apps:
            st.error(f"Error al inicializar Firebase: {e}. Revisa las credenciales en los Secrets.")
            return None
    return firestore.client()

def guardar_sesion(db, eventos):
    """Guarda la lista de eventos en Firestore y devuelve el ID único."""
    if not db:
        st.error("No se puede guardar la sesión: conexión a la base de datos no disponible.")
        return None
    if not eventos:
        st.warning("No hay eventos para guardar.")
        return None
    try:
        sesion_id = str(uuid.uuid4().hex[:10]) # ID más corto
        eventos_serializados = []
        for e in eventos:
            if not isinstance(e['Fecha'], date):
                st.error(f"Error: Fecha inválida en evento {e}")
                return None
            eventos_serializados.append({**e, 'Fecha': e['Fecha'].isoformat()})
        doc_ref = db.collection('sesiones').document(sesion_id)
        doc_ref.set({'eventos': eventos_serializados})
        return sesion_id
    except Exception as e:
        st.error(f"Error al guardar la sesión: {e}")
        return None

def cargar_sesion(db, sesion_id):
    """Carga una lista de eventos desde Firestore usando un ID."""
    if not db:
        st.error("No se puede cargar la sesión: conexión a la base de datos no disponible.")
        return None
    if not sesion_id:
        return None
    try:
        doc_ref = db.collection('sesiones').document(sesion_id)
        doc = doc_ref.get()
        if doc.exists:
            eventos_cargados = doc.to_dict().get('eventos', [])
            for e in eventos_cargados:
                e['Fecha'] = date.fromisoformat(e['Fecha'])
            return eventos_cargados
        return None
    except ValueError as e:
        st.error(f"Error al cargar la sesión: formato de datos inválido ({e}).")
        return None
    except Exception as e:
        st.error(f"Error al cargar la sesión: {e}")
        return None

# --- INICIALIZACIÓN DE LA APP Y LA UI ---
db = init_firestore()

st.set_page_config(layout="wide", page_title="Calculadora de Inversión")
st.title("📊 Calculadora de Inversión con Interés Compuesto Variable")

# Lógica para cargar datos desde la URL o iniciar una sesión vacía
if 'eventos' not in st.session_state:
    query_params = st.query_params
    sesion_id = query_params.get("sesion")
    if sesion_id and db:
        st.session_state.eventos = cargar_sesion(db, sesion_id)
        if st.session_state.eventos is None:
            st.error("No se pudo cargar la sesión con el ID proporcionado.")
            st.session_state.eventos = []
    else:
        st.session_state.eventos = []

# --- Columnas principales de la UI ---
col1, col2 = st.columns([1, 2])
with col1:
    st.header("1. Datos Iniciales")
    capital_inicial = st.number_input("Capital Inicial ($)", min_value=0.0, value=1000000.0, step=50000.0, format="%.2f")
    fecha_inicio = st.date_input("Fecha de Inicio", value=date.today() - timedelta(days=180))
    fecha_final = st.date_input("Fecha Final del Cálculo", value=date.today())
    
    # Validación de fechas inicial y final
    if fecha_final < fecha_inicio:
        st.error("La fecha final debe ser posterior o igual a la fecha de inicio.")
        st.stop()

    st.header("2. Agregar Nuevo Evento")
    with st.form("form_nuevo_evento", clear_on_submit=True):
        tipo_evento = st.selectbox("Tipo de Evento", ["Cambio de Tasa", "Transacción (Depósito/Extracción)"])
        fecha_evento = st.date_input("Fecha del Evento", value=date.today())
        # Validación de fecha del evento
        if fecha_evento < fecha_inicio:
            st.error("La fecha del evento no puede ser anterior a la fecha de inicio.")
            st.stop()
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

# --- BARRA LATERAL ---
st.sidebar.header("💾 Guardar Sesión en la Nube")
if st.sidebar.button("Generar Link para Guardar y Compartir"):
    if st.session_state.eventos and db:
        sesion_id = guardar_sesion(db, st.session_state.eventos)
        if sesion_id:
            st.query_params.set(sesion=sesion_id) # Actualiza la URL con el ID de la sesión
            st.sidebar.success("¡Sesión guardada! Copiá y guardá este link:")
            st.sidebar.code(f"{st.get_option('server.baseUrlPath')}?sesion={sesion_id}", language=None)
    elif not st.session_state.eventos:
        st.sidebar.warning("Agrega al menos un evento para guardar.")
    else:
        st.sidebar.error("Error de conexión con la base de datos.")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Editar o Eliminar Evento")
if st.session_state.eventos:
    opciones_eventos = {f"ID {e['ID']}: {e['Tipo']} el {e['Fecha']}": e['ID'] for e in st.session_state.eventos}
    id_seleccionado = st.sidebar.selectbox("Selecciona un evento para modificar", options=opciones_eventos.keys())
    evento_a_editar = next((e for e in st.session_state.eventos if e['ID'] == opciones_eventos[id_seleccionado]), None)
    if evento_a_editar:
        with st.sidebar.form("form_editar_evento"):
            st.write(f"**Editando Evento ID {evento_a_editar['ID']}**")
            nueva_fecha = st.date_input("Nueva Fecha", value=evento_a_editar['Fecha'])
            # Validación de nueva fecha
            if nueva_fecha < fecha_inicio:
                st.error("La nueva fecha no puede ser anterior a la fecha de inicio.")
                st.stop()
            if evento_a_editar['_tipo_interno'] == 'cambio_tasa':
                nuevo_valor = st.number_input("Nuevo Valor de Tasa", min_value=0.0, value=evento_a_editar['Valor'], format="%.2f")
            else:
                nuevo_valor = st.number_input("Nuevo Monto de Transacción", value=evento_a_editar['Valor'], format="%.2f")
            col_edit, col_del = st.columns(2)
            if col_edit.form_submit_button("💾 Guardar Cambios"):
                evento_a_editar['Fecha'], evento_a_editar['Valor'] = nueva_fecha, nuevo_valor
                st.rerun()
            if col_del.form_submit_button("🗑️ Eliminar Evento"):
                st.session_state.eventos = [e for e in st.session_state.eventos if e['ID'] != evento_a_editar['ID']]
                st.rerun()
else:
    st.sidebar.info("Agrega un evento para poder editarlo.")

# --- BOTÓN DE CÁLCULO Y GRÁFICO ---
st.markdown("---")
if st.button("🚀 Calcular y Graficar", type="primary", use_container_width=True):
    try:
        calc = CalculadoraInteresVariable(capital_inicial, fecha_inicio)
        for ev in st.session_state.eventos:
            calc.agregar_evento(ev['Fecha'], ev['_tipo_interno'], ev['Valor'])
        saldo_final, historial, df_grafico = calc.calcular(fecha_final)
        st.header("📈 Resultados de la Simulación")
        st.metric("Saldo Final", f"${saldo_final:,.2f}")
        fig = px.line(df_grafico, x='fecha', y='saldo', title="Evolución del Saldo de la Inversión", labels={'fecha': 'Fecha', 'saldo': 'Saldo ($)'})
        fig.update_traces(hovertemplate='<b>%{x|%d %b %Y}</b><br>Saldo: $%{y:,.2f}')
        for ev in st.session_state.eventos:
            fecha_evento_dt = pd.to_datetime(ev['Fecha'])
            if fecha_inicio <= ev['Fecha'] <= fecha_final and not df_grafico[df_grafico['fecha'] == fecha_evento_dt].empty:
                simbolo = "triangle-up" if ev['_tipo_interno'] == 'transaccion' and ev['Valor'] > 0 else "triangle-down"
                if ev['_tipo_interno'] == 'cambio_tasa':
                    simbolo = "circle"
                color = "green" if ev['_tipo_interno'] == 'transaccion' and ev['Valor'] > 0 else "red"
                if ev['_tipo_interno'] == 'cambio_tasa':
                    color = "orange"
                saldo_en_fecha = df_grafico[df_grafico['fecha'] == fecha_evento_dt]['saldo'].iloc[0]
                fig.add_scatter(x=[ev['Fecha']], y=[saldo_en_fecha], mode='markers',
                                marker=dict(symbol=simbolo, color=color, size=10, line=dict(width=1, color='DarkSlateGrey')),
                                name=f"{ev['Tipo']}: {ev['Valor']}",
                                hovertemplate=f"<b>{ev['Fecha']:%d %b %Y}</b><br>{ev['Tipo']}<br>Valor: {ev['Valor']:,}")
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("Ver historial de cálculo detallado"):
            st.text("\n".join(historial))
    except ValueError as e:
        st.error(f"⚠️ **Error de Configuración:** {e} Por favor, agregá un evento de 'Cambio de Tasa' que cubra la 'Fecha de Inicio'.")
    except Exception as e:
        st.error(f"Ocurrió un error inesperado durante el cálculo: {e}")
