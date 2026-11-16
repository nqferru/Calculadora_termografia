import streamlit as st
import requests
import json
from datetime import datetime
from fpdf import FPDF

st.set_page_config(page_title="Inspector Termográfico", page_icon="🌡️", layout="centered")

def enviar_a_sharepoint(datos):
    webhook_url = st.secrets["WEBHOOK_URL"]
    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(datos),
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return False

st.title("Inspector Termográfico")
st.caption("ASISTENTE PREDICTIVO SAP PM - CMPC")

# 0. Datos de Registro
st.subheader("0. Identificación del Equipo")
tag_equipo = st.text_input("TAG de Equipo (Solo números)", placeholder="Ej: 3001")

tag_is_valid = True
if tag_equipo and not tag_equipo.isdigit():
    st.error("El TAG del equipo debe ser numérico. Revisa el valor ingresado.")
    tag_is_valid = False

# 1. Ingreso de Datos
st.markdown("---")
st.subheader("1. Parámetros de Inspección")
col1, col2 = st.columns(2)
with col1:
    t_amb = st.number_input("T. Ambiente (°C)", value=None, format="%.1f")
    i_nom = st.number_input("Corriente Nominal (A)", value=None, min_value=0.1, format="%.1f")
with col2:
    t_max = st.number_input("T. Máx Conexión (°C)", value=None, format="%.1f")
    i_med = st.number_input("Corriente Medida (A)", value=None, min_value=0.1, format="%.1f")

# Función PDF
def generar_pdf(tag, texto_sap):
    pdf = FPDF()
    pdf.add_page()
    safe_text = texto_sap.replace("Δ", "Delta ").replace("°", " grados ")
    
    pdf.set_font("helvetica", style="B", size=16)
    pdf.cell(0, 10, "INFORME TERMOGRAFICO PREDICTIVO", ln=True, align="C")
    
    pdf.set_font("helvetica", size=10)
    pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="R")
    
    pdf.set_font("helvetica", style="B", size=12)
    pdf.cell(0, 8, f"Ubicacion Tecnica (TAG): {tag if tag else 'NO ESPECIFICADO'}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("helvetica", size=11)
    pdf.multi_cell(0, 7, text=safe_text)
        
    return bytes(pdf.output())

# CONDICIÓN DE EJECUCIÓN DEL ANÁLISIS
if tag_is_valid and t_amb is not None and t_max is not None and i_nom is not None and i_med is not None and i_nom > 0 and i_med > 0:
    delta_t = round(t_max - t_amb, 1)
    carga = round((i_med / i_nom) * 100, 1)

    st.markdown("---")
    st.subheader("2. Análisis de Severidad")
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("ΔT Medido", f"{delta_t} °C")
    col_m2.metric("% Carga Actual", f"{carga}%")

    is_nok = False
    nok_reasons = []
    priority = ''
    delta_t_100_str = "N/A"
    delta_t_100_json = "N/A"
    status = 'IDLE'
    status_msg = ''

    if carga < 30:
        col_m3.metric("ΔT Proyectado (100%)", "Inválido (<30% Carga)")
        if delta_t >= 15 or t_max >= 50:
            is_nok = True
            priority = 'CRÍTICA (Falla severa en vacío)'
            if delta_t >= 15: nok_reasons.append(f'ΔT excesivo para baja carga ({delta_t}°C)')
            if t_max >= 50: nok_reasons.append(f'T_máx anormal en vacío ({t_max}°C)')
        else:
            status = 'WARNING'
            status_msg = 'Carga insuficiente (<30%). No hay flujo de electrones necesario para manifestar resistencia de contacto.'
            priority = 'INCONCLUSO (Reevaluar en régimen)'
    else:
        delta_t_100_val = round(delta_t * ((i_nom / i_med) ** 1.6), 1)
        delta_t_100_str = f"{delta_t_100_val} °C"
        delta_t_100_json = delta_t_100_val
        col_m3.metric("ΔT Proyectado", delta_t_100_str)

        if delta_t_100_val >= 25 or t_max >= 60:
            is_nok = True
            priority = 'URGENTE (Intervenir en parada)'
            if delta_t_100_val >= 25: nok_reasons.append(f'ΔT Proyectado ≥ 25°C ({delta_t_100_val}°C)')
            if t_max >= 60: nok_reasons.append(f'T_máx crítica ({t_max}°C)')
        elif delta_t_100_val >= 18 or t_max >= 48:
            is_nok = True
            priority = 'ALTA (< 7 días)'
            if delta_t_100_val >= 18: nok_reasons.append(f'ΔT Proyectado ≥ 18°C ({delta_t_100_val}°C)')
            if t_max >= 48: nok_reasons.append(f'T_máx alta ({t_max}°C)')
        elif delta_t_100_val >= 12:
            is_nok = True
            priority = 'MEDIA (Monitorear)'
            if delta_t_100_val >= 12: nok_reasons.append(f'ΔT Proyectado ≥ 12°C ({delta_t_100_val}°C)')
        else:
            priority = 'NORMAL'

    if is_nok:
        status = 'NOK'
        status_msg = 'Anomalía Térmica Confirmada por matriz de severidad.'
    elif status != 'WARNING':
        status = 'OK'
        status_msg = 'Calentamiento acorde al nivel de carga real. Operación dentro de tolerancia.'

    sap_text = f"""[AVISO M2 - TERMOGRAFÍA]
EQUIPO (TAG): {tag_equipo if tag_equipo else 'N/A'}

ESTADO: {status}
PRIORIDAD: {priority}

MEDICIONES:
- T. Máxima: {t_max} °C
- T. Ambiente: {t_amb} °C

ANÁLISIS DE CARGA:
- Carga Actual: {carga}%
- ΔT Medido: {delta_t} °C
- ΔT Proyectado (100%): {delta_t_100_str}

DIAGNÓSTICO:
{status_msg}
MOTIVOS: {', '.join(nok_reasons) if nok_reasons else 'Ninguno'}"""

    st.markdown("---")
    if status == 'OK':
        st.success(f"**ESTADO: {status}**\n\n{status_msg}")
    elif status == 'NOK':
        st.error(f"**ESTADO: {status}**\n\n{status_msg}")
    elif status == 'WARNING':
        st.warning(f"**ESTADO: {status}**\n\n{status_msg}")
        
    st.caption("Texto estandarizado para SAP PM (Aviso M2)")
    st.code(sap_text, language="text")
    
    st.markdown("---")
    st.subheader("3. Acciones de Registro")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("☁️ Enviar a SharePoint", use_container_width=True):
            if not tag_equipo:
                st.error("Falta ingresar el TAG de Equipo (Sección 0).")
            else:
                datos_json = {
                    'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'TAG_Equipo': int(tag_equipo),
                    'T_Amb': t_amb,
                    'T_Max': t_max,
                    'I_Nom': i_nom,
                    'I_Med': i_med,
                    'Carga_Pct': carga,
                    'Delta_T_Medido': delta_t,
                    'Delta_T_100': delta_t_100_json,
                    'Estado': status
                }
                
                with st.spinner("Enviando a SharePoint..."):
                    if enviar_a_sharepoint(datos_json):
                        st.success("✅ Registro ingresado exitosamente en SharePoint.")

    with col_btn2:
        pdf_bytes = generar_pdf(tag_equipo, sap_text)
        fecha_str = datetime.now().strftime('%Y%m%d_%H%M')
        nombre_pdf = f"Termografia_TAG{tag_equipo if tag_equipo else 'N-A'}_{fecha_str}.pdf"
        
        st.download_button(
            label="📄 Descargar Reporte PDF",
            data=pdf_bytes,
            file_name=nombre_pdf,
            mime="application/pdf",
            type="primary",
            use_container_width=True
    )
