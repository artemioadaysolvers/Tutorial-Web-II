# Publicar con el workflow generado por Azure

El tutorial completo de esta entrega está en **Tutorial.tex**. Es un documento LaTeX independiente con preámbulo, índice y pasos numerados. No hay workflow incluido en el ZIP: Azure debe crearlo al conectar el repositorio.

## Orden de configuración

1. Crear o reutilizar un repositorio GitHub y subir los archivos descomprimidos a su raíz, con Dockerfile en la primera lista de archivos. La rama de publicación será main.
2. Retirar el antiguo workflow de la calculadora o del ZIP previo si ya estaba en el repositorio. No borrar workflows ajenos a este despliegue.
3. Crear grupo de recursos y Azure Container Registry, revisar su costo y copiar su login server real.
4. Construir la imagen inicial con ACR Tasks desde Cloud Shell. Esto evita necesitar Docker en el computador:

```bash
az account set --subscription "TU_ID_DE_SUSCRIPCION"
az acr build --registry "TU_NOMBRE_DE_ACR" --image "recados:inicial" --file "Dockerfile" "https://github.com/TU_USUARIO/TU_REPOSITORIO.git#main"
```

La URL debe ser pública para ese comando sin credenciales. Para repositorios privados, subir el ZIP a Cloud Shell, descomprimirlo, entrar en la carpeta del Dockerfile y usar `az acr build --registry "TU_NOMBRE_DE_ACR" --image "recados:inicial" --file "Dockerfile" .`. El tutorial explica ambos recorridos y las restricciones de cuotas.

5. Crear Cosmos DB for NoSQL con base RecadosDB, contenedor recados y partición **/owner**. El contenedor sumas de la calculadora no corresponde a este proyecto.
6. Crear App Service Linux para **contenedor**, con plan compatible (por ejemplo B1 si está disponible), imagen recados:inicial y comando de inicio vacío. El recorrido principal del tutorial usa contenedor único clásico; allí configurar WEBSITES_PORT=8080. Revisar las indicaciones específicas del tutorial si la web existente usa sidecars.
7. Configurar redes de Cosmos para permitir las IP de salida necesarias de App Service.
8. Registrar recados-login en Entra con cuentas organizativas y personales; plataforma Web y retorno `https://TU_DOMINIO_REAL/auth/callback`.
9. Configurar en App Service las variables siguientes:

| Variable | Valor |
|---|---|
| SECRET_KEY | Cadena aleatoria estable de al menos 32 caracteres |
| APP_URL | URL HTTPS pública exacta, sin barra final |
| MICROSOFT_CLIENT_ID | Id. de cliente del registro de login |
| MICROSOFT_CLIENT_SECRET | Valor del secreto de ese registro |
| MICROSOFT_TENANT | common |
| COSMOS_ENDPOINT | URI de Cosmos |
| COSMOS_KEY | Clave de lectura y escritura |
| COSMOS_DATABASE | RecadosDB |
| COSMOS_CONTAINER | recados |
| WEBSITES_PORT | 8080 para contenedor clásico |

Generar una clave aleatoria en Cloud Shell con `python3 -c "import secrets; print(secrets.token_hex(32))"`. Mantener la clave estable. Habilitar HTTPS; dejar Easy Auth desactivado porque Python gestiona el login. El backend no utiliza SQLite ni las variables DB_BACKEND, SQLITE_PATH o TRUST_PROXY_HEADERS.

## Generar el workflow desde Azure

10. Abrir App Service > Centro de implementación > Configuración. Seleccionar **GitHub Actions** como origen del código, autorizar GitHub y elegir propietario, repositorio y main.
11. Elegir ACR y el repositorio recados; completar la autenticación solicitada. Para la plantilla de contenedores basada en credenciales, el portal puede requerir Admin user de ACR y SCM Basic Auth Publishing Credentials para el perfil de publicación. Si ofrece una variante de identidad/OIDC, aplicar sus permisos; no mezclar ambos métodos.
12. Abrir la vista previa. Debe construir el Dockerfile de la raíz, publicar la imagen y actualizar el contenedor. Una plantilla que solo publica código Python no sirve para esta estructura.
13. Guardar. Azure deposita el archivo en `.github/workflows/` y configura las referencias de secretos de su plantilla. No inventar nombres ni añadir manualmente los secretos del pipeline anterior salvo que el archivo real los use.
14. Confirmar en GitHub el commit de Azure, el nuevo workflow y la primera ejecución. Descargar ese commit en GitHub Desktop con Fetch/Pull.
15. Verificar la web, /health, login, creación, persistencia después de cerrar sesión, aislamiento entre dos cuentas y borrado.

## Actualizaciones

Editar, confirmar y enviar cambios a la rama configurada. Guardar un archivo local sin enviarlo a GitHub no publica la web. No repetir la construcción inicial, crear recursos ni regenerar el workflow para cada edición. Los datos permanecen en Cosmos.

La plantilla de Azure puede no ejecutar las pruebas unitarias ni comprobar /health: revisar el YAML real. No se ha conectado ninguna cuenta ni realizado un despliegue al preparar esta entrega.

## Referencias

- https://learn.microsoft.com/en-us/azure/app-service/deploy-ci-cd-custom-container
- https://learn.microsoft.com/en-us/azure/app-service/deploy-github-actions
- https://learn.microsoft.com/en-us/azure/container-registry/container-registry-tutorial-quick-task
- https://learn.microsoft.com/en-us/azure/app-service/configure-custom-container
