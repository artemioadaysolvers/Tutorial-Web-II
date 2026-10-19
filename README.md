# Recados — GitHub + Next.js + Python + Azure

Esta versión reemplaza el login de Microsoft por GitHub. Conserva Docker, Next.js/React, Flask y Cosmos DB. No requiere Entra ID ni permisos de la UAI. Cada visitante necesita una cuenta GitHub.

## Actualizar tu repositorio

1. Descomprimir el ZIP. Copiar TODO el contenido de esta carpeta a la raíz del mismo repositorio: Dockerfile debe quedar junto a server.py.
2. Reemplazar los archivos existentes, incluyendo tests y docs. Conservar .git y el workflow .github/workflows que Azure haya creado. Este ZIP no incluye un pipeline: no borres el que ya funciona.
3. Seguir docs/AZURE.md antes de probar el login. Enviar los cambios a la rama de publicación activa el workflow solamente si ya está configurado.

No recrear App Service, Cosmos DB, RecadosDB ni el contenedor recados. Mantener las reglas de firewall que agregaste.

## Funcionamiento

El backend valida state, limita el flujo a 10 minutos y utiliza PKCE S256. Intercambia el código con GitHub y consulta /user para obtener el identificador numérico estable de la cuenta; no usa el nombre ni el correo como propietario. No solicita acceso a repositorios privados ni a correos. El token se utiliza en el servidor y no se guarda en cookies ni en Cosmos.

Cerrar sesión termina la sesión de Recados en ese navegador; no cierra la cuenta de github.com. Las sesiones están firmadas, usan HttpOnly, SameSite=Lax y Secure en HTTPS, con vencimiento tras 8 horas de inactividad. Las operaciones de escritura requieren CSRF. Cambiar SECRET_KEY invalida las sesiones. No hay revocación central de cookies robadas.

Los recados antiguos creados con Microsoft no se vinculan automáticamente a GitHub: son identidades distintas. No se eliminan, pero necesitarían una migración verificada para aparecer con otra identidad.

## Pruebas

python -m unittest discover -s tests -v

En frontend: npm ci y npm run build. Docker realiza la construcción automáticamente. Los tests de identidad usan respuestas simuladas; la conexión real se verifica después de configurar las credenciales.

No subir .env, credenciales, node_modules, .next ni frontend/out. Solo Python y Cosmos se ejecutan en producción: Node construye la exportación estática en Docker.
