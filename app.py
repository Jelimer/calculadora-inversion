import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Calculadora de Inversión por Filas",
    page_icon="🧾",
    layout="wide",
)

# --- TÍTULO Y DESCRIPCIÓN ---
st.title("🧾 Calculadora de Inversión por Filas")
st.markdown("Simulá cada período de inversión de forma independiente, como en una hoja de cálculo.")

# --- INICIALIZACIÓN DEL ESTADO ---
if 'periodos' not in st.session_state:
    # Creamos un DataFrame de ejemplo con la nueva estructura de capital por fila
    st.session_state.periodos = pd.DataFrame(
        [
            {
                "Capital Inicial ($)": 1000000.0,
                "Fecha Inicio": date(2024, 1, 1),
                "Días de Inversión": 30,
                "Depósito Adicional ($)": 0.0,
                "Extracción ($)": 0.0,
                "Tasa Anual (%)": 50.0,
            }
        ]
    )

# --- SECCIÓN DE ENTRADA DE DATOS ---
with st.container(border=True):
    st.header("💵 Períodos de Inversión")
    st.markdown("##### Agregá, editá o eliminá los períodos de tu inversión directamente en la tabla. Cada fila es un cálculo independiente.")
    
    # Editor de datos interactivo con la nueva estructura
    edited_df = st.data_editor(
        st.session_state.periodos,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Capital Inicial ($)": st.column_config.NumberColumn(
                "Capital Inicial ($)",
                help="El monto con el que comienza este período específico.",
                required=True,
                format="$ %.2f",
            ),
            "Fecha Inicio": st.column_config.DateColumn(
                "Fecha de Inicio",
                help="Fecha en que comienza este período de inversión.",
                required=True,
                format="DD/MM/YYYY",
            ),
            "Días de Inversión": st.column_config.NumberColumn(
                "Días de Inversión",
                help="La duración en días de este período (ej: 30 para un plazo fijo mensual).",
                required=True,
                min_value=1,
                step=1,
            ),
            "Depósito Adicional ($)": st.column_config.NumberColumn(
                "Depósito Adicional ($)",
                help="Dinero que agregás al capital inicial de este período.",
                format="$ %.2f",
            ),
            "Extracción ($)": st.column_config.NumberColumn(
                "Extracción ($)",
                help="Dinero que retirás del capital inicial de este período.",
                format="$ %.2f",
            ),
            "Tasa Anual (%)": st.column_config.NumberColumn(
                "Tasa Anual (%)",
                help="La Tasa Nominal Anual para este período. Ej: 50 para 50%",
                format="%.2f %%",
            ),
        }
    )
    
    st.session_state.periodos = edited_df

# --- BOTÓN DE CÁLCULO ---
st.markdown("---")
if st.button("🚀 Calcular Resultados", type="primary", use_container_width=True):
    
    df_periodos = st.session_state.periodos.copy()
    
    if df_periodos.isnull().values.any():
        st.error("⚠️ Hay celdas vacías en la tabla. Por favor, completá todos los datos.")
    else:
        # --- LÓGICA DE CÁLCULO INDEPENDIENTE POR FILA ---
        resultados = []

        for index, row in df_periodos.iterrows():
            # Tomar los datos de la fila actual
            capital_inicial_fila = row["Capital Inicial ($)"]
            dias_inversion = int(row["Días de Inversión"])
            tasa_diaria = (row["Tasa Anual (%)"] / 100) / 365
            
            # Aplicar depósitos y extracciones al capital de la fila
            capital_efectivo = capital_inicial_fila + row["Depósito Adicional ($)"] - row["Extracción ($)"]
            
            saldo_actual = capital_efectivo
            interes_ganado_periodo = 0.0

            # Calcular interés compuesto diario
            for i in range(dias_inversion):
                interes_diario = saldo_actual * tasa_diaria
                saldo_actual += interes_diario
            
            interes_ganado_periodo = saldo_actual - capital_efectivo
            
            # Guardar el resultado de la fila
            resultados.append({
                "Capital Inicial ($)": capital_inicial_fila,
                "Depósito Adicional ($)": row["Depósito Adicional ($)"],
                "Extracción ($)": row["Extracción ($)"],
                "Capital Invertido ($)": capital_efectivo,
                "Días de Inversión": dias_inversion,
                "Tasa Anual (%)": row["Tasa Anual (%)"],
                "Interés Ganado ($)": interes_ganado_periodo,
                "Saldo Final ($)": saldo_actual
            })

        # --- MOSTRAR RESULTADOS ---
        if resultados:
            df_resultados = pd.DataFrame(resultados)

            with st.container(border=True):
                st.header("📊 Resultados de la Simulación")
                
                # Formatear columnas para mejor visualización
                df_display = df_resultados.copy()
                columnas_dinero = [
                    "Capital Inicial ($)", "Depósito Adicional ($)", "Extracción ($)",
                    "Capital Invertido ($)", "Interés Ganado ($)", "Saldo Final ($)"
                ]
                for col in columnas_dinero:
                    df_display[col] = df_display[col].apply(lambda x: f"${x:,.2f}")
                
                st.dataframe(df_display, use_container_width=True, hide_index=True)

                # Métricas totales
                st.markdown("---")
                st.markdown("##### Totales de la Simulación")
                total_interes = df_resultados["Interés Ganado ($)"].sum()
                total_depositos = df_resultados["Depósito Adicional ($)"].sum()
                total_extracciones = df_resultados["Extracción ($)"].sum()

                col1, col2, col3 = st.columns(3)
                col1.metric("Total Intereses Ganados", f"${total_interes:,.2f}")
                col2.metric("Total Depósitos", f"${total_depositos:,.2f}")
                col3.metric("Total Extracciones", f"${total_extracciones:,.2f}")

        else:
            st.warning("No hay datos para calcular. Agregá al menos un período.")
