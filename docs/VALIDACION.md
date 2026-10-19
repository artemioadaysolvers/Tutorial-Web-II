# Validación

Se completó la construcción de Next.js y pasaron las 20 pruebas Python, incluyendo la entrega del frontend y sus hashes CSP, OAuth con state y PKCE, expiración, cancelación, rechazo de respuestas inválidas, errores de red, CSRF y aislamiento de recados.

Se reutilizaron dependencias locales de las mismas versiones del proyecto. El ZIP no incluye dependencias instaladas ni archivos compilados: Docker los construye.

No se ejecutó Docker (no disponible en este equipo), ni un despliegue real en Azure, ni una autorización con credenciales reales de GitHub. Las pruebas OAuth y Cosmos utilizan respuestas simuladas. La comprobación real requiere configurar la OAuth App y las variables de App Service conforme a docs/AZURE.md.
