"""Prototipo ENERGYPLAN 360: levantamiento y plano de vivienda.
Las mediciones se introducen manualmente en esta versión; Bluetooth requiere hardware compatible.
"""
import streamlit as st
import pandas as pd
import html


def mostrar_planos_inteligentes():
    st.markdown("""<div style='padding:1rem 1.2rem;border-radius:16px;background:linear-gradient(120deg,#071a2b,#073c53);border:1px solid #16c8e8'>
    <div style='color:#38e8f4;font-size:.8rem;letter-spacing:2px'>ENERGYPLAN 360</div>
    <h1 style='color:white;margin:.2rem 0'>📐 Planos inteligentes</h1>
    <p style='color:#c9e6ef'>Mide · Dibuja · Organiza · Calcula</p></div>""", unsafe_allow_html=True)
    st.info("Prototipo inicial: registra medidas y puntos eléctricos. La lectura automática por Bluetooth y la generación CAD/BIM requieren integración adicional.")
    if "ep_medidas" not in st.session_state:
        st.session_state.ep_medidas = []
    if "ep_puntos" not in st.session_state:
        st.session_state.ep_puntos = []
    tab1, tab2, tab3 = st.tabs(["📏 Levantamiento", "⚡ Plano eléctrico", "📤 Exportar datos"])
    with tab1:
        st.subheader("Registrar medidas de la vivienda")
        with st.form("ep_add_measure"):
            a,b,c = st.columns([1,2,1])
            pared = a.text_input("Elemento", placeholder="Pared 1")
            medida = b.number_input("Longitud (m)", min_value=0.01, max_value=1000.0, value=3.50, step=0.05)
            orientacion = c.selectbox("Orientación", ["Horizontal", "Vertical", "Diagonal"])
            nota = st.text_input("Nota / espacio", placeholder="Sala, habitación, muro exterior...")
            if st.form_submit_button("➕ Guardar medición", use_container_width=True):
                st.session_state.ep_medidas.append({"Elemento": pared.strip() or f"Pared {len(st.session_state.ep_medidas)+1}", "Longitud (m)": round(medida,2), "Orientación": orientacion, "Espacio / nota": nota})
                st.success("Medición guardada.")
        if st.session_state.ep_medidas:
            df = pd.DataFrame(st.session_state.ep_medidas)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.metric("Longitud acumulada registrada", f"{df['Longitud (m)'].sum():.2f} m")
            if st.button("🗑️ Borrar todas las medidas"):
                st.session_state.ep_medidas = []
                st.rerun()
        else:
            st.caption("Aún no hay medidas registradas.")
    with tab2:
        st.subheader("Registrar elementos eléctricos")
        with st.form("ep_add_point"):
            a,b,c = st.columns(3)
            tipo = a.selectbox("Elemento", ["Luminaria", "Interruptor", "Tomacorriente", "Tablero principal", "Carga especial"])
            circuito = b.selectbox("Circuito", ["C1 - Iluminación", "C2 - Tomacorrientes", "C3 - Habitaciones", "C4 - Cocina", "C5 - Baño", "C6 - Carga especial"])
            espacio = c.text_input("Ubicación", placeholder="Sala / cocina...")
            if st.form_submit_button("➕ Agregar punto eléctrico", use_container_width=True):
                st.session_state.ep_puntos.append({"Elemento":tipo,"Circuito":circuito,"Ubicación":espacio})
                st.success("Punto eléctrico agregado.")
        if st.session_state.ep_puntos:
            st.dataframe(pd.DataFrame(st.session_state.ep_puntos), use_container_width=True, hide_index=True)
            selected = st.selectbox("Filtrar por circuito", ["Todos"] + sorted({p['Circuito'] for p in st.session_state.ep_puntos}))
            filtered = [p for p in st.session_state.ep_puntos if selected == "Todos" or p["Circuito"] == selected]
            st.caption(f"{len(filtered)} punto(s) en la selección.")
            if st.button("🗑️ Borrar puntos eléctricos"):
                st.session_state.ep_puntos = []
                st.rerun()
        else:
            st.caption("Añade luminarias, interruptores, tomacorrientes y circuitos.")
        st.warning("Este registro documenta el diseño; no reemplaza la verificación de seguridad, normativa ni el trabajo de personal competente.")
    with tab3:
        st.subheader("Descargar información del levantamiento")
        if st.session_state.ep_medidas:
            st.download_button("⬇️ Descargar medidas CSV", pd.DataFrame(st.session_state.ep_medidas).to_csv(index=False).encode("utf-8-sig"), "energyplan_medidas.csv", "text/csv", use_container_width=True)
        if st.session_state.ep_puntos:
            st.download_button("⬇️ Descargar plano eléctrico CSV", pd.DataFrame(st.session_state.ep_puntos).to_csv(index=False).encode("utf-8-sig"), "energyplan_puntos_electricos.csv", "text/csv", use_container_width=True)
        st.caption("La exportación DXF/DWG, Revit/BIM y la conexión Bluetooth se incorporarán en etapas posteriores.")
