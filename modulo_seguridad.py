# modulo_seguridad.py — Calculadora Solar · Módulo de Seguridad y Control de Acceso
# ═══════════════════════════════════════════════════════════════════════════════
"""
Gestión completa de usuarios, roles y permisos para Calculadora Solar.

Roles disponibles:
  • superadmin  — acceso total + gestión de usuarios
  • admin       — acceso total a proyectos y módulos
  • ingeniero   — dimensionamiento, simulador y planos
  • visualizador— solo lectura (sin guardar ni exportar)

Tablas creadas:
  usuarios  — id, username, nombre_completo, email, password_hash, rol, activo, creado
  sesiones  — id, usuario_id, token, creado, expira
  auditoria — id, usuario_id, accion, detalle, ip, fecha
"""

import streamlit as st
import sqlite3
import hashlib
import secrets
import smtplib
import ssl
from email.message import EmailMessage
import os
import pathlib
import base64
import tempfile
import re
import pandas as pd
from datetime import datetime, timedelta

# ─── Constantes de roles y permisos ──────────────────────────────────────────
ROLES = {
    "superadmin": {
        "label":   "Super Administrador",
        "color":   "#FF5252",
        "icon":    "👑",
        "permisos": [
            "ver_proyectos", "crear_proyectos", "editar_proyectos", "eliminar_proyectos",
            "dimensionamiento", "simulador", "planos", "presupuesto",
            "exportar_pdf", "exportar_excel",
            "ver_usuarios", "crear_usuarios", "editar_usuarios", "eliminar_usuarios",
            "ver_auditoria", "gestion_sistema",
        ],
    },
    "admin": {
        "label":   "Administrador",
        "color":   "#FF6B35",
        "icon":    "🔧",
        "permisos": [
            "ver_proyectos", "crear_proyectos", "editar_proyectos", "eliminar_proyectos",
            "dimensionamiento", "simulador", "planos", "presupuesto",
            "exportar_pdf", "exportar_excel",
            "ver_usuarios", "crear_usuarios", "editar_usuarios",
            "ver_auditoria",
        ],
    },
    "ingeniero": {
        "label":   "Ingeniero",
        "color":   "#00BCD4",
        "icon":    "⚡",
        "permisos": [
            "ver_proyectos", "crear_proyectos", "editar_proyectos",
            "dimensionamiento", "simulador", "planos", "presupuesto",
            "exportar_pdf", "exportar_excel",
        ],
    },
    "visualizador": {
        "label":   "Visualizador",
        "color":   "#8A9BBD",
        "icon":    "👁",
        "permisos": [
            "ver_proyectos", "dimensionamiento",
        ],
    },
}

PERMISOS_LABELS = {
    "ver_proyectos":      "Ver proyectos",
    "crear_proyectos":    "Crear proyectos",
    "editar_proyectos":   "Editar proyectos",
    "eliminar_proyectos": "Eliminar proyectos",
    "dimensionamiento":   "Dimensionamiento",
    "simulador":          "Simulador",
    "planos":             "Ver planos",
    "presupuesto":        "Presupuesto",
    "exportar_pdf":       "Exportar PDF",
    "exportar_excel":     "Exportar Excel",
    "ver_usuarios":       "Ver usuarios",
    "crear_usuarios":     "Crear usuarios",
    "editar_usuarios":    "Editar usuarios",
    "eliminar_usuarios":  "Eliminar usuarios",
    "ver_auditoria":      "Ver auditoría",
    "gestion_sistema":    "Gestión del sistema",
}

# ─── DB path ─────────────────────────────────────────────────────────────────
def _db_path() -> str:
    env = os.environ.get("SOLARCALC_DB_PATH")
    if env: return env
    script_dir = pathlib.Path(__file__).parent.resolve()
    try:
        t = script_dir / ".wt"; t.touch(); t.unlink()
        return str(script_dir / "solar_calc.db")
    except Exception:
        return str(pathlib.Path(tempfile.gettempdir()) / "solar_calc.db")

DB_PATH = _db_path()

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def _secret_password(key: str, default: str = "") -> str:
    try:
        return str(st.secrets.get("auth", {}).get(key, default))
    except Exception:
        return default


# ═══════════════════════════════════════════════════════════════════════════════
# INICIALIZACIÓN DE TABLAS
# ═══════════════════════════════════════════════════════════════════════════════
def init_seguridad_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            username         TEXT    NOT NULL UNIQUE,
            nombre_completo  TEXT    NOT NULL,
            email            TEXT    NOT NULL UNIQUE,
            password_hash    TEXT    NOT NULL,
            rol              TEXT    NOT NULL DEFAULT 'visualizador',
            activo           INTEGER NOT NULL DEFAULT 1,
            creado           TEXT    DEFAULT (datetime('now')),
            ultimo_acceso    TEXT,
            actualizado      TEXT,
            creado_por       INTEGER
        )
    """)

    try:
        c.execute("ALTER TABLE usuarios ADD COLUMN actualizado TEXT")
    except sqlite3.OperationalError:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS sesiones (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id  INTEGER NOT NULL,
            token       TEXT    NOT NULL UNIQUE,
            creado      TEXT    DEFAULT (datetime('now')),
            expira      TEXT    NOT NULL,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS auditoria (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id  INTEGER,
            username    TEXT,
            accion      TEXT    NOT NULL,
            detalle     TEXT,
            modulo      TEXT,
            fecha       TEXT    DEFAULT (datetime('now'))
        )
    """)

    # Crear cuentas iniciales si la BD está vacía. En SQLite solo se guardan hashes.
    existing = c.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    if existing == 0:
        cuentas = [
            ("admin", "Esteban Zarate", "zarateyesesteban2009@gmail.com", "admin_password", "Admin2026!", "superadmin"),
            ("prueba", "Usuario Prueba", "zarateyesesteban@gmail.com", "prueba_password", "Prueba2026!", "visualizador"),
            ("usuario1", "Usuario 1", "yoestebanzarate1004@gmail.com", "usuario1_password", "Usuario12026!", "visualizador"),
            ("usuario2", "Usuario 2", "zarateyesesteban11@gmail.com", "usuario2_password", "Usuario22026!", "visualizador"),
            ("usuario3", "Usuario 3", "usuario3@calculadorasolar.com", "usuario3_password", "Usuario32026!", "visualizador"),
            ("Jabes", "Jabes Vargas", "vargas4567girardot@gmail.com", "Jabes_password", "12345678J", "ingeniero"),
        ]
        for username, nombre, email, key, default_pwd, rol in cuentas:
            c.execute("INSERT INTO usuarios(username,nombre_completo,email,password_hash,rol) VALUES(?,?,?,?,?)",
                      (username, nombre, email, _hash_password(_secret_password(key, default_pwd)), rol))

    # Asegurar que el usuario Jabes exista también cuando la BD ya tenía cuentas.
    jabes = c.execute("SELECT 1 FROM usuarios WHERE lower(username)=lower(?) OR lower(email)=lower(?) LIMIT 1",
                      ("Jabes", "vargas4567girardot@gmail.com")).fetchone()
    if not jabes:
        c.execute(
            "INSERT INTO usuarios(username,nombre_completo,email,password_hash,rol,activo,creado,actualizado) "
            "VALUES(?,?,?,?,?,1,datetime('now'),datetime('now'))",
            ("Jabes", "Jabes Vargas", "vargas4567girardot@gmail.com",
             _hash_password(_secret_password("Jabes_password", "12345678J")), "ingeniero"))

    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS DE SEGURIDAD
# ═══════════════════════════════════════════════════════════════════════════════
def _hash_password(password: str) -> str:
    """SHA-256 con sal fija de la app."""
    salt = "SolarCalcPro_2024_#SEC"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

def _generar_token() -> str:
    return secrets.token_hex(32)

def _validar_email(email: str) -> bool:
    return bool(re.match(r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$", email))

def _validar_password(pwd: str) -> tuple:
    if len(pwd) < 8:
        return False, "Mínimo 8 caracteres"
    if not re.search(r"[A-Z]", pwd):
        return False, "Debe tener al menos una mayúscula"
    if not re.search(r"[0-9]", pwd):
        return False, "Debe tener al menos un número"
    return True, "OK"


def _smtp_config():
    """Lee el servicio emisor desde Streamlit secrets o variables de entorno.

    El correo de cada usuario se usa siempre como DESTINO; SMTP solo define
    la cuenta técnica que envía el código.
    """
    cfg = {}
    try:
        cfg = dict(st.secrets.get("smtp", {}))
    except Exception:
        cfg = {}
    return {
        "host": cfg.get("host") or os.environ.get("SMTP_HOST", ""),
        "port": int(cfg.get("port") or os.environ.get("SMTP_PORT", "587")),
        "user": cfg.get("user") or os.environ.get("SMTP_USER", ""),
        "password": cfg.get("password") or os.environ.get("SMTP_PASSWORD", ""),
        "from": cfg.get("from") or os.environ.get("SMTP_FROM", cfg.get("user") or os.environ.get("SMTP_USER", "")),
        "use_tls": str(cfg.get("use_tls", os.environ.get("SMTP_USE_TLS", "true"))).lower() not in ("0","false","no")
    }

def _enviar_codigo_recuperacion(email_destino: str, codigo: str) -> tuple:
    cfg = _smtp_config()
    if not all([cfg["host"], cfg["port"], cfg["user"], cfg["password"], cfg["from"]]):
        return False, "El correo de recuperación aún no está configurado. El administrador debe configurar SMTP en los secretos de Streamlit."
    try:
        msg = EmailMessage()
        msg["Subject"] = "Código de recuperación · Calculadora Solar"
        msg["From"] = cfg["from"]
        msg["To"] = email_destino
        msg.set_content(
            f"Tu código de verificación para recuperar la contraseña es: {codigo}\n\n"
            "El código vence en 10 minutos. Si no solicitaste este cambio, ignora este mensaje."
        )
        context = ssl.create_default_context()
        if cfg["use_tls"]:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as server:
                server.starttls(context=context)
                server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context, timeout=20) as server:
                server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
        return True, "Código enviado correctamente."
    except Exception as e:
        return False, f"No fue posible enviar el correo de recuperación: {e}"

def _solicitar_codigo(email: str):
    if not _validar_email(email):
        return False, "Escribe un correo electrónico válido."
    conn = get_conn()
    row = conn.execute("SELECT id, username, nombre_completo, activo FROM usuarios WHERE lower(email)=lower(?) LIMIT 1", (email.strip(),)).fetchone()
    conn.close()
    if not row:
        return False, "No encontramos una cuenta con ese correo."
    if not row[3]:
        return False, "La cuenta está desactivada. Contacta al administrador."
    codigo = f"{secrets.randbelow(1000000):06d}"
    st.session_state["reset_email"] = email.strip()
    st.session_state["reset_code_hash"] = hashlib.sha256(codigo.encode()).hexdigest()
    st.session_state["reset_code_exp"] = (datetime.now().timestamp() + 600)
    st.session_state["reset_user_id"] = row[0]
    return _enviar_codigo_recuperacion(email.strip(), codigo)

def _verificar_y_cambiar_password(email: str, codigo: str, nueva: str, confirmacion: str):
    if st.session_state.get("reset_email","").lower() != email.strip().lower():
        return False, "Solicita primero un código para este correo."
    if datetime.now().timestamp() > float(st.session_state.get("reset_code_exp", 0)):
        return False, "El código ya venció. Solicita uno nuevo."
    esperado = st.session_state.get("reset_code_hash","")
    recibido = hashlib.sha256(codigo.strip().encode()).hexdigest()
    if not esperado or not secrets.compare_digest(esperado, recibido):
        return False, "Código de verificación incorrecto."
    ok, msg = _validar_password(nueva)
    if not ok:
        return False, msg
    if nueva != confirmacion:
        return False, "Las contraseñas no coinciden."
    conn = get_conn()
    conn.execute("UPDATE usuarios SET password_hash=?, actualizado=datetime('now') WHERE id=?",
                 (_hash_password(nueva), st.session_state.get("reset_user_id")))
    conn.commit()
    conn.close()
    st.session_state.pop("reset_code_hash", None)
    st.session_state.pop("reset_code_exp", None)
    st.session_state.pop("reset_user_id", None)
    st.session_state["login_mode"] = "login"
    return True, "Contraseña actualizada. Ya puedes iniciar sesión."

def mostrar_recuperacion_password():
    st.markdown("<div class='auth-form'><h2>Recuperar contraseña</h2><p>Te enviaremos un código de verificación al correo registrado.</p></div>", unsafe_allow_html=True)
    email = st.text_input("Correo electrónico", key="reset_email_input", placeholder="Ej: usuario@gmail.com")
    if st.button("ENVIAR CÓDIGO", use_container_width=True, type="primary", key="reset_send"):
        ok, msg = _solicitar_codigo(email)
        if ok:
            st.success(msg)
            st.session_state["reset_step"] = 2
        else:
            st.error(msg)
    if st.session_state.get("reset_step") == 2:
        codigo = st.text_input("Código de verificación", max_chars=6, key="reset_code_input")
        nueva = st.text_input("Nueva contraseña", type="password", key="reset_new")
        confirm = st.text_input("Confirmar nueva contraseña", type="password", key="reset_confirm")
        if st.button("CAMBIAR CONTRASEÑA", use_container_width=True, type="primary", key="reset_change"):
            ok, msg = _verificar_y_cambiar_password(email, codigo, nueva, confirm)
            if ok:
                st.success(msg)
                st.session_state["reset_step"] = 0
                st.rerun()
            else:
                st.error(msg)
    st.markdown("<div class='small-note'>El código es válido durante 10 minutos.</div>", unsafe_allow_html=True)

def registrar_auditoria(usuario_id: int, username: str, accion: str,
                         detalle: str = "", modulo: str = ""):
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO auditoria(usuario_id,username,accion,detalle,modulo) VALUES(?,?,?,?,?)",
            (usuario_id, username, accion, detalle, modulo))
        conn.commit()
        conn.close()
    except Exception:
        pass

def usuario_activo() -> object:
    """Retorna el dict del usuario en sesión o None."""
    return st.session_state.get("usuario_sesion")

def _rol_actual_desde_bd(usuario: dict):
    """Lee el rol directamente de SQLite para evitar una sesión desactualizada."""
    if not usuario or not usuario.get("id"):
        return None
    try:
        conn = get_conn()
        row = conn.execute("SELECT rol, activo FROM usuarios WHERE id=?", (usuario["id"],)).fetchone()
        conn.close()
        if not row or not row[1]:
            return None
        usuario["rol"] = row[0]
        return row[0]
    except Exception:
        return usuario.get("rol", "visualizador")

def tiene_permiso(permiso: str) -> bool:
    """Verifica el permiso usando el rol vigente en la base de datos."""
    usuario = usuario_activo()
    rol = _rol_actual_desde_bd(usuario) if usuario else None
    return bool(rol and permiso in ROLES.get(rol, {}).get("permisos", []))

def es_superadmin() -> bool:
    u = usuario_activo()
    return bool(u and _rol_actual_desde_bd(u) == "superadmin")


# ═══════════════════════════════════════════════════════════════════════════════
# AUTENTICACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
def _login(username: str, password: str) -> tuple:
    """Intenta autenticar. Retorna (éxito, mensaje)."""
    conn = get_conn()
    # El acceso se realiza exclusivamente con el NOMBRE DE USUARIO.
    # El correo se conserva como dato de contacto/perfil, pero no es un identificador
    # válido para iniciar sesión.
    login_username = username.strip().lower()
    row = conn.execute(
        "SELECT id, username, nombre_completo, email, password_hash, rol, activo "
        "FROM usuarios WHERE lower(username)=?",
        (login_username,)).fetchone()
    conn.close()

    if not row:
        return False, "Usuario no encontrado"
    if not row[6]:
        return False, "Cuenta desactivada. Contacta al administrador"
    if row[4] != _hash_password(password):
        return False, "Contraseña incorrecta"

    # Sesión exitosa
    token = _generar_token()
    expira = (datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn()
    conn.execute("INSERT INTO sesiones(usuario_id,token,expira) VALUES(?,?,?)",
                 (row[0], token, expira))
    conn.execute("UPDATE usuarios SET ultimo_acceso=? WHERE id=?",
                 (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row[0]))
    conn.commit()
    conn.close()

    st.session_state["usuario_sesion"] = {
        "id": row[0], "username": row[1], "nombre": row[2],
        "email": row[3], "rol": row[5], "token": token,
    }
    registrar_auditoria(row[0], row[1], "LOGIN", "Inicio de sesión exitoso", "seguridad")
    return True, "OK"

def _iniciar_sesion_como_usuario(usuario_id: int) -> tuple:
    """Permite al Super Administrador entrar temporalmente como otro usuario.
    La sesión original del Super Admin se conserva para poder regresar.
    """
    if not es_superadmin():
        return False, "Solo el Super Administrador puede iniciar sesión como otro usuario."
    conn = get_conn()
    row = conn.execute(
        "SELECT id, username, nombre_completo, email, rol, activo FROM usuarios WHERE id=?",
        (int(usuario_id),)).fetchone()
    conn.close()
    if not row:
        return False, "Usuario no encontrado."
    if not row[5]:
        return False, "La cuenta está desactivada."

    admin = dict(usuario_activo())
    st.session_state["usuario_admin_origen"] = admin
    token = _generar_token()
    expira = (datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn()
    conn.execute("INSERT INTO sesiones(usuario_id,token,expira) VALUES(?,?,?)",
                 (row[0], token, expira))
    conn.execute("UPDATE usuarios SET ultimo_acceso=? WHERE id=?",
                 (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row[0]))
    conn.commit(); conn.close()
    st.session_state["usuario_sesion"] = {
        "id": row[0], "username": row[1], "nombre": row[2],
        "email": row[3], "rol": row[4], "token": token,
    }
    st.session_state["modo_impersonacion"] = True
    registrar_auditoria(admin["id"], admin["username"], "INICIO_SESION_COMO",
                        f"Entró temporalmente como @{row[1]}", "usuarios")
    registrar_auditoria(row[0], row[1], "INICIO_SESION_ADMIN",
                        f"Sesión iniciada temporalmente por @{admin['username']}", "seguridad")
    return True, "Sesión temporal iniciada."

def _volver_a_superadmin():
    """Regresa al Super Administrador después de una sesión temporal."""
    admin = st.session_state.get("usuario_admin_origen")
    actual = usuario_activo()
    if actual:
        registrar_auditoria(actual["id"], actual["username"], "FIN_SESION_ADMIN",
                            "Fin de sesión temporal", "seguridad")
        try:
            conn = get_conn(); conn.execute("DELETE FROM sesiones WHERE token=?", (actual.get("token", ""),)); conn.commit(); conn.close()
        except Exception:
            pass
    if admin:
        st.session_state["usuario_sesion"] = admin
    st.session_state.pop("usuario_admin_origen", None)
    st.session_state.pop("modo_impersonacion", None)
    st.session_state["modulo_activo"] = "usuarios"

def _logout():
    u = usuario_activo()
    if u:
        registrar_auditoria(u["id"], u["username"], "LOGOUT", "Cierre de sesión", "seguridad")
        conn = get_conn()
        conn.execute("DELETE FROM sesiones WHERE token=?", (u.get("token",""),))
        conn.commit()
        conn.close()
    for k in ["usuario_sesion", "tipo_sistema", "modulo_activo"]:
        st.session_state.pop(k, None)


# ═══════════════════════════════════════════════════════════════════════════════
# PANTALLA DE LOGIN
# ═══════════════════════════════════════════════════════════════════════════════
def _registrar_usuario_publico(nombre: str, username: str, email: str, password: str) -> tuple:
    """Crea una cuenta pública y deja todo listo para iniciar sesión con username."""
    nombre = (nombre or "").strip()
    username = (username or "").strip().lower()
    email = (email or "").strip().lower()

    if not nombre:
        return False, "El nombre completo es obligatorio"
    if not re.fullmatch(r"[a-z0-9._-]{3,30}", username):
        return False, "El nombre de usuario debe tener 3-30 caracteres y solo usar letras, números, punto, guion o guion bajo"
    if not _validar_email(email):
        return False, "Escribe un correo electrónico válido"
    ok, msg = _validar_password(password)
    if not ok:
        return False, f"Contraseña no válida: {msg}"

    conn = get_conn()
    try:
        # Comprobación previa: mensajes claros en lugar de depender del error de SQLite.
        if conn.execute("SELECT 1 FROM usuarios WHERE lower(username)=? LIMIT 1", (username,)).fetchone():
            return False, "Ese nombre de usuario ya está registrado. Elige otro."
        if conn.execute("SELECT 1 FROM usuarios WHERE lower(email)=? LIMIT 1", (email,)).fetchone():
            return False, "Ese correo electrónico ya está registrado. Usa otro correo."

        conn.execute(
            "INSERT INTO usuarios(username,nombre_completo,email,password_hash,rol,activo,creado,actualizado) "
            "VALUES(?,?,?,?,?,?,datetime('now'),datetime('now'))",
            (username, nombre, email, _hash_password(password), "visualizador", 1))
        conn.commit()
        return True, "Cuenta creada correctamente. Ya puedes iniciar sesión con tu nombre de usuario."
    except sqlite3.IntegrityError as e:
        conn.rollback()
        msg = str(e).lower()
        if "username" in msg or "usuarios.username" in msg:
            return False, "Ese nombre de usuario ya está registrado. Elige otro."
        if "email" in msg or "usuarios.email" in msg:
            return False, "Ese correo electrónico ya está registrado. Usa otro correo."
        return False, "No fue posible crear la cuenta. Revisa los datos e inténtalo nuevamente."
    except Exception as e:
        conn.rollback()
        return False, f"Error al crear la cuenta: {e}"
    finally:
        conn.close()

def mostrar_login():
    """Pantalla de acceso/registro con diseño dividido y marca de agua renovable."""
    if "login_mode" not in st.session_state:
        st.session_state["login_mode"] = "login"
    if "reset_step" not in st.session_state:
        st.session_state["reset_step"] = 0

    # Logo usado como marca de agua: no se muestra arriba del formulario.
    watermark_path = pathlib.Path(__file__).parent / "solar_calculadora_marca_agua.png"
    watermark_uri = ""
    if watermark_path.exists():
        watermark_uri = "data:image/png;base64," + base64.b64encode(watermark_path.read_bytes()).decode("ascii")

    st.markdown(f"""<style>
    /* ===== LOGIN / REGISTRO — IDENTIDAD CALCULADORA SOLAR ===== */
    [data-testid="stMainBlockContainer"] {{
        max-width: 1220px !important;
        margin: 0 auto !important;
        padding: 1.1rem 1.5rem 2rem !important;
    }}
    [data-testid="stAppViewContainer"] > .main,
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(135deg,#EEF8F3 0%,#E2F3EA 52%,#F8FCFA 100%) !important;
    }}
    .login-page {{
        width:100%; max-width:1120px; margin:0 auto; position:relative;
        min-height:720px; isolation:isolate;
    }}
    .login-page:before {{
        content:""; position:fixed; z-index:-1; pointer-events:none;
        width:520px; height:520px; right:-35px; bottom:-55px;
        background-image:url('{watermark_uri}'); background-repeat:no-repeat;
        background-size:contain; background-position:center; opacity:.16;
        filter:drop-shadow(0 12px 20px rgba(5,75,55,.05));
    }}
    .login-page:after {{
        content:""; position:fixed; z-index:-2; pointer-events:none;
        width:100%; height:100%; inset:0;
        background:radial-gradient(circle at 12% 12%,rgba(135,207,50,.10),transparent 28%),
                   radial-gradient(circle at 92% 88%,rgba(7,127,91,.10),transparent 32%);
    }}
    .auth-card {{ width:100%; position:relative; margin-top:1.2rem; }}
    .auth-card [data-testid="stHorizontalBlock"] {{
        gap:1rem !important; align-items:stretch !important;
    }}
    .auth-card [data-testid="stColumn"] {{ padding:0 !important; }}
    .auth-card [data-testid="stVerticalBlockBorderWrapper"] {{
        height:100% !important; min-height:500px !important;
        border:1px solid #A7D5BF !important;
        border-radius:22px !important; overflow:hidden !important;
        box-shadow:0 16px 38px rgba(0,90,63,.12) !important;
        background:#FFFFFF !important;
    }}
    .auth-card [data-testid="stVerticalBlockBorderWrapper"] > div {{
        padding:0 !important;
    }}
    .auth-card [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {{
        gap:.25rem !important;
    }}
    .auth-form {{
        padding:1.7rem 1.8rem .55rem !important;
        background:#FFFFFF;
    }}
    .auth-form h2 {{
        margin:0 0 .25rem; color:#063B2D; font-size:1.65rem;
        font-weight:800; letter-spacing:-.4px;
    }}
    .auth-form p {{ color:#456C5C; font-size:.78rem; margin:0 0 .7rem; }}
    .auth-form .small-note {{ text-align:center; color:#557668; font-size:.68rem; margin:.55rem 0 .35rem; }}
    .auth-side {{
        min-height:500px; height:100%; padding:2.25rem 2.25rem;
        display:flex; flex-direction:column; justify-content:center;
        color:#fff; position:relative; overflow:hidden;
        background:linear-gradient(145deg,#063B2D 0%,#087F5B 50%,#18A957 100%);
    }}
    .auth-side:before {{
        content:""; position:absolute; width:290px; height:290px; border-radius:50%;
        right:-105px; top:-100px; background:rgba(139,207,50,.25);
    }}
    .auth-side:after {{
        content:"☀"; position:absolute; right:28px; bottom:12px;
        color:rgba(244,196,0,.48); font-size:74px;
    }}
    .auth-side > * {{ position:relative; z-index:2; }}
    .auth-side h2 {{ font-size:1.9rem; line-height:1.08; margin:0 0 .75rem; color:#fff; }}
    .auth-side p {{ font-size:.82rem; line-height:1.6; color:#F2FFF8; max-width:390px; margin:0 0 1rem; }}
    .green-badge {{
        display:inline-block; border:1px solid rgba(215,255,221,.55); border-radius:20px;
        padding:.35rem .75rem; color:#FFF3A8; font-size:.65rem; letter-spacing:.4px;
        background:rgba(255,255,255,.07);
    }}
    .benefits {{ display:flex; gap:.5rem; margin-top:1.2rem; flex-wrap:wrap; }}
    .benefit {{ font-size:.66rem; color:#F4FFF9; padding:.45rem .55rem; border-radius:12px; background:rgba(255,255,255,.08); }}
    .auth-card label, .auth-card [data-testid="stWidgetLabel"] p {{
        color:#145443 !important; font-size:.72rem !important; font-weight:700 !important;
    }}
    .auth-card input {{
        background:#FFFFFF !important; color:#123F31 !important;
        border:1px solid #9ACDB1 !important; border-radius:9px !important;
    }}
    .auth-card input::placeholder {{ color:#6B887C !important; opacity:1 !important; }}
    .auth-card [data-testid="stTextInput"] {{ margin-bottom:.12rem; }}
    .auth-card .stButton button {{
        background:linear-gradient(90deg,#F4C400,#8BCF32) !important;
        color:#173A2D !important; border:0 !important; border-radius:10px !important;
        font-weight:800 !important; min-height:42px !important;
        box-shadow:0 7px 18px rgba(139,170,24,.25) !important;
    }}
    .auth-card .stButton button:hover {{ background:linear-gradient(90deg,#D9AE00,#69B52B) !important; }}
    .switch-btn button {{
        background:#FFFFFF !important; color:#087F5B !important; border:1px solid #75BD9A !important;
        box-shadow:none !important; min-height:38px !important; font-weight:700 !important;
    }}
    .switch-btn button:hover {{ background:#EAF8F0 !important; }}
    .auth-footer {{ text-align:center; color:#68887B; font-size:.68rem; margin-top:1rem; }}
    @media (max-width: 760px) {{
        [data-testid="stMainBlockContainer"] {{ padding:.7rem .55rem 1rem !important; }}
        .login-page {{ min-height:auto; }}
        .login-page:before {{ width:330px; height:330px; right:-90px; bottom:-35px; opacity:.42; }}
        .auth-card [data-testid="stHorizontalBlock"] {{ flex-direction:column !important; }}
        .auth-card [data-testid="stVerticalBlockBorderWrapper"] {{ min-height:auto !important; }}
        .auth-side {{ min-height:310px; padding:1.6rem; }}
        .auth-form {{ padding:1.35rem 1.25rem .4rem !important; }}
    }}
    </style>""", unsafe_allow_html=True)

    st.markdown("<div class='login-page'>", unsafe_allow_html=True)
    mode = st.session_state.get("login_mode", "login")
    st.markdown("<div class='auth-card'>", unsafe_allow_html=True)
    left, right = st.columns(2, gap="small")

    if mode == "login":
        with left:
            with st.container(border=True):
                st.markdown("<div class='auth-form'><h2>Iniciar sesión</h2><p>Accede a tus proyectos de energía solar.</p></div>", unsafe_allow_html=True)
                username = st.text_input("Nombre de usuario", placeholder="Ej: usuario1", key="login_user", help="Usa el nombre de usuario registrado.")
                password = st.text_input("Contraseña", type="password", placeholder="••••••••", key="login_pass")
                if st.button("INGRESAR", use_container_width=True, type="primary", key="login_btn"):
                    if not username or not password:
                        st.error("Ingresa usuario y contraseña")
                    else:
                        ok, msg = _login(username, password)
                        if ok:
                            st.success("✓ Acceso concedido")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
                st.markdown("<div class='switch-btn' style='margin-top:.35rem;'>", unsafe_allow_html=True)
                if st.button("¿OLVIDASTE TU CONTRASEÑA?", use_container_width=True, key="forgot_password"):
                    st.session_state["login_mode"] = "reset"
                    st.session_state["reset_step"] = 0
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("<div class='auth-form'><div class='small-note'>¿No tienes una cuenta?</div>", unsafe_allow_html=True)
                st.markdown("<div class='switch-btn'>", unsafe_allow_html=True)
                if st.button("CREAR CUENTA", use_container_width=True, key="go_register"):
                    st.session_state["login_mode"] = "register"
                    st.rerun()
                st.markdown("</div></div>", unsafe_allow_html=True)
        with right:
            with st.container(border=True):
                st.markdown("""<div class='auth-side'>
                    <h2>¡Bienvenido de nuevo!</h2>
                    <p>Gestiona tus proyectos fotovoltaicos, cálculos, materiales, presupuestos y resultados de energía solar desde un solo lugar.</p>
                    <span class='green-badge'>☀ ENERGÍA LIMPIA · SOLUCIONES SOLARES</span>
                    <div class='benefits'><span class='benefit'>♻ Energía limpia</span><span class='benefit'>⚡ Ahorro eficiente</span><span class='benefit'>🌱 Un mejor futuro</span></div>
                </div>""", unsafe_allow_html=True)
    elif mode == "reset":
        with left:
            with st.container(border=True):
                mostrar_recuperacion_password()
                st.markdown("<div class='switch-btn'>", unsafe_allow_html=True)
                if st.button("VOLVER A INICIAR SESIÓN", use_container_width=True, key="back_login_reset"):
                    st.session_state["login_mode"] = "login"
                    st.session_state["reset_step"] = 0
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        with right:
            with st.container(border=True):
                st.markdown("""<div class='auth-side'>
                    <h2>Recuperación segura</h2>
                    <p>Usa el correo registrado para recibir un código temporal y crear una nueva contraseña.</p>
                    <span class='green-badge'>🔐 CÓDIGO DE VERIFICACIÓN</span>
                    <div class='benefits'><span class='benefit'>📧 Correo registrado</span><span class='benefit'>⏱ 10 minutos</span><span class='benefit'>🔒 Código temporal</span></div>
                </div>""", unsafe_allow_html=True)
    else:
        with left:
            with st.container(border=True):
                st.markdown("""<div class='auth-side'>
                    <h2>¡Hola, amigo!</h2>
                    <p>Crea tu cuenta y comienza a gestionar tus proyectos de energía solar de forma fácil y organizada.</p>
                    <span class='green-badge'>☀ TU CAMINO HACIA LA ENERGÍA SOLAR</span>
                    <div class='benefits'><span class='benefit'>♻ Energía limpia</span><span class='benefit'>⚡ Proyectos solares</span><span class='benefit'>🌱 Futuro sostenible</span></div>
                </div>""", unsafe_allow_html=True)
        with right:
            with st.container(border=True):
                st.markdown("<div class='auth-form'><h2>Crear cuenta</h2><p>Ingresa tus datos para comenzar.</p></div>", unsafe_allow_html=True)
                n = st.text_input("Nombre completo", placeholder="Ej: Juan Pérez", key="reg_nombre")
                un = st.text_input("Nombre de usuario", placeholder="Ej: juanperez", key="reg_usuario")
                em = st.text_input("Correo electrónico", placeholder="Ej: juan@gmail.com", key="reg_email")
                pw = st.text_input("Contraseña", type="password", placeholder="Mínimo 8 caracteres", key="reg_pwd")
                pw2 = st.text_input("Confirmar contraseña", type="password", placeholder="Repite tu contraseña", key="reg_pwd2")
                if st.button("REGISTRARSE", use_container_width=True, type="primary", key="reg_btn"):
                    if not all([n.strip(), un.strip(), em.strip(), pw, pw2]):
                        st.error("❌ Completa todos los campos obligatorios.")
                    elif pw != pw2:
                        st.error("❌ Las contraseñas no coinciden.")
                    else:
                        ok, msg = _registrar_usuario_publico(n, un, em, pw)
                        if ok:
                            login_ok, login_msg = _login(un, pw)
                            if login_ok:
                                st.success("✓ Cuenta creada e inicio de sesión correcto.")
                                st.rerun()
                            else:
                                st.success("✓ " + msg)
                        else:
                            st.error("❌ " + msg)
                st.markdown("<div class='auth-form'><div class='small-note'>¿Ya tienes una cuenta?</div>", unsafe_allow_html=True)
                st.markdown("<div class='switch-btn'>", unsafe_allow_html=True)
                if st.button("INICIAR SESIÓN", use_container_width=True, key="go_login"):
                    st.session_state["login_mode"] = "login"
                    st.rerun()
                st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='auth-footer'>Calculadora Solar · Acceso seguro · Contraseñas almacenadas como hash</div></div>", unsafe_allow_html=True)
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — INFO DE USUARIO ACTIVO
# ═══════════════════════════════════════════════════════════════════════════════
def mostrar_usuario_sidebar():
    """Renderiza el bloque de usuario en el sidebar."""
    u = usuario_activo()
    if not u:
        return
    rol_info = ROLES.get(u["rol"], ROLES["visualizador"])
    st.markdown(f"""
    <div style='background:#1A2235;border:1px solid #2A3A55;border-radius:10px;
     padding:0.7rem 0.9rem;margin-bottom:0.5rem;'>
        <div style='font-family:Rajdhani,sans-serif;font-size:0.95rem;
         color:#E8EDF5;font-weight:600;'>{rol_info["icon"]} {u["nombre"]}</div>
        <div style='font-size:0.7rem;color:#8A9BBD;margin-top:0.2rem;'>
            @{u["username"]}
        </div>
        <div style='margin-top:0.4rem;'>
            <span style='background:{rol_info["color"]}22;color:{rol_info["color"]};
             font-family:Rajdhani,sans-serif;font-weight:700;font-size:0.65rem;
             padding:2px 8px;border-radius:12px;letter-spacing:1px;border:1px solid {rol_info["color"]}44;'>
                {rol_info["label"].upper()}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("modo_impersonacion") and st.session_state.get("usuario_admin_origen"):
        admin = st.session_state["usuario_admin_origen"]
        st.warning(f"👑 Sesión temporal como @{u['username']}\n\nSuper Administrador: @{admin['username']}")
        if st.button("↩️ Volver al Super Administrador", use_container_width=True, key="btn_return_admin"):
            _volver_a_superadmin()
            st.rerun()

    if st.button("🚪 Cerrar sesión", use_container_width=True, key="btn_logout"):
        _logout()
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# MÓDULO DE GESTIÓN DE USUARIOS (solo admin/superadmin)
# ═══════════════════════════════════════════════════════════════════════════════
def mostrar_gestion_usuarios():
    """Panel completo de administración de usuarios."""
    u = usuario_activo()
    if not tiene_permiso("ver_usuarios"):
        st.error("🔒 No tienes permiso para acceder a esta sección.")
        return

    st.markdown("""
    <div class='hero-header'>
        <div class='hero-title'>🔐 GESTIÓN DE USUARIOS</div>
        <div class='hero-sub'>ADMINISTRACIÓN DE ACCESO · ROLES · PERMISOS</div>
    </div>
    """, unsafe_allow_html=True)

    tab_lista, tab_nuevo, tab_auditoria = st.tabs([
        "👥 Usuarios", "➕ Nuevo usuario", "📋 Actividad / Auditoría"
    ])

    # ── TAB: Lista de usuarios ────────────────────────────────────────────────
    with tab_lista:
        conn = get_conn()
        usuarios_df = pd.read_sql(
            "SELECT id, username, nombre_completo, email, rol, activo, creado, ultimo_acceso "
            "FROM usuarios ORDER BY creado DESC", conn)
        conn.close()

        st.markdown(f"""
        <div style='display:flex;gap:1rem;margin-bottom:1rem;flex-wrap:wrap;'>
            <div style='background:#1A2235;border-radius:8px;padding:0.6rem 1.2rem;text-align:center;'>
                <div style='font-family:Share Tech Mono;font-size:1.4rem;color:#FFB300;'>{len(usuarios_df)}</div>
                <div style='font-size:0.72rem;color:#8A9BBD;'>Usuarios totales</div>
            </div>
            <div style='background:#1A2235;border-radius:8px;padding:0.6rem 1.2rem;text-align:center;'>
                <div style='font-family:Share Tech Mono;font-size:1.4rem;color:#00E676;'>{usuarios_df["activo"].sum()}</div>
                <div style='font-size:0.72rem;color:#8A9BBD;'>Activos</div>
            </div>
            <div style='background:#1A2235;border-radius:8px;padding:0.6rem 1.2rem;text-align:center;'>
                <div style='font-family:Share Tech Mono;font-size:1.4rem;color:#FF5252;'>{(~usuarios_df["activo"].astype(bool)).sum()}</div>
                <div style='font-size:0.72rem;color:#8A9BBD;'>Inactivos</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── CAMBIO DE ROL: panel directo y exclusivo del Super Administrador ──
        # Se coloca fuera de cada expander para que el Super Admin pueda editar
        # el rol aunque el expander de un usuario esté cerrado.
        if es_superadmin():
            st.markdown("""
            <div style='background:#111A2D;border:1px solid #FFB300;border-radius:10px;padding:1rem;margin:0.5rem 0 1.2rem;'>
                <div style='color:#FFB300;font-weight:700;font-size:0.9rem;'>👑 CAMBIAR ROL DE USUARIO</div>
                <div style='color:#8A9BBD;font-size:0.72rem;margin-top:0.2rem;'>Solo el Super Administrador puede modificar los roles.</div>
            </div>
            """, unsafe_allow_html=True)
            candidatos = usuarios_df[usuarios_df["id"] != u["id"]].copy()
            if not candidatos.empty:
                opciones_usuario = {
                    int(r["id"]): f"@{r['username']} — {r['nombre_completo']} ({ROLES.get(r['rol'], ROLES['visualizador'])['label']})"
                    for _, r in candidatos.iterrows()
                }
                id_objetivo = st.selectbox(
                    "Usuario", list(opciones_usuario.keys()),
                    format_func=lambda x: opciones_usuario[x],
                    key="superadmin_usuario_objetivo")
                rol_actual_objetivo = str(candidatos.loc[candidatos["id"] == id_objetivo, "rol"].iloc[0])
                nuevo_rol_directo = st.selectbox(
                    "Nuevo rol", list(ROLES.keys()),
                    index=list(ROLES.keys()).index(rol_actual_objetivo) if rol_actual_objetivo in ROLES else 0,
                    format_func=lambda x: f"{ROLES[x]['icon']} {ROLES[x]['label']}",
                    key="superadmin_nuevo_rol")
                if st.button("💾 GUARDAR CAMBIO DE ROL", type="primary", use_container_width=True, key="superadmin_guardar_rol"):
                    conn = get_conn()
                    conn.execute(
                        "UPDATE usuarios SET rol=?, actualizado=? WHERE id=?",
                        (nuevo_rol_directo, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(id_objetivo)))
                    conn.commit()
                    conn.close()
                    fila = candidatos[candidatos["id"] == id_objetivo].iloc[0]
                    registrar_auditoria(
                        u["id"], u["username"], "CAMBIO_ROL",
                        f"Usuario #{int(id_objetivo)} @{fila['username']} → rol: {nuevo_rol_directo}",
                        "usuarios")
                    st.success(f"Rol actualizado correctamente: @{fila['username']} → {ROLES[nuevo_rol_directo]['label']}")
                    st.rerun()

        for _, row in usuarios_df.iterrows():
            rol_i  = ROLES.get(row["rol"], ROLES["visualizador"])
            activo = bool(row["activo"])
            with st.expander(
                f"{rol_i['icon']} {row['nombre_completo']} — @{row['username']} "
                f"{'✅' if activo else '🔴'}",
                expanded=False):

                col1, col2, col3 = st.columns([1.5, 1.5, 1])
                with col1:
                    st.markdown(f"""
                    <table style='font-size:0.82rem;width:100%;border-collapse:collapse;'>
                        <tr><td style='color:#8A9BBD;padding:0.25rem 0;'>ID</td>
                            <td style='font-family:Share Tech Mono;color:#FFD54F;'>#{row['id']}</td></tr>
                        <tr><td style='color:#8A9BBD;padding:0.25rem 0;'>Usuario</td>
                            <td style='color:#E8EDF5;'>@{row['username']}</td></tr>
                        <tr><td style='color:#8A9BBD;padding:0.25rem 0;'>Correo</td>
                            <td style='color:#E8EDF5;'>{row['email']}</td></tr>
                        <tr><td style='color:#8A9BBD;padding:0.25rem 0;'>Rol</td>
                            <td style='color:{rol_i["color"]};font-weight:700;'>{rol_i["label"]}</td></tr>
                        <tr><td style='color:#8A9BBD;padding:0.25rem 0;'>Creado</td>
                            <td style='font-family:Share Tech Mono;color:#8A9BBD;'>{row['creado'][:16]}</td></tr>
                        <tr><td style='color:#8A9BBD;padding:0.25rem 0;'>Último acceso</td>
                            <td style='font-family:Share Tech Mono;color:#8A9BBD;'>{str(row['ultimo_acceso'] or '—')[:16]}</td></tr>
                    </table>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown("<div style='color:#8A9BBD;font-size:0.75rem;margin-bottom:0.4rem;'>PERMISOS DEL ROL</div>", unsafe_allow_html=True)
                    perms = ROLES.get(row["rol"], {}).get("permisos", [])
                    for p in PERMISOS_LABELS:
                        tiene = p in perms
                        st.markdown(
                            f"<div style='font-size:0.75rem;color:{'#00E676' if tiene else '#2A3A55'};'>"
                            f"{'✓' if tiene else '✗'} {PERMISOS_LABELS[p]}</div>",
                            unsafe_allow_html=True)

                with col3:
                    if tiene_permiso("editar_usuarios") and row["id"] != u["id"]:
                        st.markdown("<div style='color:#8A9BBD;font-size:0.75rem;margin-bottom:0.4rem;'>ACCIONES</div>", unsafe_allow_html=True)

                        # El cambio de rol es una operación exclusiva del Super Administrador.
                        # Los administradores pueden gestionar otras acciones de usuario, pero
                        # no pueden elevar, reducir ni modificar el rol de una cuenta.
                        if es_superadmin():
                            st.markdown(
                                "<div style='color:#FFB300;font-size:0.72rem;margin-bottom:0.3rem;'>👑 SOLO SUPER ADMINISTRADOR · CAMBIAR ROL</div>",
                                unsafe_allow_html=True)
                            nuevo_rol = st.selectbox(
                                "Cambiar rol",
                                options=list(ROLES.keys()),
                                format_func=lambda x: f"{ROLES[x]['icon']} {ROLES[x]['label']}",
                                index=list(ROLES.keys()).index(row["rol"]) if row["rol"] in ROLES else 0,
                                key=f"rol_sel_{row['id']}")

                            if st.button("💾 Guardar rol", key=f"save_rol_{row['id']}",
                                         use_container_width=True):
                                if nuevo_rol not in ROLES:
                                    st.error("Rol no válido")
                                else:
                                    conn = get_conn()
                                    conn.execute(
                                        "UPDATE usuarios SET rol=?, actualizado=? WHERE id=?",
                                        (nuevo_rol, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row["id"]))
                                    conn.commit(); conn.close()
                                    registrar_auditoria(
                                        u["id"], u["username"], "CAMBIO_ROL",
                                        f"Usuario #{row['id']} @{row['username']} → rol: {nuevo_rol}",
                                        "usuarios")
                                    st.success(f"Rol de @{row['username']} actualizado a {ROLES[nuevo_rol]['label']} ✓")
                                    st.rerun()
                        else:
                            st.info("🔒 Solo el Super Administrador puede cambiar roles.")

                        btn_lbl  = "🔴 Desactivar" if activo else "✅ Activar"
                        btn_val  = 0 if activo else 1
                        if st.button(btn_lbl, key=f"toggle_{row['id']}",
                                     use_container_width=True):
                            conn = get_conn()
                            conn.execute("UPDATE usuarios SET activo=? WHERE id=?",
                                         (btn_val, row["id"]))
                            conn.commit(); conn.close()
                            registrar_auditoria(u["id"], u["username"],
                                                "ACTIVAR" if btn_val else "DESACTIVAR",
                                                f"Usuario #{row['id']} @{row['username']}", "usuarios")
                            st.rerun()

                        if tiene_permiso("eliminar_usuarios") and row["rol"] != "superadmin":
                            if st.checkbox("⚠ Eliminar usuario", key=f"chk_del_{row['id']}"):
                                st.markdown("<div style='color:#FF5252;font-size:0.75rem;'>Esta acción es permanente.</div>", unsafe_allow_html=True)
                                if st.button("🗑 Confirmar eliminación",
                                             key=f"del_{row['id']}",
                                             use_container_width=True):
                                    conn = get_conn()
                                    conn.execute("DELETE FROM usuarios WHERE id=?", (row["id"],))
                                    conn.commit(); conn.close()
                                    registrar_auditoria(u["id"], u["username"], "ELIMINAR_USUARIO",
                                                        f"@{row['username']}", "usuarios")
                                    st.success("Usuario eliminado ✓"); st.rerun()

                        # Ver actividad del usuario
                        if st.button("📋 Ver actividad", key=f"activity_{row['id']}", use_container_width=True):
                            conn = get_conn()
                            actividad = pd.read_sql(
                                "SELECT fecha, accion, detalle, modulo FROM auditoria WHERE usuario_id=? ORDER BY fecha DESC LIMIT 25",
                                conn, params=(int(row["id"]),))
                            conn.close()
                            if actividad.empty:
                                st.info("No hay actividad registrada para este usuario.")
                            else:
                                st.dataframe(actividad, use_container_width=True, hide_index=True)

                        # Inicio de sesión temporal como el usuario (solo Super Administrador)
                        if es_superadmin():
                            if st.button("🔑 Iniciar sesión como este usuario", key=f"imp_{row['id']}", use_container_width=True):
                                ok_imp, msg_imp = _iniciar_sesion_como_usuario(int(row["id"]))
                                if ok_imp:
                                    st.success(msg_imp)
                                    st.rerun()
                                else:
                                    st.error(msg_imp)

                        # Reset contraseña
                        if st.checkbox("🔑 Cambiar contraseña", key=f"chk_pwd_{row['id']}"):
                            nueva_pwd = st.text_input("Nueva contraseña",
                                                       type="password",
                                                       key=f"npwd_{row['id']}")
                            if st.button("Aplicar", key=f"rpwd_{row['id']}",
                                         use_container_width=True):
                                ok_p, msg_p = _validar_password(nueva_pwd)
                                if not ok_p:
                                    st.error(msg_p)
                                else:
                                    conn = get_conn()
                                    conn.execute(
                                        "UPDATE usuarios SET password_hash=?, actualizado=? WHERE id=?",
                                        (_hash_password(nueva_pwd), row["id"]))
                                    conn.commit(); conn.close()
                                    registrar_auditoria(u["id"], u["username"], "RESET_PASSWORD",
                                                        f"@{row['username']}", "usuarios")
                                    st.success("Contraseña actualizada ✓")

    # ── TAB: Nuevo usuario ────────────────────────────────────────────────────
    with tab_nuevo:
        if not tiene_permiso("crear_usuarios"):
            st.error("🔒 No tienes permiso para crear usuarios.")
        else:
            st.markdown("""
            <div class='sol-card-title'><span class='step-badge'>+</span>
            REGISTRAR NUEVO USUARIO</div>
            """, unsafe_allow_html=True)

            col_n1, col_n2 = st.columns(2)
            with col_n1:
                n_nombre   = st.text_input("Nombre completo *", key="nu_nombre",
                                           placeholder="Ej: Juan Pérez González")
                n_username = st.text_input("Nombre de usuario *", key="nu_user",
                                           placeholder="Ej: jperez")
                n_email    = st.text_input("Correo electrónico *", key="nu_email",
                                           placeholder="jperez@empresa.com")
            with col_n2:
                n_rol    = st.selectbox("Rol *", options=list(ROLES.keys()),
                                        format_func=lambda x: f"{ROLES[x]['icon']} {ROLES[x]['label']}",
                                        key="nu_rol")
                n_pwd    = st.text_input("Contraseña *", type="password", key="nu_pwd",
                                         placeholder="Mín. 8 chars, 1 mayúscula, 1 número")
                n_pwd2   = st.text_input("Confirmar contraseña *", type="password",
                                          key="nu_pwd2")

            # Vista previa de permisos del rol seleccionado
            if n_rol:
                rol_sel = ROLES[n_rol]
                st.markdown(f"""
                <div class='sol-card' style='margin-top:0.8rem;'>
                    <div style='color:{rol_sel["color"]};font-family:Rajdhani,sans-serif;
                     font-weight:600;margin-bottom:0.6rem;'>
                        {rol_sel["icon"]} Permisos de {rol_sel["label"]}
                    </div>
                    <div style='display:flex;flex-wrap:wrap;gap:0.4rem;'>
                """, unsafe_allow_html=True)
                for p in rol_sel["permisos"]:
                    st.markdown(
                        f"<span style='background:{rol_sel['color']}22;color:{rol_sel['color']};"
                        f"font-size:0.72rem;padding:2px 8px;border-radius:10px;"
                        f"border:1px solid {rol_sel['color']}44;'>"
                        f"{PERMISOS_LABELS.get(p, p)}</span>",
                        unsafe_allow_html=True)
                st.markdown("</div></div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✅ Crear usuario", use_container_width=True,
                         type="primary", key="btn_crear_user"):
                errores = []
                if not n_nombre.strip():  errores.append("Nombre completo requerido")
                if not n_username.strip(): errores.append("Nombre de usuario requerido")
                if not _validar_email(n_email): errores.append("Correo electrónico inválido")
                ok_p, msg_p = _validar_password(n_pwd)
                if not ok_p: errores.append(f"Contraseña: {msg_p}")
                if n_pwd != n_pwd2: errores.append("Las contraseñas no coinciden")

                if errores:
                    for e in errores: st.error(e)
                else:
                    try:
                        conn = get_conn()
                        conn.execute("""
                            INSERT INTO usuarios
                            (username, nombre_completo, email, password_hash, rol, creado_por)
                            VALUES (?,?,?,?,?,?)
                        """, (n_username.strip().lower(), n_nombre.strip(),
                              n_email.strip().lower(), _hash_password(n_pwd),
                              n_rol, u["id"]))
                        conn.commit(); conn.close()
                        registrar_auditoria(u["id"], u["username"], "CREAR_USUARIO",
                                            f"@{n_username} rol:{n_rol}", "usuarios")
                        st.success(f"✓ Usuario @{n_username} creado exitosamente")
                        st.balloons()
                    except sqlite3.IntegrityError as e:
                        if "username" in str(e):
                            st.error("❌ El nombre de usuario ya existe")
                        elif "email" in str(e):
                            st.error("❌ El correo electrónico ya está registrado")
                        else:
                            st.error(f"❌ Error: {e}")

    # ── TAB: Auditoría ────────────────────────────────────────────────────────
    with tab_auditoria:
        if not tiene_permiso("ver_auditoria"):
            st.error("🔒 No tienes permiso para ver la auditoría.")
        else:
            conn = get_conn()
            aud_df = pd.read_sql("""
                SELECT fecha, username, accion, modulo, detalle
                FROM auditoria
                ORDER BY fecha DESC LIMIT 200
            """, conn)
            conn.close()

            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                filtro_user = st.text_input("Filtrar por usuario", key="aud_user")
            with col_f2:
                filtro_acc  = st.text_input("Filtrar por acción", key="aud_acc")
            with col_f3:
                filtro_mod  = st.text_input("Filtrar por módulo", key="aud_mod")

            df_show = aud_df.copy()
            if filtro_user: df_show = df_show[df_show["username"].str.contains(filtro_user, case=False, na=False)]
            if filtro_acc:  df_show = df_show[df_show["accion"].str.contains(filtro_acc, case=False, na=False)]
            if filtro_mod:  df_show = df_show[df_show["modulo"].str.contains(filtro_mod, case=False, na=False)]

            st.markdown(f"<div style='color:#8A9BBD;font-size:0.8rem;margin-bottom:0.5rem;'>"
                        f"Mostrando {len(df_show)} de {len(aud_df)} registros</div>",
                        unsafe_allow_html=True)

            for _, row in df_show.head(100).iterrows():
                accion_col = {"LOGIN": "#00E676", "LOGOUT": "#8A9BBD",
                              "CREAR": "#00BCD4", "ELIMINAR": "#FF5252",
                              "CAMBIO": "#FFB300"}.get(row["accion"][:6], "#8A9BBD")
                st.markdown(f"""
                <div style='background:#0F1525;border-left:3px solid {accion_col};
                 border-radius:6px;padding:0.4rem 0.8rem;margin-bottom:0.3rem;
                 display:flex;gap:1rem;align-items:center;font-size:0.78rem;'>
                    <span style='color:#2A3A55;font-family:Share Tech Mono;min-width:130px;'>{str(row['fecha'])[:16]}</span>
                    <span style='color:#FFB300;font-weight:600;min-width:100px;'>@{row['username'] or '—'}</span>
                    <span style='color:{accion_col};font-family:Share Tech Mono;min-width:140px;'>{row['accion']}</span>
                    <span style='color:#8A9BBD;min-width:90px;'>{row['modulo'] or ''}</span>
                    <span style='color:#E8EDF5;'>{row['detalle'] or ''}</span>
                </div>
                """, unsafe_allow_html=True)

            if tiene_permiso("gestion_sistema"):
                st.markdown("<hr style='border-color:#2A3A55;margin:1rem 0;'>", unsafe_allow_html=True)
                if st.button("🗑 Limpiar auditoría (>8 días)", key="limpiar_aud"):
                    conn = get_conn()
                    conn.execute("DELETE FROM auditoria WHERE fecha < datetime('now','-8 days')")
                    conn.commit(); conn.close()
                    st.success("Auditoría limpiada ✓"); st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# ACTUALIZACIÓN DE PERFIL
# ═══════════════════════════════════════════════════════════════════════════════
def mostrar_actualizacion_perfil():
    u=usuario_activo()
    if not u: return
    conn=get_conn(); row=conn.execute("SELECT nombre_completo,email FROM usuarios WHERE id=?",(u["id"],)).fetchone(); conn.close()
    if not row: return
    nombre=st.text_input("Nombre completo",value=row[0],key="perfil_nombre")
    email=st.text_input("Correo electrónico",value=row[1],key="perfil_email")
    if st.button("💾 Guardar mis datos",use_container_width=True,type="primary",key="btn_guardar_perfil"):
        if not nombre.strip(): st.error("El nombre no puede quedar vacío"); return
        if not _validar_email(email): st.error("Correo electrónico inválido"); return
        conn=get_conn()
        try:
            conn.execute("UPDATE usuarios SET nombre_completo=?,email=?,actualizado=? WHERE id=?",(nombre.strip(),email.strip().lower(),datetime.now().strftime("%Y-%m-%d %H:%M:%S"),u["id"]))
            conn.commit()
            st.session_state["usuario_sesion"]["nombre"]=nombre.strip(); st.session_state["usuario_sesion"]["email"]=email.strip().lower()
            registrar_auditoria(u["id"],u["username"],"ACTUALIZAR_PERFIL","Nombre/correo actualizados","seguridad")
            st.success("✓ Datos actualizados y guardados en la base de datos")
        except sqlite3.IntegrityError: st.error("❌ Ese correo ya está registrado por otra cuenta")
        finally: conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# CAMBIO DE CONTRASEÑA (perfil propio)
# ═══════════════════════════════════════════════════════════════════════════════
def mostrar_cambio_password():
    """Panel para que el usuario cambie su propia contraseña."""
    u = usuario_activo()
    if not u:
        return

    st.markdown("""
    <div class='sol-card-title'><span class='step-badge'>🔑</span>
    CAMBIAR CONTRASEÑA</div>
    """, unsafe_allow_html=True)

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        pwd_actual = st.text_input("Contraseña actual", type="password", key="cp_actual")
        pwd_nueva  = st.text_input("Nueva contraseña", type="password", key="cp_nueva",
                                   help="Mín. 8 chars, 1 mayúscula, 1 número")
        pwd_conf   = st.text_input("Confirmar nueva contraseña", type="password",
                                   key="cp_conf")

        if st.button("💾 Actualizar contraseña", use_container_width=True,
                     type="primary", key="btn_cambiar_pwd"):
            conn = get_conn()
            row = conn.execute("SELECT password_hash FROM usuarios WHERE id=?",
                               (u["id"],)).fetchone()
            conn.close()

            if not row or row[0] != _hash_password(pwd_actual):
                st.error("❌ La contraseña actual es incorrecta")
            else:
                ok_p, msg_p = _validar_password(pwd_nueva)
                if not ok_p:
                    st.error(f"❌ {msg_p}")
                elif pwd_nueva != pwd_conf:
                    st.error("❌ Las contraseñas no coinciden")
                else:
                    conn = get_conn()
                    conn.execute("UPDATE usuarios SET password_hash=? WHERE id=?",
                                 (_hash_password(pwd_nueva), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), u["id"]))
                    conn.commit(); conn.close()
                    registrar_auditoria(u["id"], u["username"], "CAMBIO_PASSWORD",
                                        "Contraseña actualizada por el usuario", "seguridad")
                    st.success("✓ Contraseña actualizada exitosamente")

    with col_p2:
        st.markdown(f"""
        <div class='sol-card'>
            <div style='color:#FFB300;font-family:Rajdhani,sans-serif;font-weight:600;
             margin-bottom:0.8rem;'>MI PERFIL</div>
            <table style='font-size:0.82rem;width:100%;border-collapse:collapse;'>
                <tr><td style='color:#8A9BBD;padding:0.3rem 0;'>ID</td>
                    <td style='font-family:Share Tech Mono;color:#FFD54F;'>#{u['id']}</td></tr>
                <tr><td style='color:#8A9BBD;padding:0.3rem 0;'>Nombre</td>
                    <td style='color:#E8EDF5;'>{u['nombre']}</td></tr>
                <tr><td style='color:#8A9BBD;padding:0.3rem 0;'>Usuario</td>
                    <td style='color:#E8EDF5;'>@{u['username']}</td></tr>
                <tr><td style='color:#8A9BBD;padding:0.3rem 0;'>Correo</td>
                    <td style='color:#E8EDF5;'>{u['email']}</td></tr>
                <tr><td style='color:#8A9BBD;padding:0.3rem 0;'>Rol</td>
                    <td style='color:{ROLES[u["rol"]]["color"]};font-weight:700;'>
                        {ROLES[u["rol"]]["icon"]} {ROLES[u["rol"]]["label"]}</td></tr>
            </table>
            <div style='margin-top:1rem;'>
                <div style='color:#8A9BBD;font-size:0.75rem;margin-bottom:0.4rem;'>MIS PERMISOS</div>
                {''.join(
                    f"<div style='font-size:0.73rem;color:#00E676;'>✓ {PERMISOS_LABELS.get(p,p)}</div>"
                    for p in ROLES[u['rol']]['permisos']
                )}
            </div>
        </div>
        """, unsafe_allow_html=True)
