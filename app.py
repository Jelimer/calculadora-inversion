import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
import json
import firebase_admin
from firebase_admin import credentials, firestore
import uuid

st.set_page_config(layout="wide", page_title="Calculadora de Inversión")
st.title("📊 Calculadora de Inversión con Interés Compuesto Variable")

# --- MODO DE DIAGNÓSTICO ---
# Vamos a verificar qué está viendo Streamlit en los secrets.
st.subheader("--- Módulo de Diagnóstico de Secrets ---")

try:
    # 1. ¿Existen los secrets?
    st.write("Claves encontradas en los Secrets:", st.secrets.keys())

    # 2. ¿Existe la sección [firebase_credentials]?
    if "firebase_credentials" in st.secrets:
        st.success("✅ ¡Éxito! Se encontró la sección [firebase_credentials] en los Secrets.")
        
        # 3. ¿Podemos leer un valor de adentro?
        project_id = st.secrets.firebase_credentials.get("project_id")
        if project_id:
            st.info(f"Project ID leído desde los Secrets: {project_id}")
        else:
            st.warning("⚠️ Se encontró [firebase_credentials], pero no se pudo leer el 'project_id'. Revisa que el formato 'clave = \"valor\"' sea correcto.")

    else:
        st.error("❌ ERROR: No se encontró la sección [firebase_credentials]. Asegurate de que el encabezado esté escrito exactamente así en tus Secrets.")

except Exception as e:
    st.error(f"Ocurrió un error inesperado al leer los Secrets: {e}")

st.subheader("--- Fin del Módulo de Diagnóstico ---")
st.markdown("---")


# --- (El resto del código no se ejecutará si hay un error de secrets, pero lo dejamos) ---
# ... (Aquí va el resto del código de la calculadora que ya tenías, no es necesario cambiarlo) ...
class CalculadoraInteresVariable:
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

def init_firestore():
    try:
        creds_dict = st.secrets["firebase_credentials"]
        creds = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(creds)
    except Exception:
        if not firebase_admin._apps:
            # Este es el error que estás viendo
            st.error("Error al inicializar Firebase. Revisa las credenciales en los Secrets.")
            return None
    return firestore.client()
# ... (resto de las funciones y la UI) ...