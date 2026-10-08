# Nuevas funciones — Calculadora Solar

## 1. Nombre y logo
Se retiró el logo de la interfaz principal y del menú lateral. La identidad se muestra como texto:
**☀ Calculadora Solar**

## 2. EcoBot Solar
Se añadió el módulo **EcoBot Solar — Chatbot IA**.

Puede:
- Explicar OFF-GRID, ON-GRID y HÍBRIDO.
- Calcular paneles con consumo diario.
- Explicar qué tipo de panel usar como referencia.
- Seleccionar una referencia de kit de AutoSolar según el sistema seleccionado.
- Trabajar inicialmente con 6,16 kWh/día como consumo de ejemplo.

Si se configura `OPENAI_API_KEY`, EcoBot puede usar un modelo externo. Si no se configura, funciona con el asistente técnico local incluido.

Variables opcionales:
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

## 3. Recuperación de contraseña por correo
La pantalla de inicio ahora tiene **¿OLVIDASTE TU CONTRASEÑA?**.

Flujo:
1. El usuario escribe el correo registrado.
2. La aplicación genera un código de 6 dígitos.
3. El código se envía por SMTP.
4. El código vence en 10 minutos.
5. El usuario crea una nueva contraseña.

### Configuración SMTP en `.streamlit/secrets.toml`

```toml
[smtp]
host = "smtp.gmail.com"
port = 587
user = "tu-correo@ejemplo.com"
password = "CONTRASEÑA_O_APP_PASSWORD"
from = "tu-correo@ejemplo.com"
use_tls = true
```

También se aceptan las variables de entorno `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` y `SMTP_USE_TLS`.

No guardes contraseñas de correo dentro del código fuente ni en GitHub.

## 4. Referencias AutoSolar
Las referencias comerciales se mantienen vinculadas al catálogo de AutoSolar:
- OFF-GRID: Kit Solar Para Casa 3000W 48V 6500Wh/día con Batería Litio.
- ON-GRID: Kit Solar On Grid 6000W 12810Wh/día Growatt.
- HÍBRIDO: Kit Solar Híbrido 3000W 21350Wh/día Growatt.

Los precios y disponibilidad pueden cambiar, por lo que el enlace abre la ficha/catálogo actual.

## 5. Ejemplo de cálculo
Para 6,16 kWh/día, usando 4,5 HSP, panel de 620 W y rendimiento global de 80 %:

Energía útil por panel ≈ 2,232 kWh/día.

6,16 / 2,232 ≈ 2,76 → **3 paneles como mínimo matemático**.

Para una instalación real se deben revisar sombras, temperatura, orientación, pérdidas, potencia de inversor y cargas de arranque. Por eso un kit comercial puede incluir más paneles que el mínimo matemático.

## 6. Ejecución
```bash
streamlit run solar_app.py --server.port 8501
```


## Recuperación de contraseña y EcoBot

- Cada cuenta guarda un correo electrónico único. Ese correo es el DESTINO del código de recuperación.
- El administrador configura una sola cuenta técnica SMTP en `.streamlit/secrets.toml`; no se usa el correo del administrador como destino de todos los usuarios.
- El código vence en 10 minutos y permite establecer una nueva contraseña.
- EcoBot Solar está disponible para cualquier usuario autenticado, incluido el Super Administrador.
- Para respuestas de IA abiertas, configura `[ai] api_key` y `model` en los secrets de Streamlit. La clave no se guarda en la base de datos ni se muestra al usuario.
