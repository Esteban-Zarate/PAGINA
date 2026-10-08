import streamlit as st
import math


def mostrar_energia_viva(usuario=None, es_admin=False):
    nombre = (usuario or {}).get('nombre_completo') if isinstance(usuario, dict) else None
    nombre = nombre or 'Usuario'
    st.markdown('''
    <div class="hero-header">
      <div class="hero-title">🌎 ENERGÍA VIVA</div>
      <div class="hero-sub">INTELIGENCIA PARA UNA ENERGÍA MÁS SEGURA, EFICIENTE Y SOSTENIBLE</div>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown(f"### Hola, {nombre} 👋")
    st.write("ENERGÍA VIVA convierte tus datos de consumo y energía en información comprensible y recomendaciones educativas. Es una propuesta propia y no copia el diseño, textos ni código de otra plataforma.")

    consumo_mes = st.number_input("Consumo mensual de tu hogar (kWh)", min_value=0.0, value=197.0, step=1.0)
    consumo_dia = consumo_mes / 30 if consumo_mes else 0
    personas = st.number_input("Personas en la vivienda", min_value=1, value=3, step=1)
    tiene_solar = st.selectbox("¿Ya tienes paneles solares?", ["No", "Sí"])

    if consumo_dia:
        hsp = 4.5
        panel_wp = 620
        rendimiento = 0.80
        paneles = max(1, math.ceil((consumo_dia * 1000) / (panel_wp * hsp * rendimiento)))
        indice_consumo = max(0, min(100, round(100 - consumo_dia * 5)))
        st.markdown("### ⚡ Tu diagnóstico energético inicial")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Consumo diario", f"{consumo_dia:.2f} kWh")
        c2.metric("Personas", str(int(personas)))
        c3.metric("Paneles de referencia", str(paneles))
        c4.metric("Índice de consumo", f"{indice_consumo}/100")

    st.markdown("### 🧠 ¿Qué quieres analizar?")
    a, b, c = st.columns(3)
    if a.button("☀️ Potencial solar", use_container_width=True):
        st.session_state["modulo_activo"] = "chatbot"
        st.session_state["eco_prefill"] = f"Analiza mi consumo de {consumo_mes:.0f} kWh/mes y dime qué sistema solar podría convenirme."
        st.rerun()
    if b.button("⚡ Problema eléctrico", use_container_width=True):
        st.session_state["modulo_activo"] = "chatbot"
        st.session_state["eco_prefill"] = "Tengo un problema eléctrico en mi vivienda. Ayúdame a identificar posibles causas y dime qué información necesitas."
        st.rerun()
    if c.button("💰 Ahorro energético", use_container_width=True):
        st.session_state["modulo_activo"] = "chatbot"
        st.session_state["eco_prefill"] = f"Quiero reducir mi consumo de {consumo_mes:.0f} kWh/mes. Dame recomendaciones de ahorro seguras y prácticas."
        st.rerun()

    st.markdown("### 🚦 Guía rápida")
    st.info("🔴 Riesgo o problema eléctrico: no intervengas instalaciones energizadas; solicita personal calificado.  🟠 Revisa consumos y equipos.  🟢 Mejora hábitos y eficiencia.")

    st.markdown("### 🔋 Compara los sistemas")
    c1, c2, c3 = st.columns(3)
    c1.markdown("**OFF-GRID**\n\nAislado de la red y con baterías. Útil cuando no hay red o se busca autonomía. Mayor inversión y necesidad de almacenamiento.")
    c2.markdown("**ON-GRID**\n\nConectado a la red y normalmente sin baterías. Puede reducir consumo de red, pero un sistema convencional no reemplaza el respaldo durante un corte.")
    c3.markdown("**HÍBRIDO**\n\nCombina solar, red y baterías. Ofrece respaldo y flexibilidad, con mayor complejidad y costo.")

    if es_admin:
        st.markdown("### 🛡️ Vista de administrador")
        st.success("Tienes acceso administrativo. EcoBot Solar y los módulos de asistencia están disponibles para ti igual que para los usuarios registrados.")
