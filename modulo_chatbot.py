# modulo_chatbot.py — VivaBot Solar
import os, re, math, streamlit as st

AUTOSOLAR_KITS = {
    "OFF-GRID": {
        "nombre": "Kit Solar Para Casa 3000W 48V 6500Wh/día con Batería Litio",
        "url": "https://autosolar.co/kits-solares-aislada/kit-solar-para-casa-3000w-48v-6500whdia-con-bateria-litio",
        "generacion_wh": 6500, "potencia_w": 3000, "paneles": 4,
        "panel_wp": 620, "bateria_kwh": 7.2, "bateria_util_kwh": 6.55,
        "detalle": "4 paneles bifaciales JA Solar 620 W, inversor-cargador Growatt 3000 W 48 V y batería de litio Pylontech US2000C."
    },
    "ON-GRID": {
        "nombre": "Kit Solar On Grid 6000W 12810Wh/día Growatt",
        "url": "https://autosolar.co/kits-solares-red/kit-solar-on-grid-6000w-12810whdia-growatt",
        "generacion_wh": 12810, "potencia_w": 6000, "paneles": 0,
        "panel_wp": 0, "bateria_kwh": 0, "bateria_util_kwh": 0,
        "detalle": "Kit conectado a red con inversor Growatt y protecciones; no incluye batería."
    },
    "HIBRIDO": {
        "nombre": "Kit Solar Híbrido 3000W 21350Wh/día Growatt",
        "url": "https://autosolar.co/kits-solares-hibridos/kit-solar-hibrido-3000w-21350whdia-growatt",
        "generacion_wh": 21350, "potencia_w": 3000, "paneles": 10,
        "panel_wp": 610, "bateria_kwh": 7.2, "bateria_util_kwh": 6.55,
        "detalle": "10 paneles bifaciales Tensite 610 W, inversor cargador Growatt, inversor On Grid Growatt y batería Pylontech de litio."
    },
}

SYSTEM_INFO = {
    "OFF-GRID": {
        "titulo": "OFF-GRID (aislado)",
        "desc": "Trabaja sin depender de la red eléctrica. Los paneles cargan las baterías y el inversor alimenta las cargas.",
        "ventajas": ["Autonomía frente a cortes de red", "Útil donde no existe red eléctrica", "Puede almacenar energía para la noche"],
        "desventajas": ["Necesita baterías", "Mayor inversión inicial", "El banco de baterías requiere dimensionamiento y mantenimiento"],
    },
    "ON-GRID": {
        "titulo": "ON-GRID (conectado a red)",
        "desc": "Los paneles producen energía para las cargas y el sistema permanece conectado a la red. Normalmente no utiliza baterías.",
        "ventajas": ["Menor costo que un sistema con baterías", "Buen aprovechamiento de la generación solar durante el día", "La red complementa el consumo cuando hace falta"],
        "desventajas": ["Un sistema grid-tie convencional no funciona como respaldo durante un corte de red", "Depende de la red para las horas sin generación", "La conexión e inyección deben cumplir los requisitos aplicables"],
    },
    "HIBRIDO": {
        "titulo": "HÍBRIDO",
        "desc": "Combina paneles, baterías y red eléctrica. Puede priorizar solar, almacenar excedentes y usar la red cuando sea necesario.",
        "ventajas": ["Respaldo con baterías", "Reduce dependencia de la red", "Permite gestionar distintas fuentes de energía"],
        "desventajas": ["Mayor costo y complejidad", "Requiere baterías", "Debe configurarse correctamente para el perfil de consumo"],
    },
}

def calcular_paneles(consumo_kwh_dia, hsp=4.5, panel_wp=620, rendimiento=0.80):
    consumo_wh = consumo_kwh_dia * 1000
    energia_por_panel = panel_wp * hsp * rendimiento
    n = max(1, math.ceil(consumo_wh / energia_por_panel))
    potencia = n * panel_wp
    generacion = potencia * hsp * rendimiento / 1000
    return n, potencia, generacion

def recomendar_kit(consumo_kwh_dia, sistema):
    kit = AUTOSOLAR_KITS[sistema]
    return kit

def _normalizar(texto):
    return re.sub(r"\s+", " ", texto.lower().strip())

def responder_local(pregunta, consumo_kwh_dia=None, sistema=None):
    q = _normalizar(pregunta)
    consumo = float(consumo_kwh_dia or st.session_state.get("eco_consumo_kwh", 6.16))
    sistema = sistema or st.session_state.get("tipo_sistema", "OFF-GRID")

    if any(x in q for x in ["off-grid", "off grid", "aislado"]):
        info = SYSTEM_INFO["OFF-GRID"]
        return f"**{info['titulo']}**\n\n{info['desc']}\n\n**Ventajas:** " + "; ".join(info["ventajas"]) + "\n\n**Desventajas:** " + "; ".join(info["desventajas"])

    if any(x in q for x in ["on-grid", "on grid", "red eléctrica", "conectado a la red"]):
        info = SYSTEM_INFO["ON-GRID"]
        return f"**{info['titulo']}**\n\n{info['desc']}\n\n**Ventajas:** " + "; ".join(info["ventajas"]) + "\n\n**Desventajas:** " + "; ".join(info["desventajas"])

    if any(x in q for x in ["híbrido", "hibrido", "batería y red"]):
        info = SYSTEM_INFO["HIBRIDO"]
        return f"**{info['titulo']}**\n\n{info['desc']}\n\n**Ventajas:** " + "; ".join(info["ventajas"]) + "\n\n**Desventajas:** " + "; ".join(info["desventajas"])

    if any(x in q for x in ["tipo de panel", "qué panel", "que panel", "panel bifacial", "n-type"]):
        return ("Como referencia de catálogo, AutoSolar utiliza paneles **bifaciales N-Type** de alta potencia en varios de sus kits. "
                "Para tu consumo, un panel de alrededor de **610–620 W** es una referencia práctica para el cálculo preliminar. "
                "La selección definitiva debe comprobar potencia, Voc, Vmpp, corriente, temperatura, área disponible y compatibilidad con el MPPT.")

    if any(x in q for x in ["panel", "cuántos paneles", "cuantos paneles", "cantidad de paneles"]):
        n, potencia, gen = calcular_paneles(consumo)
        return (f"Con un consumo de **{consumo:.2f} kWh/día**, usando como referencia **4,5 HSP**, "
                f"paneles de **620 W** y un rendimiento global de **80 %**, el cálculo da aproximadamente "
                f"**{n} paneles**, para una potencia FV de **{potencia/1000:.2f} kWp** y una generación estimada "
                f"de **{gen:.2f} kWh/día**. Es un dimensionamiento preliminar: la ubicación, sombras, orientación, "
                f"temperatura y cargas de arranque pueden cambiar el resultado.")

    if any(x in q for x in ["kit", "autosolar", "recomienda", "recomendación"]):
        kit = recomendar_kit(consumo, sistema)
        return (f"Para el sistema **{sistema}**, el catálogo consultado de AutoSolar tiene como referencia:\n\n"
                f"**{kit['nombre']}**\n\n{kit['detalle']}\n\n"
                f"Generación indicada por AutoSolar: **{kit['generacion_wh']/1000:.2f} kWh/día**. "
                f"Es una referencia de catálogo y debe verificarse con el diseño final del sitio.\n\n"
                f"[Ver kit en AutoSolar]({kit['url']})")

    if any(x in q for x in ["consumo", "197 kwh", "6.16", "6,16"]):
        return (f"Tu dato de referencia es **197 kWh/mes**, equivalente a unos **6,16 kWh/día**. "
                f"Puedes usar ese valor como entrada inicial y luego reemplazarlo por el consumo real de tu factura.")

    if any(x in q for x in ["mejor sistema", "cuál es mejor", "cual es mejor"]):
        return ("No hay un sistema universalmente mejor. **OFF-GRID** se usa cuando se busca independencia de la red; "
                "**ON-GRID** cuando se busca autoconsumo conectado a la red sin banco de baterías; **HÍBRIDO** cuando "
                "se quiere combinar red, solar y almacenamiento. La elección depende del acceso a red, cortes, consumo "
                "nocturno, presupuesto y necesidad de respaldo.")

    if any(x in q for x in ["hola", "buenas", "hey"]):
        return ("Hola. Soy **VivaBot Solar**, asistente de energía renovable. Puedo ayudarte con paneles, consumo, "
                "OFF-GRID, ON-GRID, HÍBRIDO y selección de kits del catálogo de AutoSolar.")

    return ("Puedo ayudarte con: **cálculo de paneles**, tipo de panel, explicación de **OFF-GRID / ON-GRID / HÍBRIDO**, "
            "selección de un kit de AutoSolar, consumo mensual o diario y conceptos básicos de energía solar.")

def _ai_config():
    """Lee la IA desde Streamlit secrets o variables de entorno."""
    try:
        ai = dict(st.secrets.get("ai", {}))
    except Exception:
        ai = {}
    key = ai.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
    model = ai.get("model") or os.environ.get("OPENAI_MODEL", "gpt-5-mini")
    return str(key).strip(), str(model).strip()

def responder(pregunta, consumo_kwh_dia=None, sistema=None):
    # VivaBot usa IA real cuando el administrador configura la clave una sola vez.
    api_key, model = _ai_config()
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            consumo = float(consumo_kwh_dia or st.session_state.get("eco_consumo_kwh", 6.16))
            sistema = sistema or st.session_state.get("tipo_sistema", "OFF-GRID")
            prompt = f"""Eres VivaBot Solar, un asistente de inteligencia artificial especializado en energía renovable, energía solar fotovoltaica, instalaciones eléctricas y eficiencia energética.

Debes responder las preguntas del usuario de forma útil, clara y completa, aunque la pregunta no sea exactamente sobre un panel solar. Si es una pregunta técnica, explica el razonamiento y, cuando corresponda, muestra fórmulas y unidades. Si faltan datos, indícalos y ofrece una estimación razonable claramente marcada como estimación. Nunca inventes normas, precios, enlaces ni especificaciones. Para temas de seguridad eléctrica, advierte cuando se requiera personal calificado.

Contexto del usuario:
- Consumo de referencia: {consumo:.2f} kWh/día (aprox. 197 kWh/mes si se usa 6,16 kWh/día).
- Sistema seleccionado: {sistema}.

Catálogo AutoSolar disponible en la aplicación:
{AUTOSOLAR_KITS}

Cuando el usuario pregunte por estos kits, utiliza los datos anteriores y enlaza la URL correspondiente. No afirmes que un kit es adecuado de forma definitiva sin verificar las condiciones de instalación.

Pregunta del usuario:
{pregunta}"""
            r = client.responses.create(model=model, input=prompt)
            text = getattr(r, "output_text", None)
            if text:
                return text
        except Exception as exc:
            # No mostramos credenciales ni detalles internos al usuario.
            st.session_state["eco_ai_error"] = str(exc)[:240]
    return responder_local(pregunta, consumo_kwh_dia, sistema)

def mostrar_chatbot():
    st.markdown("""
    <div class="hero-header">
      <div class="hero-title">🤖 VivaBot Solar</div>
      <div class="hero-sub">ASISTENTE DE ENERGÍA RENOVABLE · CALCULADORA SOLAR</div>
    </div>
    """, unsafe_allow_html=True)

    st.info("VivaBot Solar es la IA de ENERGÍA VIVA. Está disponible para todos los usuarios autenticados, incluidos los administradores. Puede responder preguntas abiertas sobre energía, electricidad, eficiencia y sistemas solares; para respuestas de IA avanzada se usa la configuración del servicio de IA del administrador.")

    c1, c2 = st.columns(2)
    with c1:
        consumo = st.number_input("Consumo diario (kWh/día)", min_value=0.1, value=float(st.session_state.get("eco_consumo_kwh", 6.16)), step=0.1, key="eco_consumo_input")
    with c2:
        sistema = st.selectbox("Sistema", ["OFF-GRID", "ON-GRID", "HIBRIDO"], index=["OFF-GRID","ON-GRID","HIBRIDO"].index(st.session_state.get("tipo_sistema","OFF-GRID")), key="eco_sistema_input")
    st.session_state["eco_consumo_kwh"] = consumo

    if "eco_messages" not in st.session_state:
        st.session_state["eco_messages"] = [{"role":"assistant","content":"Hola, soy VivaBot Solar. Pregúntame cuántos paneles necesitas, qué sistema te conviene técnicamente o qué kit corresponde al sistema seleccionado."}]

    for m in st.session_state["eco_messages"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    pregunta = st.chat_input("Pregúntame lo que necesites sobre energía, electricidad o energía solar...")
    if pregunta:
        st.session_state["eco_messages"].append({"role":"user","content":pregunta})
        respuesta = responder(pregunta, consumo, sistema)
        st.session_state["eco_messages"].append({"role":"assistant","content":respuesta})
        st.rerun()
