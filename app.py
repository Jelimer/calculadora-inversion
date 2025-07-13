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
    # Creamos un DataFrame de ejemplo para empezar
    st.session_state.periodos = pd.DataFrame(
        [
            {
                "Fecha Inicio": date(2024, 1, 1),
                "Fecha Fin": date(2024, 1, 31),
                "Depósito Adicional": 0.0,
                "Extracción": 0.0,
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
    
    # Editor de datos interactivo, como una hoja de cálculo
    edited_df = st.data_editor(
        st.session_state.periodos,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Fecha Inicio": st.column_config.DateColumn(
                "Fecha de Inicio",
                required=True,
                format="DD/MM/YYYY",
            ),
            "Fecha Fin": st.column_config.DateColumn(
                "Fecha de Fin",
                required=True,
                format="DD/MM/YYYY",
            ),
            "Depósito Adicional": st.column_config.NumberColumn(
                "Depósito Adicional ($)",
                help="Dinero que agregás al inicio de este período.",
                format="$ %.2f",
            ),
            "Extracción": st.column_config.NumberColumn(
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
    
    # Actualizar el estado de la sesión con los datos editados
    st.session_state.periodos = edited_df

# --- BOTÓN DE CÁLCULO ---
st.markdown("---")
if st.button("🚀 Calcular y Graficar Simulación", type="primary", use_container_width=True):
    
    df_periodos = st.session_state.periodos.copy()
    
    # Validaciones de datos
    if df_periodos.isnull().values.any():
        st.error("⚠️ Hay celdas vacías en la tabla. Por favor, completá todos los datos.")
    elif (df_periodos['Fecha Fin'] < df_periodos['Fecha Inicio']).any():
        st.error("⚠️ Hay períodos donde la 'Fecha Fin' es anterior a la 'Fecha Inicio'.")
    else:
        # --- LÓGICA DE CÁLCULO POR PERÍODOS ---
        df_periodos = df_periodos.sort_values(by="Fecha Inicio").reset_index(drop=True)
        
        datos_grafico = []
        saldo_actual = capital_inicial
        capital_aportado_neto = capital_inicial
        interes_total_ganado = 0.0

        fecha_anterior_fin = None

        for index, row in df_periodos.iterrows():
            fecha_inicio_periodo = row["Fecha Inicio"]
            fecha_fin_periodo = row["Fecha Fin"]
            
            # Si hay un hueco entre períodos, mantenemos el saldo sin cambios
            if fecha_anterior_fin and fecha_inicio_periodo > fecha_anterior_fin:
                dias_hueco = (fecha_inicio_periodo - fecha_anterior_fin).days
                for i in range(dias_hueco):
                    fecha_diaria = fecha_anterior_fin + timedelta(days=i + 1)
                    datos_grafico.append({
                        "fecha": fecha_diaria,
                        "saldo_total": saldo_actual,
                        "capital_aportado": capital_aportado_neto,
                        "interes_ganado": interes_total_ganado
                    })

            # Aplicar depósitos y extracciones al inicio del período
            saldo_actual += row["Depósito Adicional"]
            saldo_actual -= row["Extracción"]
            capital_aportado_neto += row["Depósito Adicional"]
            capital_aportado_neto -= row["Extracción"]
            
            # Registrar el estado al inicio del período (después de la transacción)
            datos_grafico.append({
                "fecha": fecha_inicio_periodo,
                "saldo_total": saldo_actual,
                "capital_aportado": capital_aportado_neto,
                "interes_ganado": interes_total_ganado
            })
            
            # Calcular interés compuesto diario dentro del período
            tasa_diaria = (row["Tasa Anual (%)"] / 100) / 365
            dias_periodo = (fecha_fin_periodo - fecha_inicio_periodo).days

            for i in range(dias_periodo):
                interes_diario = saldo_actual * tasa_diaria
                interes_total_ganado += interes_diario
                saldo_actual += interes_diario
                
                fecha_diaria = fecha_inicio_periodo + timedelta(days=i + 1)
                datos_grafico.append({
                    "fecha": fecha_diaria,
                    "saldo_total": saldo_actual,
                    "capital_aportado": capital_aportado_neto,
                    "interes_ganado": interes_total_ganado
                })
            
            fecha_anterior_fin = fecha_fin_periodo

        # --- MOSTRAR RESULTADOS ---
        if datos_grafico:
            df_grafico = pd.DataFrame(datos_grafico).drop_duplicates(subset='fecha', keep='last').sort_values(by='fecha')
            
            with st.container(border=True):
                st.header("📊 Resultados de la Simulación")
                
                col_metrica1, col_metrica2, col_metrica3 = st.columns(3)
                col_metrica1.metric("Saldo Final Calculado", f"${saldo_actual:,.2f}")
                col_metrica2.metric("Capital Aportado Neto", f"${capital_aportado_neto:,.2f}")
                col_metrica3.metric("Intereses Ganados Totales", f"${interes_total_ganado:,.2f}")

                fig = px.line(
                    df_grafico, 
                    x='fecha', 
                    y=['saldo_total', 'capital_aportado', 'interes_ganado'],
                    title="Evolución de la Inversión: Saldo vs Capital vs Intereses",
                    template="plotly_dark",
                    labels={'value': 'Monto en Pesos ($)', 'fecha': 'Línea de Tiempo', 'variable': 'Componente'},
                    color_discrete_map={
                        'saldo_total': '#1f77b4',
                        'capital_aportado': '#ff7f0e',
                        'interes_ganado': '#2ca02c'
                    }
                )
                fig.update_layout(
                    font=dict(family="Arial, sans-serif", size=12, color="white"),
                    plot_bgcolor='rgba(0,0,0,0.3)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("Ver tabla de datos diarios del gráfico"):
                    df_display = df_grafico.copy()
                    for col in ['saldo_total', 'capital_aportado', 'interes_ganado']:
                        df_display[col] = df_display[col].apply(lambda x: f"${x:,.2f}")
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.warning("No hay datos para calcular. Agregá al menos un período.")
