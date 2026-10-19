# Recados — Next.js + React y Python

Una web para iniciar sesión con Microsoft y guardar, consultar o borrar tus propias notas. Sube este proyecto a GitHub: los cambios enviados a `main` se despliegan automáticamente en Azure una vez realizada la configuración inicial.

## Tecnologías

- **Frontend:** Next.js y React, con JavaScript, HTML y CSS.
- **Backend:** Python con Flask; gestiona Microsoft, sesiones y API.
- **Base de datos:** Azure Cosmos DB. Los recados permanecen al actualizar la web.
- **Publicación:** Docker + Azure App Service + GitHub Actions.

Next.js genera los archivos del frontend durante la construcción de Docker (`output: 'export'`). Node.js se usa únicamente en esa etapa de construcción. El contenedor final ejecuta Python, que sirve el frontend y la API desde el mismo dominio. No hay servidor Node.js, funciones de backend de Next.js, SQLite ni base de datos local.

## Publicar desde GitHub con el workflow generado por Azure

**Este ZIP no incluye `.github/workflows` ni un YAML de despliegue.** Azure lo generará y lo agregará a tu repositorio cuando guardes la conexión desde el Centro de implementación de App Service.

1. Descomprimir el ZIP y subir **su contenido** a la raíz del repositorio GitHub. `Dockerfile` debe quedar en la raíz. No subir solamente el ZIP.
2. Si se había usado una entrega anterior, retirar su antiguo workflow de despliegue y confirmar ese cambio; copiar archivos nuevos no elimina los antiguos.
3. Seguir [docs/AZURE.md](docs/AZURE.md). El tutorial completo está en [docs/Tutorial.tex](docs/Tutorial.tex), con preámbulo y todas las secciones para compilarlo como documento independiente.
4. Crear ACR y construir una primera imagen con ACR Tasks; crear Cosmos DB y App Service para contenedor Linux; configurar Microsoft, redes y variables de ejecución.
5. En App Service > Centro de implementación, conectar **GitHub Actions**, seleccionar repositorio y rama `main`, elegir ACR y revisar que la vista previa construya el Dockerfile. Guardar: Azure agrega el workflow y las referencias de autenticación que correspondan a su plantilla.
6. En GitHub Desktop, descargar el commit creado por Azure con Fetch/Pull. Desde entonces, enviar cambios a `main` activa la automatización.

La guía usa una Web App de contenedor único clásico como recorrido de referencia. Incluye las diferencias y comprobaciones para una web existente con sidecars. Las opciones de autenticación dependen de la plantilla disponible: puede usar credenciales de ACR y perfil de publicación, o identidad/OIDC si esa integración lo ofrece. No copiar nombres de secretos del workflow anterior sin comprobar el archivo generado.

**GitHub guarda el código y ejecuta la automatización; Azure aloja la web y sus datos.** Subir el código no configura automáticamente la suscripción, los recursos ni el acceso con Microsoft. GitHub Pages no ejecuta este backend Python.

## Registro para iniciar sesión con Microsoft

En Microsoft Entra ID > Registros de aplicaciones > Nuevo registro:

1. Nombre: `Recados`. Seleccionar **Cuentas de cualquier directorio organizativo y cuentas personales de Microsoft**.
2. Plataforma **Web**, URI `https://TU-HOST-REAL/auth/callback`. Usa el dominio exacto que muestra App Service, incluidos sus sufijos.
3. Copiar el Id. de aplicación (cliente) a `MICROSOFT_CLIENT_ID` en App Service.
4. Certificados y secretos > Nuevo secreto de cliente. Copiar su **valor** a `MICROSOFT_CLIENT_SECRET`. Renovarlo antes del vencimiento.
5. Configurar `MICROSOFT_TENANT=common`, `APP_URL=https://TU-HOST-REAL` (sin barra final).
6. Añadir `https://TU-HOST-REAL/` a las URI admitidas para volver después de cerrar sesión si Microsoft lo requiere.

No activar flujo implícito. La aplicación no necesita acceder a tus correos ni a Microsoft Graph. MSAL solicita los ámbitos de identidad. Si tu organización exige autorización administrativa, su administrador debe habilitarla.

## Funcionamiento y seguridad

Cada cuenta tiene sus propios recados. Python obtiene la identidad de Microsoft del emisor y el sujeto, no del correo ni de un identificador enviado por el navegador. Cosmos almacena cada nota con la partición `/owner`. El frontend no recibe claves de Azure ni secretos Microsoft.

Las sesiones usan cookies firmadas HttpOnly, Secure y SameSite=Lax; expiran tras 8 horas de inactividad. Las solicitudes para crear y borrar requieren un token CSRF. El código usa MSAL para validar el flujo de acceso y no almacena los tokens de Microsoft en la cookie. React muestra el texto de las notas sin interpretar HTML. La política CSP autoriza mediante hashes los scripts inline que genera Next.js, sin habilitar scripts inline arbitrarios.

Al cerrar sesión se elimina la cookie del navegador actual. No existe invalidación central de una copia previamente robada de una cookie: para ese requisito habría que incorporar sesiones de servidor. Mantén secretos y cookies protegidos. Cambiar el registro de aplicación puede cambiar los identificadores de usuario y requerir una migración de propietarios.

La calculadora anterior se reemplaza por esta web. Sus sumas no se migran a notas porque no tenían cuentas asociadas. El despliegue actualiza la imagen web, sin eliminar Cosmos DB.

## API Python

| Método | Ruta | Función |
|---|---|---|
| GET | `/api/session` | Estado de acceso y token CSRF |
| GET | `/api/recados` | Notas del usuario actual |
| POST | `/api/recados` | Crear con JSON `{"body":"Mi nota"}` |
| DELETE | `/api/recados/{uuid}` | Borrar una nota propia |
| GET | `/auth/login` | Acceso con Microsoft |
| GET | `/auth/callback` | Retorno de Microsoft |
| POST | `/auth/logout` | Cerrar sesión |
| GET | `/health` | Estado de conexión con Cosmos |

Las notas admiten entre 1 y 2000 caracteres. La creación y el borrado necesitan `X-CSRF-Token`; el formulario de cierre de sesión envía ese token como campo.

## Comprobaciones para desarrollo

Estos comandos son opcionales para revisar el código y no requieren credenciales reales: las pruebas usan dobles de almacenamiento y de Microsoft. La plantilla que genere Azure puede no incluir pruebas unitarias; no asumir que las ejecuta si no aparecen en su YAML.

```text
pip install -r requirements.txt
python -m unittest discover -s tests -v
cd frontend
npm ci
npm run build
```

El Dockerfile construye Next.js e instala Python automáticamente. No subas `node_modules`, `.next`, `out`, `.env` ni secretos a GitHub. El build no usa credenciales; solo la aplicación publicada las necesita.

Guía técnica de exportación estática: https://nextjs.org/docs/app/guides/static-exports
