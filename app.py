import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import uuid

# --- CLASE DE LA CALCULADORA (MODIFICADA PARA DESGLOSAR CAPITAL E INTERESES) ---
class CalculadoraInteresVariable:
    """Calculadora de interés compuesto que desglosa capital e intereses."""
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
        historial_texto = []
        # Columnas para el nuevo desglose
        datos_grafico = {'fecha': [], 'saldo_total': [], 'capital_aportado': [], 'interes_ganado': []}
        
        self._eventos.sort(key=lambda x: (x[0], x[1] == 'cambio_tasa'))
        
        # Variables para el desglose
        capital_actual = self.capital_inicial
        interes_acumulado = 0.0
        saldo_total = self.capital_inicial
        
        fecha_actual, tasa_actual = self.fecha_inicio, self._obtener_tasa_inicial()
        
        historial_texto.append(f"[{fecha_actual}] Inicio: ${saldo_total:,.2f} | Tasa: {tasa_actual:.2%}")
        datos_grafico['fecha'].append(fecha_actual)
        datos_grafico['saldo_total'].append(saldo_total)
        datos_grafico['capital_aportado'].append(capital_actual)
        datos_grafico['interes_ganado'].append(interes_acumulado)

        eventos_a_procesar = self._eventos + [(fecha_final, 'fin_calculo', 0)]
        for fecha_evento, tipo_evento, valor in eventos_a_procesar:
            if fecha_evento > fecha_actual:
                dias = (fecha_evento - fecha_actual).days
                tasa_diaria = tasa_actual / 365
                for i in range(dias):
                    interes_diario = saldo_total * tasa_diaria
                    interes_acumulado += interes_diario
                    saldo_total += interes_diario
                    
                    fecha_diaria = fecha_actual + timedelta(days=i + 1)
                    if fecha_diaria > fecha_final: break
                    
                    datos_grafico['fecha'].append(fecha_diaria)
                    datos_grafico['saldo_total'].append(saldo_total)
                    datos_grafico['capital_aportado'].append(capital_actual)
                    datos_grafico['interes_ganado'].append(interes_acumulado)

            fecha_actual = fecha_evento
            if fecha_actual > fecha_final: break

            if tipo_evento == 'transaccion':
                saldo_total += valor
                capital_actual += valor # El capital aportado cambia aquí
                op_str = "Depósito" if valor > 0 else "Extracción"
                historial_texto.append(f"[{fecha_actual}] {op_str}: ${abs(valor):,.2f} | Saldo: ${saldo_total:,.2f}")
                datos_grafico['fecha'].append(fecha_actual)
                datos_grafico['saldo_total'].append(saldo_total)
                datos_grafico['capital_aportado'].append(capital_actual)
                datos_grafico['interes_ganado'].append(interes_acumulado)
            elif tipo_evento == 'cambio_tasa':
                tasa_actual = valor
                historial_texto.append(f"[{fecha_actual}] Cambio Tasa: {tasa_actual:.2%}")
        
        df_grafico = pd.DataFrame(datos_grafico).drop_duplicates('fecha', keep='last').sort_values('fecha')
        df_grafico['fecha'] = pd.to_datetime(df_grafico['fecha'])
        return saldo_total, historial_texto, df_grafico

# --- CONEXIÓN A FIREBASE Y FUNCIONES DE LA DB (SIN CAMBIOS) ---
def init_firestore():
    try:
        creds_dict = dict(st.secrets["firebase_credentials"])
        creds = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(creds)
    except Exception as e:
        if not firebase_admin._apps:
            st.error(f"Error al inicializar Firebase: {e}. Revisa las credenciales en los Secrets.")
            return None
    return firestore.client()

def guardar_sesion(db, eventos):
    if not db:
        st.error("No se puede guardar la sesión: conexión a la base de datos no disponible.")
        return None
    if not eventos:
        st.warning("No hay eventos para guardar.")
        return None
    try:
        sesion_id = str(uuid.uuid4().hex[:10])
        eventos_serializados = [{**e, 'Fecha': e['Fecha'].isoformat()} for e in eventos]
        doc_ref = db.collection('sesiones').document(sesion_id)
        doc_ref.set({'eventos': eventos_serializados})
        return sesion_id
    except Exception as e:
        st.error(f"Error al guardar la sesión: {e}")
        return None

def cargar_sesion(db, sesion_id):
    if not db: return None
    if not sesion_id: return None
    try:
        doc_ref = db.collection('sesiones').document(sesion_id)
        doc = doc_ref.get()
        if doc.exists:
            eventos_cargados = doc.to_dict().get('eventos', [])
            for e in eventos_cargados:
                e['Fecha'] = date.fromisoformat(e['Fecha'])
            return eventos_cargados
        return None
    except Exception as e:
        st.error(f"Error al cargar la sesión: {e}")
        return None

# --- INICIALIZACIÓN DE LA APP Y LA UI ---
db = init_firestore()

st.set_page_config(
    page_title="Calculadora de Inversión",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("💰 Calculadora de Inversión Avanzada")
st.markdown("Simulá el rendimiento de tus inversiones con tasas variables, depósitos y extracciones.")

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

col1, col2 = st.columns([1, 1.5], gap="large")

with col1:
    with st.container(border=True):
        st.header("1. 💵 Datos Iniciales")
        capital_inicial = st.number_input("Capital Inicial ($)", min_value=0.0, value=1000000.0, step=50000.0, format="%.2f")
        col_fechas1, col_fechas2 = st.columns(2)
        fecha_inicio = col_fechas1.date_input("Fecha de Inicio", value=date.today() - timedelta(days=180))
        fecha_final = col_fechas2.date_input("Fecha Final del Cálculo", value=date.today())
        
        if fecha_final < fecha_inicio:
            st.error("La fecha final debe ser posterior o igual a la fecha de inicio.")
            st.stop()

    with st.container(border=True):
        st.header("2. 🗓️ Agregar Nuevo Evento")
        tipo_evento = st.selectbox("Tipo de Evento", ["Cambio de Tasa", "Transacción (Depósito/Extracción)"])
        
        with st.form("form_nuevo_evento", clear_on_submit=True):
            fecha_evento = st.date_input("Fecha del Evento", value=date.today())
            if fecha_evento < fecha_inicio:
                st.error("La fecha del evento no puede ser anterior a la fecha de inicio.", icon="⚠️")
                st.stop()
            
            if tipo_evento == "Cambio de Tasa":
                valor_evento = st.number_input("Nueva Tasa Anual (ej: 0.40 para 40%)", min_value=0.0, value=0.40, step=0.01, format="%.2f")
                tipo_interno = 'cambio_tasa'
            else: 
                valor_evento = st.number_input("Monto de la Transacción ($)", value=0.0, step=10000.0, format="%.2f", help="Usa un valor positivo para depósitos y negativo para extracciones.")
                tipo_interno = 'transaccion'
            
            if st.form_submit_button("➕ Agregar Evento", use_container_width=True):
                nuevo_id = max([e.get('ID', 0) for e in st.session_state.eventos] + [0]) + 1
                st.session_state.eventos.append({"ID": nuevo_id, "Fecha": fecha_evento, "Tipo": tipo_evento, "Valor": valor_evento, "_tipo_interno": tipo_interno})
                st.rerun()

with col2:
    with st.container(border=True):
        st.header("📋 Eventos Registrados")
        if st.session_state.eventos:
            eventos_ordenados = sorted(st.session_state.eventos, key=lambda x: x['Fecha'])
            df_eventos = pd.DataFrame(eventos_ordenados).drop(columns=['_tipo_interno', 'ID'])
            st.dataframe(df_eventos, use_container_width=True, hide_index=True)
        else:
            st.info("Aún no has agregado ningún evento.")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("💾 Guardar Sesión")
    if st.button("Generar Link para Compartir", use_container_width=True):
        if st.session_state.eventos and db:
            sesion_id = guardar_sesion(db, st.session_state.eventos)
            if sesion_id:
                st.query_params["sesion"] = sesion_id
                st.success("¡Link generado! Copialo y guardalo.")
                st.code(f"{st.get_option('server.baseUrlPath')}?sesion={sesion_id}", language=None)
        elif not st.session_state.eventos:
            st.warning("Agrega al menos un evento para guardar.")
        else:
            st.error("Error de conexión con la DB.")

    st.markdown("---")
    st.header("⚙️ Editar / Eliminar")
    if st.session_state.eventos:
        opciones_eventos = {f"ID {e['ID']}: {e['Tipo']} ({e['Fecha']})": e['ID'] for e in st.session_state.eventos}
        id_seleccionado = st.selectbox("Selecciona un evento", options=opciones_eventos.keys(), label_visibility="collapsed")
        evento_a_editar = next((e for e in st.session_state.eventos if e['ID'] == opciones_eventos[id_seleccionado]), None)
        if evento_a_editar:
            with st.form("form_editar_evento"):
                st.write(f"**Editando Evento ID {evento_a_editar['ID']}**")
                nueva_fecha = st.date_input("Nueva Fecha", value=evento_a_editar['Fecha'])
                if nueva_fecha < fecha_inicio:
                    st.error("La fecha no puede ser anterior al inicio.")
                    st.stop()
                if evento_a_editar['_tipo_interno'] == 'cambio_tasa':
                    nuevo_valor = st.number_input("Nuevo Valor de Tasa", min_value=0.0, value=evento_a_editar['Valor'], format="%.2f")
                else:
                    nuevo_valor = st.number_input("Nuevo Monto", value=evento_a_editar['Valor'], format="%.2f")
                
                col_edit, col_del = st.columns(2)
                if col_edit.form_submit_button("💾 Guardar", use_container_width=True):
                    evento_a_editar['Fecha'], evento_a_editar['Valor'] = nueva_fecha, nuevo_valor
                    st.rerun()
                if col_del.form_submit_button("🗑️ Eliminar", use_container_width=True):
                    st.session_state.eventos = [e for e in st.session_state.eventos if e['ID'] != evento_a_editar['ID']]
                    st.rerun()
    else:
        st.info("Agrega eventos para poder editarlos.")

# --- BOTÓN DE CÁLCULO Y GRÁFICO ---
st.markdown("---")
if st.button("🚀 Calcular y Graficar Simulación", type="primary", use_container_width=True):
    if not st.session_state.eventos:
        st.warning("Por favor, agrega al menos un evento para poder calcular.")
        st.stop()
    try:
        calc = CalculadoraInteresVariable(capital_inicial, fecha_inicio)
        for ev in st.session_state.eventos:
            calc.agregar_evento(ev['Fecha'], ev['_tipo_interno'], ev['Valor'])
        saldo_final, historial, df_grafico = calc.calcular(fecha_final)

        with st.container(border=True):
            st.header("📈 Resultados de la Simulación")
            
            # Métricas desglosadas
            col_metrica1, col_metrica2, col_metrica3 = st.columns(3)
            col_metrica1.metric("Saldo Final Calculado", f"${saldo_final:,.2f}")
            col_metrica2.metric("Capital Aportado Neto", f"${df_grafico['capital_aportado'].iloc[-1]:,.2f}")
            col_metrica3.metric("Intereses Ganados Totales", f"${df_grafico['interes_ganado'].iloc[-1]:,.2f}")

            # --- GRÁFICO MEJORADO CON DESGLOSE ---
            fig = px.line(
                df_grafico, 
                x='fecha', 
                y=['saldo_total', 'capital_aportado', 'interes_ganado'],
                title="Evolución de la Inversión: Saldo vs Capital vs Intereses",
                template="plotly_dark",
                labels={'value': 'Monto en Pesos ($)', 'fecha': 'Línea de Tiempo', 'variable': 'Componente'},
                color_discrete_map={
                    'saldo_total': '#1f77b4',      # Azul
                    'capital_aportado': '#ff7f0e', # Naranja
                    'interes_ganado': '#2ca02c'     # Verde
                }
            )
            fig.update_layout(
                font=dict(family="Arial, sans-serif", size=12, color="white"),
                plot_bgcolor='rgba(0,0,0,0.3)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # --- NUEVO: MOSTRAR TABLA DE DATOS ---
            with st.expander("Ver tabla de datos diarios del gráfico"):
                # Formatear columnas para mejor lectura
                df_display = df_grafico.copy()
                for col in ['saldo_total', 'capital_aportado', 'interes_ganado']:
                    df_display[col] = df_display[col].apply(lambda x: f"${x:,.2f}")
                st.dataframe(df_display, use_container_width=True, hide_index=True)

            with st.expander("Ver historial de cálculo detallado"):
                st.text("\n".join(historial))

    except ValueError as e:
        st.error(f"⚠️ **Error de Configuración:** {e}")
    except Exception as e:
        st.error(f"Ocurrió un error inesperado durante el cálculo: {e}")
