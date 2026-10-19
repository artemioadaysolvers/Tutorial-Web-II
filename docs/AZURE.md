# Configurar GitHub y publicar en el Azure existente

## 1. Registrar el login (OAuth App, no un repositorio nuevo)

1. Entrar con tu cuenta personal en https://github.com/settings/developers
2. Elegir OAuth Apps > New OAuth App.
3. Application name: Recados.
4. Homepage URL: https://web-recados-2026abc-dme6gyf6cbdbf3a4.chilecentral-01.azurewebsites.net
5. Authorization callback URL: https://web-recados-2026abc-dme6gyf6cbdbf3a4.chilecentral-01.azurewebsites.net/auth/callback
6. No habilitar Device Flow. Pulsar Register application.
7. Copiar Client ID. Pulsar Generate a new client secret y copiar su valor; protegerlo y no pegarlo en GitHub ni en el chat.

Para otra Web App, sustituir ambas URL por su dominio real HTTPS completo. No usar la URL del repositorio como callback.

## 2. Variables de App Service

En App Services > web-recados-2026abc > Configuración > Variables de entorno > Configuración de aplicación, agregar:

| Nombre | Valor |
|---|---|
| GITHUB_CLIENT_ID | Client ID de la OAuth App |
| GITHUB_CLIENT_SECRET | Secreto de esa OAuth App |
| APP_URL | https://web-recados-2026abc-dme6gyf6cbdbf3a4.chilecentral-01.azurewebsites.net |
| SECRET_KEY | Clave aleatoria estable, mínimo 32 caracteres; conservar la anterior si ya existe |
| COSMOS_ENDPOINT | URI de tu cuenta Cosmos |
| COSMOS_KEY | Clave de lectura y escritura de Cosmos |
| COSMOS_DATABASE | RecadosDB |
| COSMOS_CONTAINER | recados |
| WEBSITES_PORT | 8080 para contenedor clásico |

Retirar MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET y MICROSOFT_TENANT: esta versión no las usa. No usar prefijo NEXT_PUBLIC_ para secretos. Easy Auth de App Service debe estar desactivado: Flask gestiona el login.

Conservar el comando de inicio vacío y HTTPS activado. Si el servicio usa sidecar, configurar el puerto de destino del contenedor principal en 8080; WEBSITES_PORT no sustituye ese campo. Conservar el modelo actual sin convertirlo.

## 3. Publicación

Reemplazar el contenido del mismo repositorio y hacer Commit/Push a main (o a la rama realmente configurada). Conservar .git y el workflow de Azure. No subir el ZIP como archivo.

Si el despliegue automático aún no está configurado, abrir App Service > Centro de implementación > Configuración, conectar GitHub Actions y elegir el repositorio y rama. Elegir ACR como destino, imagen recados, Dockerfile de la raíz y contexto '.'. Revisar la vista previa: debe construir Docker, publicar en ACR y actualizar el contenedor. Completar la autenticación exigida por esa plantilla y guardar. No usar una plantilla de publicación directa de código Python. Las opciones y permisos dependen de tu portal; si no aparece esa integración, revisar la configuración antes de crear otro plan o recurso.

Azure debe agregar .github/workflows al repositorio. Descargar su commit con Fetch/Pull en GitHub Desktop. Este ZIP no genera ni sustituye ese archivo. La primera ejecución debe reemplazar la imagen temporal mcr.microsoft.com/k8se/quickstart:latest; mientras esa imagen siga activa, todavía no está desplegada Recados.

F1 es para pruebas y tiene límites de CPU/memoria y sin Always On; puede haber arranques lentos o suspensión por cuota. Usarlo si el portal admite tu contenedor Linux en F1. No contratar B1 para seguir estas instrucciones sin revisar su precio. ACR Basic se cobra por separado. Cosmos conserva su nivel gratuito solo dentro de los límites aplicables.

## 4. Comprobar

1. Revisar GitHub > Actions: construcción y despliegue correctos.
2. Abrir APP_URL/health: debe responder {"status":"ok"}.
3. Abrir la web, entrar con GitHub y guardar un recado.
4. Cerrar sesión y volver a entrar con la misma cuenta: debe persistir.
5. Con otra cuenta GitHub, comprobar que no ve ni puede borrar los recados anteriores.
6. Probar el borrado de un recado propio.

Si falla /health, revisar Cosmos, variables y firewall. Si falla el login, revisar Client ID, secreto y callback exacto. El secreto del login va en App Service, no en secretos de Actions, salvo que un workflow independiente lo requiera explícitamente (este build no lo necesita).

## Referencias

- https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app
- https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps
- https://learn.microsoft.com/en-us/azure/app-service/deploy-ci-cd-custom-container
- https://learn.microsoft.com/en-us/azure/app-service/configure-custom-container
