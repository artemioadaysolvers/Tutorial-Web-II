# Typewriter · Next.js + React + TypeScript

Máquina de escribir con el fondo beige del PDF (#f2e8cf), texto marrón, sonidos originales y guardado privado con GitHub y Cosmos DB. El frontend sigue en TypeScript estricto, Next.js y React; el backend Flask sirve la exportación de Next.js como en el proyecto original.

## Subir al Azure existente

1. Descomprime este ZIP y copia el CONTENIDO de su carpeta a la raíz del MISMO repositorio. Dockerfile debe quedar junto a server.py. Copia también la carpeta oculta .github.
2. Conserva tu carpeta .git y el workflow de Azure que ya funciona. El workflow original .github/workflows/main_web-recados-2026abc.yml está incluido sin modificaciones. Si tu repositorio tiene una versión más reciente de ese workflow, conserva la que ya funciona.
3. Haz commit y push a la rama de despliegue (main en el workflow incluido). El workflow se ejecuta al enviar cambios solo si ya está configurado para esa rama. No subas el ZIP como un único archivo ni crees recursos nuevos en Azure.

Esta actualización no requiere cambiar variables de entorno, secretos, puerto, imagen, OAuth ni esquema de Cosmos DB. Conserva GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, APP_URL, SECRET_KEY, COSMOS_ENDPOINT, COSMOS_KEY, COSMOS_DATABASE, COSMOS_CONTAINER y WEBSITES_PORT exactamente como estén en tu despliegue funcional. Mantiene los valores predeterminados RecadosDB y recados, la partición owner y las rutas /api/recados. No recrees App Service, Cosmos DB, RecadosDB ni el contenedor recados; conserva las reglas de firewall existentes.

Los secretos de GitHub Actions están asociados al repositorio actual. Crear otro repositorio no transfiere esos secretos. Para mantener Azure sin cambios, reemplaza los archivos en el repositorio ya conectado.

## Uso

- Escribe directamente en la hoja, incluso antes de iniciar sesión. Límite de 2000 caracteres, igual que el proyecto original.
- Guardar o Ctrl/Cmd + S guarda en tu cuenta. Si no has iniciado sesión, el borrador se conserva temporalmente en esta pestaña mientras entras con el acceso GitHub existente. Al volver, pulsa Guardar texto.
- Pulsa un texto en Mis textos para volver a abrirlo. Si lo modificas, Guardar copia crea un texto nuevo y conserva el anterior.
- Nueva hoja comienza otro texto. El navegador pide confirmación al reemplazar cambios sin guardar.
- Descargar .txt permite guardar una copia local, también sin iniciar sesión.
- Cada botón reproduce static/sounds/boton.wav. Cada pulsación de tecla dentro del editor reproduce static/sounds/teclado.wav. El control Sonido activa o silencia ambos; recuerda tu preferencia en este navegador. Los WAV se incluyen sin modificaciones.
- Borrar elimina un texto de tu colección después de confirmar.

Los espacios iniciales, líneas vacías y saltos finales se conservan al guardar. No hay guardado automático en Cosmos: usa Guardar texto. Si falla una operación, el texto permanece en el editor.

## Autenticación y datos

El backend valida state, limita el flujo a 10 minutos y utiliza PKCE S256. Intercambia el código con GitHub y consulta /user para obtener el identificador numérico estable de la cuenta; no usa el nombre ni el correo como propietario. No solicita acceso a repositorios privados ni a correos. El token se utiliza en el servidor y no se guarda en cookies ni en Cosmos.

Cerrar sesión termina la sesión de Recados en ese navegador; no cierra la cuenta de github.com. Las sesiones están firmadas, usan HttpOnly, SameSite=Lax y Secure en HTTPS, con vencimiento tras 8 horas de inactividad. Las operaciones de escritura requieren CSRF. Cambiar SECRET_KEY invalida las sesiones. No hay revocación central de cookies robadas.

Los recados ya creados con GitHub aparecen como textos guardados. Los recados antiguos creados con Microsoft no se vinculan automáticamente a GitHub porque son identidades distintas. No se eliminan, pero necesitarían una migración verificada para aparecer con otra identidad.

## Desarrollo y comprobación

En frontend:

    npm ci
    npm run typecheck
    npm run build

En la raíz:

    python -m pip install -r requirements.txt
    python -m unittest discover -s tests -v

Docker construye Next.js y ejecuta Flask/Gunicorn en el puerto 8080 como antes. Node construye la exportación estática en Docker; solo Python y Cosmos se ejecutan en producción. No subas node_modules, .next, frontend/out, credenciales ni archivos .env. Los sonidos se sirven mediante la ruta /static ya existente, y cumplen la política de contenido del servidor.

Las pruebas verifican autenticación, CSRF, aislamiento entre usuarios, guardado fiel del texto, archivos de sonido y exportación de Next.js. Las pruebas de identidad usan respuestas simuladas; la autenticación real y el Cosmos de tu cuenta se comprueban después de configurar las credenciales y desplegar. Las pruebas locales usan una base en memoria aislada.

Consulta docs/AZURE.md para los detalles conservados de la instalación original y docs/VALIDACION.md para las comprobaciones de esta adaptación.
