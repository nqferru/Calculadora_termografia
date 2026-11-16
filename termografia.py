import streamlit as st

st.set_page_config(page_title="Inspector Termográfico", page_icon="🌡️", layout="centered")

st.title("Inspector Termográfico")
st.caption("ASISTENTE PREDICTIVO SAP PM")

# 1. Mediciones Base
st.subheader("1. Mediciones Base")
col1, col2 = st.columns(2)
with col1:
    t_amb = st.number_input("T. Ambiente (°C)", value=None, format="%.1f")
with col2:
    t_max = st.number_input("T. Máx Conexión (°C)", value=None, format="%.1f")

if t_amb is not None and t_max is not None:
    delta_t = round(t_max - t_amb, 1)
    
    # Mostrar Delta T
    if delta_t >= 15:
        st.error(f"**Delta T (ΔT): {delta_t} °C**")
    else:
        st.success(f"**Delta T (ΔT): {delta_t} °C**")

    # Condición de disparo para medir corriente
    needs_current = (t_max >= 45) or (delta_t >= 15)

    status = 'IDLE'
    status_msg = ''
    sap_text = ''
    
    if not needs_current:
        status = 'OK'
        status_msg = 'Tablero dentro de parámetros normales. No requiere medición de corriente.'
    else:
        st.warning("⚠️ Umbral preventivo superado (T_máx ≥ 45°C o ΔT ≥ 15°C). Requiere medir corriente para evaluar severidad.")
        
        # 2. Análisis de Carga Requerido
        st.subheader("2. Análisis de Carga Requerido")
        col3, col4 = st.columns(2)
        with col3:
            i_nom = st.number_input("Corriente Nominal (A)", value=None, min_value=0.1, format="%.1f")
        with col4:
            i_med = st.number_input("Corriente Medida (A)", value=None, min_value=0.1, format="%.1f")
            
        asimetria = st.number_input("Asimetría entre Fases (°C) (Opcional)", value=None, format="%.1f")
        asim_val = asimetria if asimetria is not None else 0.0

        if i_nom is not None and i_med is not None and i_nom > 0 and i_med > 0:
            carga = round((i_med / i_nom) * 100, 1)
            delta_t_100 = round(delta_t * ((i_nom / i_med) ** 1.6), 1)

            st.markdown("---")
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("% Carga Actual", f"{carga}%")
            col_m2.metric("ΔT Proyectado (100%)", f"{delta_t_100} °C")

            # Matriz de Decisión
            is_nok = False
            nok_reasons = []
            priority = ''
            c = carga
            dt = delta_t

            if c >= 80:
                if dt >= 25: is_nok = True; nok_reasons.append('ΔT ≥ 25°C')
                if t_max >= 60: is_nok = True; nok_reasons.append('T_máx ≥ 60°C')
                if asim_val >= 15: is_nok = True; nok_reasons.append('Asimetría ≥ 15°C')
                priority = 'URGENTE (Intervenir en parada)'
            elif c >= 60:
                if dt >= 18: is_nok = True; nok_reasons.append('ΔT ≥ 18°C')
                if t_max >= 48: is_nok = True; nok_reasons.append('T_máx ≥ 48°C')
                if asim_val >= 10: is_nok = True; nok_reasons.append('Asimetría ≥ 10°C')
                priority = 'ALTA (< 7 días)'
            elif c >= 40:
                if dt >= 12: is_nok = True; nok_reasons.append('ΔT ≥ 12°C')
                if t_max >= 39: is_nok = True; nok_reasons.append('T_máx ≥ 39°C')
                if asim_val >= 6: is_nok = True; nok_reasons.append('Asimetría ≥ 6°C')
                priority = 'ALTA (Peligro al subir carga)'
            elif c >= 20:
                if dt >= 7: is_nok = True; nok_reasons.append('ΔT ≥ 7°C')
                if t_max >= 32: is_nok = True; nok_reasons.append('T_máx ≥ 32°C')
                if asim_val >= 3: is_nok = True; nok_reasons.append('Asimetría ≥ 3°C')
                priority = 'INMEDIATA (Falso contacto activo)'
            else:
                if t_max >= 30: is_nok = True; nok_reasons.append('T_máx ≥ 30°C en vacío')
                if asim_val >= 2: is_nok = True; nok_reasons.append('Asimetría ≥ 2°C en vacío')
                priority = 'CRÍTICA (Evaluar con carga)'

            if is_nok:
                status = 'NOK'
                status_msg = f"Anomalía Térmica Detectada. Prioridad: {priority}."
            else:
                status = 'OK'
                status_msg = 'Calentamiento acorde al nivel de carga. Operación normalizada.'
                
            # Renderizado de SAP Text
            if status == 'OK':
                sap_text = f"ESTADO: OK | T_max: {t_max}°C | T_amb: {t_amb}°C | DeltaT: {delta_t}°C | Operación Normal."
            elif status == 'NOK':
                sap_text = f"ESTADO: NOK | T_max: {t_max}°C | T_amb: {t_amb}°C | Carga: {carga}% | DeltaT: {delta_t}°C (Proyectado 100%: {delta_t_100}°C) | Motivo: {', '.join(nok_reasons)} | Prioridad: {priority}"

    # 3. Status / Output
    if status != 'IDLE':
        st.markdown("---")
        if status == 'OK':
            st.success(f"**ESTADO: {status}**\n\n{status_msg}")
        elif status == 'NOK':
            st.error(f"**ESTADO: {status}**\n\n{status_msg}")
            
        if sap_text:
            st.caption("Texto estandarizado para SAP PM (Aviso M2)")
            # st.code incluye un botón nativo de copia al portapapeles en la esquina superior derecha
            st.code(sap_text, language=None)