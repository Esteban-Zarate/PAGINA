# Calculadora Solar

Aplicación web desarrollada para apoyar el dimensionamiento y análisis de sistemas fotovoltaicos.

**Creado por Esteban Zarate**

## Acceso y usuarios

- El inicio de sesión se realiza **únicamente con el nombre de usuario** y la contraseña.
- El **correo electrónico no se utiliza para iniciar sesión**; se conserva como dato de contacto y perfil.
- El nombre de usuario debe ser único.
- Al crear una cuenta desde la pantalla pública, la cuenta queda con rol **Visualizador**.
- El administrador puede gestionar usuarios, activar/desactivar cuentas, cambiar roles y restablecer contraseñas según sus permisos.

> Las credenciales iniciales se configuran localmente en `.streamlit/secrets.toml`. Este README no contiene cuentas ni contraseñas.

## Registro y actualización de cuentas

La pantalla de acceso permite crear una cuenta nueva con nombre completo, nombre de usuario, correo y contraseña. El nombre de usuario queda guardado en `solar_calc.db` y es el identificador utilizado para iniciar sesión.

Desde **Mi perfil**, cada usuario puede actualizar su nombre, correo y contraseña; los cambios se guardan en la base de datos.

## Seguridad

- Las contraseñas no se almacenan en texto plano en SQLite.
- Se utiliza hash SHA-256 con sal de la aplicación.
- `.streamlit/secrets.toml` no debe publicarse en GitHub.
- `solar_calc.db` no debe publicarse en repositorios públicos porque contiene datos de usuarios y sesiones.
- Las nuevas cuentas públicas reciben el rol Visualizador por defecto.

## Ejecución

```bash
streamlit run solar_app.py --server.port 8501
```


## Identidad y originalidad

**Energía Viva Solar** utiliza una identidad visual propia: paleta, composición, textos de interfaz, nombre del asistente y elementos gráficos fueron definidos para este proyecto. No se incorporan logotipos, capturas de pantalla ni textos propietarios de otras aplicaciones.

El proyecto puede usar bibliotecas y estándares de software de terceros conforme a sus respectivas licencias. La originalidad visual no implica una garantía jurídica absoluta de ausencia de similitudes; antes de una publicación comercial conviene revisar también las licencias de dependencias, imágenes, fuentes y cualquier código externo incorporado.
