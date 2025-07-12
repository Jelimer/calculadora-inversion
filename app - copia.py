import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta

# --- (La clase CalculadoraInteresVariable ahora dará un error más claro) ---
class CalculadoraInteresVariable:
    """
    Calculadora de interés compuesto con tasas y transacciones variables.
    Modificada para devolver datos para graficar.
    """
    def __init__(self, capital_inicial: float, fecha_inicio: date):
        self.capital_inicial = capital_inicial
        self.fecha_inicio = fecha_inicio
        self._eventos = []

    def agregar_evento(self, fecha: date, tipo: str, valor: float):
        self._eventos.append((fecha, tipo, valor))

    def _obtener_tasa_inicial(self) -> float:
        tasas_validas = [e for e in self._eventos if e[1] == 'cambio_tasa' and e[0] <= self.fecha_inicio]
        # --- CAMBIO CLAVE AQUÍ ---
        # Si no hay tasa para la fecha de inicio, lanzamos un error en lugar de devolver 0.
        if not tasas_validas:
            raise ValueError("Falta Tasa de Interés Inicial. No se encontró una tasa definida para la fecha de inicio.")
        return max(tasas_validas, key=lambda x: x[0])[2]

    def calcular(self, fecha_final: date) -> (float, list, pd.DataFrame):
        historial_texto = []
        datos_grafico = {'fecha': [], 'saldo': []}
        self._eventos.sort(key=lambda x: x[0])

        saldo_actual = self.capital_inicial
        fecha_actual = self.fecha_inicio
        # Esta llamada ahora puede lanzar el error que creamos
        tasa_actual = self._obtener_tasa_inicial() 

        historial_texto.append(f"[{self.fecha_inicio}] Inicio con ${saldo_actual:,.2f}")
        datos_grafico['fecha'].append(fecha_actual)
        datos_grafico['saldo'].append(saldo_actual)
        historial_texto.append(f"[{self.fecha_inicio}] Tasa inicial establecida en: {tasa_actual:.2%}")

        eventos_a_procesar = self._eventos + [(fecha_final, 'fin_calculo', 0)]
        for fecha_evento, tipo_evento, valor in eventos_a_procesar:
            if fecha_evento < fecha_actual:
                continue
            if fecha_evento > fecha_actual:
                dias = (fecha_evento - fecha_actual).days
                tasa_diaria = tasa_actual / 365
                for i in range(dias):
                    saldo_actual *= (1 + tasa_diaria)
                    fecha_diaria = fecha_actual + timedelta(days=i + 1)
                    datos_grafico['fecha'].append(fecha_diaria)
                    datos_grafico['saldo'].append(saldo_actual)
            fecha_actual = fecha_evento
            if fecha_actual > fecha_final: break
            if tipo_evento == 'transaccion':
                saldo_actual += valor
                tipo_transaccion = "Depósito" if valor > 0 else "Extracción"
                historial_texto.append(f"[{fecha_evento}] {tipo_transaccion} de ${abs(valor):,.2f}. Nuevo saldo: ${saldo_actual:,.2f}")
                datos_grafico['fecha'].append(fecha_evento)
                datos_grafico['saldo'].append(saldo_actual)
            elif tipo_evento == 'cambio_tasa':
                tasa_actual = valor
                historial_texto.append(f"[{fecha_evento}] CAMBIO DE TASA a {valor:.2%}")
        df_grafico = pd.DataFrame(datos_grafico).drop_duplicates(subset='fecha', keep='last').sort_values(by='fecha')
        return saldo_actual, historial_texto, df_grafico

# --- INTERFAZ DE USUARIO CON STREAMLIT ---

st.set_page_config(layout="wide", page_title="Calculadora de Inversión")
st.title("📊 Calculadora de Inversión con Interés Compuesto Variable")
if 'eventos' not in st.session_state:
    st.session_state.eventos = []

col1, col2 = st.columns([1, 2])
with col1:
    st.header("1. Datos Iniciales")
    capital_inicial = st.number_input("Capital Inicial ($)", min_value=0.0, value=1000000.0, step=50000.0, format="%.2f")
    fecha_inicio = st.date_input("Fecha de Inicio", value=date(2025, 1, 1))
    fecha_final = st.date_input("Fecha Final del Cálculo", value=date.today())

    st.header("2. Agregar Nuevo Evento")
    with st.form("form_nuevo_evento", clear_on_submit=True):
        tipo_evento = st.selectbox("Tipo de Evento", ["Cambio de Tasa", "Transacción (Depósito/Extracción)"])
        fecha_evento = st.date_input("Fecha del Evento", value=date.today())
        if tipo_evento == "Cambio de Tasa":
            valor_evento = st.number_input("Nueva Tasa Anual (ej: 0.60 para 60%)", min_value=0.0, value=0.60, step=0.01, format="%.2f")
            tipo_interno = 'cambio_tasa'
        else:
            valor_evento = st.number_input("Monto de la Transacción ($)", value=0.0, step=10000.0, format="%.2f", help="Usa un valor positivo para depósitos y negativo para extracciones.")
            tipo_interno = 'transaccion'
        submitted = st.form_submit_button("➕ Agregar Evento")
        if submitted:
            nuevo_id = max([e['ID'] for e in st.session_state.eventos] + [0]) + 1
            st.session_state.eventos.append({"ID": nuevo_id, "Fecha": fecha_evento, "Tipo": tipo_evento, "Valor": valor_evento, "_tipo_interno": tipo_interno})
            st.success(f"Evento '{tipo_evento}' agregado.")
            st.rerun()

with col2:
    st.header("Eventos Registrados")
    if st.session_state.eventos:
        eventos_ordenados = sorted(st.session_state.eventos, key=lambda x: x['Fecha'])
        df_eventos = pd.DataFrame(eventos_ordenados).drop(columns=['_tipo_interno', 'ID'])
        st.dataframe(df_eventos, use_container_width=True)
    else:
        st.info("Aún no has agregado ningún evento.")

st.sidebar.header("⚙️ Editar o Eliminar Evento")
if not st.session_state.eventos:
    st.sidebar.info("Agrega un evento para poder editarlo.")
else:
    opciones_eventos = {f"ID {e['ID']}: {e['Tipo']} el {e['Fecha']}": e['ID'] for e in st.session_state.eventos}
    id_seleccionado = st.sidebar.selectbox("Selecciona un evento para modificar", options=opciones_eventos.keys())
    evento_a_editar = next((e for e in st.session_state.eventos if e['ID'] == opciones_eventos[id_seleccionado]), None)
    if evento_a_editar:
        with st.sidebar.form("form_editar_evento"):
            st.write(f"**Editando Evento ID {evento_a_editar['ID']}**")
            nueva_fecha = st.date_input("Nueva Fecha", value=evento_a_editar['Fecha'])
            if evento_a_editar['_tipo_interno'] == 'cambio_tasa':
                nuevo_valor = st.number_input("Nuevo Valor de Tasa", value=evento_a_editar['Valor'], format="%.2f")
            else:
                nuevo_valor = st.number_input("Nuevo Monto de Transacción", value=evento_a_editar['Valor'], format="%.2f")
            col_edit, col_del = st.columns(2)
            submitted_edit = col_edit.form_submit_button("💾 Guardar Cambios")
            submitted_delete = col_del.form_submit_button("🗑️ Eliminar Evento")
            if submitted_edit:
                evento_a_editar['Fecha'] = nueva_fecha
                evento_a_editar['Valor'] = nuevo_valor
                st.sidebar.success(f"Evento ID {evento_a_editar['ID']} actualizado.")
                st.rerun()
            if submitted_delete:
                st.session_state.eventos = [e for e in st.session_state.eventos if e['ID'] != evento_a_editar['ID']]
                st.sidebar.success(f"Evento ID {evento_a_editar['ID']} eliminado.")
                st.rerun()
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
        for ev in st.session_state.eventos:
            if fecha_inicio <= ev['Fecha'] <= fecha_final:
                if not df_grafico.loc[df_grafico['fecha'] == pd.to_datetime(ev['Fecha'])].empty:
                    simbolo = "triangle-up" if ev['_tipo_interno'] == 'transaccion' and ev['Valor'] > 0 else "triangle-down"
                    if ev['_tipo_interno'] == 'cambio_tasa': simbolo = "circle"
                    color = "green" if ev['_tipo_interno'] == 'transaccion' and ev['Valor'] > 0 else "red"
                    if ev['_tipo_interno'] == 'cambio_tasa': color = "orange"
                    saldo_en_fecha = df_grafico.loc[df_grafico['fecha'] == pd.to_datetime(ev['Fecha']), 'saldo'].iloc[0]
                    fig.add_scatter(x=[ev['Fecha']], y=[saldo_en_fecha], mode='markers', marker=dict(symbol=simbolo, color=color, size=10, line=dict(width=1, color='DarkSlateGrey')), name=f"{ev['Tipo']}: {ev['Valor']}", hovertemplate=f"<b>{ev['Fecha']:%d %b %Y}</b><br>{ev['Tipo']}<br>Valor: {ev['Valor']}")
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("Ver historial de cálculo detallado"):
            st.text("\n".join(historial))
    except ValueError as e:
        # --- CAMBIO CLAVE AQUÍ ---
        # Atrapamos el error y mostramos un mensaje amigable y específico.
        st.error(f"⚠️ **Error de Configuración:** {e} Por favor, agregá un evento de 'Cambio de Tasa' con la misma fecha que tu 'Fecha de Inicio'.")