import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Calculadora de Inversión por Períodos",
    page_icon="📈",
    layout="wide",
)

# --- TÍTULO Y DESCRIPCIÓN ---
st.title("📈 Calculadora de Inversión por Períodos")
st.markdown("Simulá tus inversiones período por período, como en una hoja de cálculo.")

# --- INICIALIZACIÓN DEL ESTADO ---
if 'periodos' not in st.session_state:
    # Creamos un DataFrame de ejemplo con la nueva estructura
    st.session_state.periodos = pd.DataFrame(
        [
            {
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
    st.header("1. 💵 Capital y Períodos de Inversión")
    
    capital_inicial = st.number_input(
        "Capital Inicial ($)", 
        min_value=0.0, 
        value=1000000.0, 
        step=50000.0, 
        format="%.2f",
        help="El monto con el que comenzás tu primera inversión."
    )

    st.markdown("##### Agregá, editá o eliminá los períodos de tu inversión directamente en la tabla:")
    
    # Editor de datos interactivo con la nueva estructura
    edited_df = st.data_editor(
        st.session_state.periodos,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
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
                help="Dinero que agregás al inicio de este período.",
                format="$ %.2f",
            ),
            "Extracción ($)": st.column_config.NumberColumn(
                "Extracción ($)",
                help="Dinero que retirás al inicio de este período.",
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
if st.button("🚀 Calcular y Graficar Simulación", type="primary", use_container_width=True):
    
    df_periodos = st.session_state.periodos.copy()
    
    if df_periodos.isnull().values.any():
        st.error("⚠️ Hay celdas vacías en la tabla. Por favor, completá todos los datos.")
    else:
        # --- LÓGICA DE CÁLCULO SECUENCIAL ---
        df_periodos = df_periodos.sort_values(by="Fecha Inicio").reset_index(drop=True)
        
        datos_grafico = []
        resumen_periodos = []
        
        saldo_periodo_anterior = capital_inicial
        capital_aportado_acumulado = capital_inicial
        interes_acumulado_total = 0.0

        for index, row in df_periodos.iterrows():
            # El capital inicial de este período es el saldo final del anterior
            capital_inicial_periodo = saldo_periodo_anterior
            
            # Aplicar depósitos y extracciones
            capital_inicial_periodo += row["Depósito Adicional ($)"]
            capital_inicial_periodo -= row["Extracción ($)"]
            capital_aportado_acumulado += row["Depósito Adicional ($)"]
            capital_aportado_acumulado -= row["Extracción ($)"]

            saldo_actual = capital_inicial_periodo
            interes_ganado_periodo = 0.0
            
            fecha_inicio_periodo = row["Fecha Inicio"]
            dias_inversion = int(row["Días de Inversión"])
            tasa_diaria = (row["Tasa Anual (%)"] / 100) / 365

            # Registrar estado al inicio del período
            datos_grafico.append({
                "fecha": fecha_inicio_periodo, "saldo_total": saldo_actual,
                "capital_aportado": capital_aportado_acumulado, "interes_ganado": interes_acumulado_total
            })

            # Calcular interés compuesto diario
            for i in range(dias_inversion):
                interes_diario = saldo_actual * tasa_diaria
                interes_ganado_periodo += interes_diario
                saldo_actual += interes_diario
                
                fecha_diaria = fecha_inicio_periodo + timedelta(days=i + 1)
                datos_grafico.append({
                    "fecha": fecha_diaria, "saldo_total": saldo_actual,
                    "capital_aportado": capital_aportado_acumulado, "interes_ganado": interes_acumulado_total + interes_ganado_periodo
                })

            interes_acumulado_total += interes_ganado_periodo
            fecha_fin_periodo = fecha_inicio_periodo + timedelta(days=dias_inversion)
            
            # Guardar resumen del período
            resumen_periodos.append({
                "Período": index + 1,
                "Fecha Inicio": fecha_inicio_periodo,
                "Fecha Fin": fecha_fin_periodo,
                "Capital Inicial Período": capital_inicial_periodo,
                "Interés Ganado Período": interes_ganado_periodo,
                "Saldo Final Período": saldo_actual
            })
            
            saldo_periodo_anterior = saldo_actual

        # --- MOSTRAR RESULTADOS ---
        if datos_grafico:
            df_grafico = pd.DataFrame(datos_grafico).drop_duplicates(subset='fecha', keep='last').sort_values(by='fecha')
            df_resumen = pd.DataFrame(resumen_periodos)

            with st.container(border=True):
                st.header("📊 Resultados de la Simulación")
                
                # Métricas generales
                col_metrica1, col_metrica2, col_metrica3 = st.columns(3)
                col_metrica1.metric("Saldo Final Calculado", f"${saldo_periodo_anterior:,.2f}")
                col_metrica2.metric("Capital Aportado Neto", f"${capital_aportado_acumulado:,.2f}")
                col_metrica3.metric("Intereses Ganados Totales", f"${interes_acumulado_total:,.2f}")
                
                # --- NUEVA TABLA DE RESUMEN POR PERÍODO ---
                st.markdown("##### Resumen por Período")
                df_display_resumen = df_resumen.copy()
                for col in ["Capital Inicial Período", "Interés Ganado Período", "Saldo Final Período"]:
                    df_display_resumen[col] = df_display_resumen[col].apply(lambda x: f"${x:,.2f}")
                st.dataframe(df_display_resumen, use_container_width=True, hide_index=True)


                # Gráfico de evolución diaria
                st.markdown("##### Evolución Diaria de la Inversión")
                fig = px.line(
                    df_grafico, x='fecha', y=['saldo_total', 'capital_aportado', 'interes_ganado'],
                    template="plotly_dark",
                    labels={'value': 'Monto ($)', 'fecha': 'Fecha', 'variable': 'Componente'},
                    color_discrete_map={
                        'saldo_total': '#1f77b4', 'capital_aportado': '#ff7f0e', 'interes_ganado': '#2ca02c'
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("Ver tabla de datos diarios detallados"):
                    df_display_grafico = df_grafico.copy()
                    for col in ['saldo_total', 'capital_aportado', 'interes_ganado']:
                        df_display_grafico[col] = df_display_grafico[col].apply(lambda x: f"${x:,.2f}")
                    st.dataframe(df_display_grafico, use_container_width=True, hide_index=True)
        else:
            st.warning("No hay datos para calcular. Agregá al menos un período.")
