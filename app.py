import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta
import io

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Simulador de Inversión PF vs Dólar",
    page_icon="⚖️",
    layout="wide",
)

# --- TÍTULO Y DESCRIPCIÓN ---
st.title("⚖️ Simulador Comparativo: Plazo Fijo vs. Dólar")
st.markdown("Analizá el rendimiento de una secuencia de plazos fijos en pesos contra la devaluación del dólar.")

# --- SECCIÓN DE ENTRADA DE DATOS ---
with st.container(border=True):
    st.header("📊 Parámetros de la Simulación")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        capital_input = st.number_input('Capital Inicial (ARS):', value=3958892.0, format="%.2f")
        fecha_inicial_input = st.date_input('Fecha Inicial:', value=date.today() - timedelta(days=125))
    
    with col2:
        dolar_inicial_input = st.number_input('Dólar Inicial:', value=1175.0, format="%.2f")
        fecha_final_input = st.date_input('Fecha Final:', value=date.today())

    with col3:
        dolar_final_input = st.number_input('Dólar Final (Hoy):', value=1265.0, format="%.2f")

    st.markdown("---")
    col_seq1, col_seq2 = st.columns(2)
    with col_seq1:
        plazos_input = st.text_input('Secuencia de Plazos (días):', value='30, 60, 31', placeholder='Ej: 30, 60, 31')
    with col_seq2:
        tasas_input = st.text_input('Secuencia de Tasas (TNA %):', value='33, 31.5, 30', placeholder='Ej: 33, 31.5, 30')


# --- BOTÓN DE CÁLCULO ---
st.markdown("---")
if st.button("Calcular y Graficar", type="primary", use_container_width=True):
    # --- 1. LECTURA Y VALIDACIÓN DE DATOS ---
    try:
        capital_inicial_ars = capital_input
        dolar_venta_inicial = dolar_inicial_input
        dolar_hoy = dolar_final_input
        
        lista_de_plazos = [int(p.strip()) for p in plazos_input.split(',') if p.strip()]
        lista_de_tasas = [float(t.strip())/100 for t in tasas_input.split(',') if t.strip()]

        if any(p <= 0 for p in lista_de_plazos):
            st.error("❌ Error: Todos los plazos deben ser mayores a 0.")
            st.stop()
        if len(lista_de_plazos) != len(lista_de_tasas):
            st.error(f"❌ Error: La cantidad de plazos ({len(lista_de_plazos)}) no coincide con la cantidad de tasas ({len(lista_de_tasas)}).")
            st.stop()
            
        dias_inversion = (fecha_final_input - fecha_inicial_input).days
        if dias_inversion < 0:
            st.error("❌ Error: La fecha final no puede ser anterior a la fecha inicial.")
            st.stop()

    except (ValueError, TypeError):
        st.error("❌ Error: Formato incorrecto en los datos de entrada. Revisa los números y las fechas.")
        st.stop()

    # --- 2. LÓGICA DE CÁLCULO (IDÉNTICA A TU CÓDIGO) ---
    evolucion_pf_escalonado, plazos_efectuados, tasas_efectuadas = [], [], []
    capital_actual = capital_inicial_ars
    dias_transcurridos_total = 0

    for i in range(len(lista_de_plazos)):
        plazo_dias, tna_plazo_fijo = lista_de_plazos[i], lista_de_tasas[i]
        if dias_transcurridos_total + plazo_dias > dias_inversion:
            break
        
        # Guardar el capital durante el plazo (para el gráfico escalonado)
        for _ in range(plazo_dias):
            if len(evolucion_pf_escalonado) < dias_inversion + 1:
                evolucion_pf_escalonado.append(capital_actual)
        
        tasa_periodo = (tna_plazo_fijo / 365) * plazo_dias
        capital_actual *= (1 + tasa_periodo)
        dias_transcurridos_total += plazo_dias
        plazos_efectuados.append(plazo_dias)
        tasas_efectuadas.append(tna_plazo_fijo * 100)

    # Rellenar los días restantes si la simulación no cubre todo el período
    for _ in range(dias_inversion - dias_transcurridos_total + 1):
        if len(evolucion_pf_escalonado) < dias_inversion + 1:
            evolucion_pf_escalonado.append(capital_actual)
    
    capital_final_pf_ars = capital_actual

    # --- 3. CÁLCULO DE MÉTRICAS FINANCIERAS ---
    dolares_originales = capital_inicial_ars / dolar_venta_inicial
    valor_final_dolares_ars = dolares_originales * dolar_hoy
    dolares_finales_comprables = capital_final_pf_ars / dolar_hoy
    rendimiento_pf_ars_pct = (capital_final_pf_ars / capital_inicial_ars) - 1
    rendimiento_dolar_ars_pct = (valor_final_dolares_ars / capital_inicial_ars) - 1
    rendimiento_pf_usd_pct = (dolares_finales_comprables / dolares_originales) - 1
    dolar_breakeven = capital_final_pf_ars / dolares_originales

    # --- 4. PRESENTACIÓN DE RESULTADOS ---
    with st.container(border=True):
        st.header("📈 Resultados de la Simulación")
        
        # --- TABLA DE RESUMEN ---
        summary_data = {
            "Estrategia": ["Plazo Fijo (ARS)", "Plazo Fijo (USD)", "Benchmark: Devaluación"],
            "Capital Inicial": [f"${capital_inicial_ars:,.0f}", f"u$s {dolares_originales:,.2f}", f"${capital_inicial_ars:,.0f}"],
            "Capital Final": [f"${capital_final_pf_ars:,.0f}", f"u$s {dolares_finales_comprables:,.2f}", f"${valor_final_dolares_ars:,.0f}"],
            "Rendimiento (%)": [rendimiento_pf_ars_pct, rendimiento_pf_usd_pct, rendimiento_dolar_ars_pct]
        }
        summary_df = pd.DataFrame(summary_data).set_index("Estrategia")
        st.dataframe(summary_df.style.format({"Rendimiento (%)": "{:+.2%}"}).background_gradient(cmap='RdYlGn', subset=['Rendimiento (%)'], vmin=-0.05, vmax=0.05))

        # --- BOLETÍN DE CALIFICACIONES ---
        st.markdown("##### 📝 Boletín de Calificaciones")
        st.text(f"Período de {dias_inversion} días, con {len(plazos_efectuados)} reinversiones.")
        st.text(f"Plazos aplicados (días): {plazos_efectuados}")
        st.text(f"Tasas TNA aplicadas (%): {[f'{t:.2f}' for t in tasas_efectuadas]}")

        # --- GRÁFICO CON PLOTLY ---
        rango_fechas = pd.date_range(start=fecha_inicial_input, end=fecha_final_input)
        evolucion_dolares = np.linspace(capital_inicial_ars, valor_final_dolares_ars, dias_inversion + 1)
        
        fig = go.Figure()

        # Línea de Plazo Fijo
        fig.add_trace(go.Scatter(x=rango_fechas, y=evolucion_pf_escalonado, mode='lines', name='Plazo Fijo Secuencial (ARS)', line=dict(color='#33AFFF', width=3, shape='hv')))
        # Línea de Dólar
        fig.add_trace(go.Scatter(x=rango_fechas, y=evolucion_dolares, mode='lines', name='Valor de los Dólares (ARS)', line=dict(color='#FF5733', width=3, dash='dash')))

        # Anotaciones de los escalones
        capital_anotacion = capital_inicial_ars
        dias_anotacion = 0
        for i in range(len(plazos_efectuados)):
            plazo_actual, tna_actual = plazos_efectuados[i], tasas_efectuadas[i] / 100
            tasa_periodo_actual = (tna_actual / 365) * plazo_actual
            interes_ganado = capital_anotacion * tasa_periodo_actual
            fecha_anotacion = fecha_inicial_input + timedelta(days=dias_anotacion + (plazo_actual / 2))
            
            fig.add_annotation(x=fecha_anotacion, y=capital_anotacion,
                               text=f"{plazo_actual}d | {tna_actual:.1%}<br>+${interes_ganado:,.0f}",
                               showarrow=False, bgcolor="rgba(0,0,0,0.6)", bordercolor="cyan", font=dict(color="cyan", size=10))
            capital_anotacion += interes_ganado
            dias_anotacion += plazo_actual
        
        # Puntos de inicio y fin
        fig.add_trace(go.Scatter(x=[rango_fechas[0], rango_fechas[-1], rango_fechas[-1]], 
                                 y=[capital_inicial_ars, capital_final_pf_ars, valor_final_dolares_ars],
                                 mode='markers+text',
                                 marker=dict(color=['white', '#33AFFF', '#FF5733'], size=10),
                                 text=[f"Inicio<br>${capital_inicial_ars:,.0f}", f"Final PF<br>${capital_final_pf_ars:,.0f}", f"Final Dólar<br>${valor_final_dolares_ars:,.0f}"],
                                 textposition=["middle left", "top center", "bottom center"],
                                 textfont=dict(size=12),
                                 showlegend=False))

        # Cuadro de resumen en el gráfico
        ganancia_bruta_ars = capital_final_pf_ars - capital_inicial_ars
        ganancia_neta_usd = dolares_finales_comprables - dolares_originales
        resumen_texto = (
            f"<b>📊 RESUMEN</b><br>"
            f"--------------------<br>"
            f"<b>Resultado en ARS:</b><br>"
            f"  Ganancia: ${ganancia_bruta_ars:,.2f}<br>"
            f"  Rendimiento: {rendimiento_pf_ars_pct:+.2%}<br>"
            f"<b>Resultado en USD:</b><br>"
            f"  Ganancia: u$s {ganancia_neta_usd:,.2f}<br>"
            f"  Rendimiento: {rendimiento_pf_usd_pct:+.2%}<br>"
            f"--------------------<br>"
            f"<b>⚖️ Equilibrio:</b><br>"
            f"  Dólar Hoy: ${dolar_hoy:,.2f}<br>"
            f"  Dólar Equilibrio: ${dolar_breakeven:,.2f}"
        )
        fig.add_annotation(x=0.02, y=0.98, xref="paper", yref="paper",
                           text=resumen_texto, showarrow=False, align="left",
                           font=dict(size=11, color="white"),
                           bgcolor="rgba(0,0,0,0.7)", bordercolor="yellow", borderwidth=1)
        
        fig.update_layout(
            title=f'Evolución de la Inversión: de u$s {dolares_originales:,.0f} a u$s {dolares_finales_comprables:,.0f}',
            yaxis_title='Valor en Pesos (ARS)',
            xaxis_title='Fecha',
            template='plotly_dark',
            legend=dict(yanchor="bottom", y=0.01, xanchor="right", x=0.99)
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- SECCIÓN DE DESCARGA ---
        st.markdown("---")
        st.markdown("##### 📥 Descargar Resultados")
        
        # Preparar reporte de texto para descarga
        reporte_texto = []
        reporte_texto.append("--- RESUMEN GENERAL DE LA OPERACIÓN ---\n")
        reporte_texto.append(summary_df.to_string(formatters={"Rendimiento (%)": '{:+.2%}'.format}))
        reporte_texto.append("\n\n--- BOLETÍN DE CALIFICACIONES ---\n")
        reporte_texto.append(f"Período de {dias_inversion} días, con {len(plazos_efectuados)} reinversiones.\n")
        reporte_texto.append(f"Plazos aplicados (días): {plazos_efectuados}\n")
        reporte_texto.append(f"Tasas TNA aplicadas (%): {[f'{t:.2f}' for t in tasas_efectuadas]}\n")
        reporte_final_str = "\n".join(reporte_texto)

        # Preparar imagen para descarga
        img_bytes = fig.to_image(format="png", width=1200, height=700, scale=2)

        col_desc1, col_desc2 = st.columns(2)
        with col_desc1:
            st.download_button(
                label="Descargar Gráfico (.png)",
                data=img_bytes,
                file_name="reporte_grafico.png",
                mime="image/png",
                use_container_width=True
            )
        with col_desc2:
            st.download_button(
                label="Descargar Reporte (.txt)",
                data=reporte_final_str,
                file_name="reporte_texto.txt",
                mime="text/plain",
                use_container_width=True
            )
