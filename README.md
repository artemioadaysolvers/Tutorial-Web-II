# Recados — TypeScript + Next.js + React + Azure 

Esta adaptación convierte el frontend existente a TypeScript estricto con Next.js y React. Conserva el diseño, los textos, el login GitHub, el backend Flask, Cosmos DB, Docker y el workflow de Azure del ZIP original. El backend sigue en Python para mantener la arquitectura y configuración existentes. No requiere cambios en las variables de Azure ni migraciones de datos.

## Actualizar tu repositorio

1. Descomprimir el ZIP. Copiar TODO el contenido de esta carpeta a la raíz del mismo repositorio: Dockerfile debe quedar junto a server.py.
2. Reemplazar los archivos existentes, incluyendo tests y docs. Conservar .git y el workflow .github/workflows que Azure haya creado. Este ZIP incluye el workflow original sin cambios: .github/workflows/main_web-recados-2026abc.yml. Asegúrate de copiar también la carpeta oculta .github.
3. Seguir docs/AZURE.md antes de probar el login. Enviar los cambios a la rama de publicación activa el workflow solamente si ya está configurado.

No recrear App Service, Cosmos DB, RecadosDB ni el contenedor recados. Mantener las reglas de firewall que agregaste.

## Funcionamiento

El backend valida state, limita el flujo a 10 minutos y utiliza PKCE S256. Intercambia el código con GitHub y consulta /user para obtener el identificador numérico estable de la cuenta; no usa el nombre ni el correo como propietario. No solicita acceso a repositorios privados ni a correos. El token se utiliza en el servidor y no se guarda en cookies ni en Cosmos.

Cerrar sesión termina la sesión de Recados en ese navegador; no cierra la cuenta de github.com. Las sesiones están firmadas, usan HttpOnly, SameSite=Lax y Secure en HTTPS, con vencimiento tras 8 horas de inactividad. Las operaciones de escritura requieren CSRF. Cambiar SECRET_KEY invalida las sesiones. No hay revocación central de cookies robadas.

Los recados antiguos creados con Microsoft no se vinculan automáticamente a GitHub: son identidades distintas. No se eliminan, pero necesitarían una migración verificada para aparecer con otra identidad.

## Pruebas

python -m unittest discover -s tests -v

En frontend: npm ci, npm run typecheck y npm run build. Docker realiza la construcción automáticamente. Los tests de identidad usan respuestas simuladas; la conexión real se verifica después de configurar las credenciales.

No subir .env, credenciales, node_modules, .next ni frontend/out. Solo Python y Cosmos se ejecutan en producción: Node construye la exportación estática en Docker.

## Cambios de esta adaptación

Componentes app/page.tsx y app/layout.tsx; tipos de sesión, recados, formularios y referencias DOM; tsconfig.json estricto; next-env.d.ts; dependencias de TypeScript y tipos con versiones fijadas en package-lock.json. Se conservan las versiones originales de Next.js y React.

Referencia de integración: https://nextjs.org/docs/app/api-reference/config/typescript
