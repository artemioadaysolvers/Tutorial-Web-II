# Typewriter · Next.js + React + TypeScript

Máquina de escribir con el fondo beige del PDF (#f2e8cf), texto marrón, sonidos originales y guardado privado con GitHub y Cosmos DB. El frontend sigue en TypeScript estricto, Next.js y React; el backend Flask sirve la exportación de Next.js como en el proyecto original.

## Subir al Azure existente

1. Descomprime este ZIP y copia el CONTENIDO de su carpeta a la raíz del MISMO repositorio. Dockerfile debe quedar junto a server.py. Copia también la carpeta oculta .github.
2. Conserva tu carpeta .git. El workflow original .github/workflows/main_web-recados-2026abc.yml está incluido sin modificaciones. Si tu repositorio tiene una versión más reciente de ese workflow, conserva la que ya funciona.
3. Haz commit y push a la rama de despliegue (main en el workflow incluido). No subas el ZIP como un único archivo ni crees recursos nuevos en Azure.

Esta actualización no requiere cambiar variables de entorno, secretos, puerto, imagen, OAuth ni esquema de Cosmos DB. Conserva GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, APP_URL, SECRET_KEY, COSMOS_ENDPOINT, COSMOS_KEY, COSMOS_DATABASE, COSMOS_CONTAINER y WEBSITES_PORT exactamente como estén en tu despliegue funcional. Mantiene los valores predeterminados RecadosDB y recados, la partición owner y las rutas /api/recados. Los nombres internos Account, Note, account, notes, body, csrf, save y remove también se mantienen. Los recados que ya existían aparecen como textos guardados.

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

## Desarrollo y comprobación

En frontend:

    npm ci
    npm run typecheck
    npm run build

En la raíz:

    python -m pip install -r requirements.txt
    python -m unittest discover -s tests -v

Docker construye Next.js y ejecuta Flask/Gunicorn en el puerto 8080 como antes. No subas node_modules, .next, frontend/out, credenciales ni archivos .env. Los sonidos se sirven mediante la ruta /static ya existente, y cumplen la política de contenido del servidor.

Las pruebas verifican autenticación, CSRF, aislamiento entre usuarios, guardado fiel del texto, archivos de sonido y exportación de Next.js. La autenticación real y el Cosmos de tu cuenta se comprueban después del despliegue; las pruebas locales usan una base en memoria aislada.

Consulta docs/AZURE.md para los detalles conservados de la instalación original y docs/VALIDACION.md para las comprobaciones de esta adaptación.
