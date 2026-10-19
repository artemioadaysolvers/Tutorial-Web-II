# Validación de la actualización

18 de octubre de 2026.

Esta actualización modifica el empaquetado y las instrucciones de publicación. Retira el workflow incluido para que lo genere Azure al conectar GitHub, y agrega el tutorial completo en LaTeX. No modifica el código de la aplicación.

En la revisión anterior del mismo código se completó la construcción de Next.js 16.4.2 con React 19.3.1 y pasaron las 15 pruebas Python, incluida la entrega de archivos exportados y sus hashes CSP. Esas pruebas se conservan. La plantilla generada por Azure puede no ejecutarlas automáticamente.

La integración real del Centro de implementación requiere tus cuentas y recursos; no se ejecutó desde este entorno. No se probaron acceso real a Microsoft, Cosmos o despliegue Azure. Docker no está instalado en este equipo. Los dobles de almacenamiento existen solo en las pruebas; la aplicación utiliza Cosmos exclusivamente.

El ZIP excluye .github/workflows, credenciales, entornos virtuales, node_modules y archivos compilados del frontend. Después de la configuración, Azure debe agregar el workflow al repositorio remoto; descargarlo a la copia local con Fetch/Pull.
