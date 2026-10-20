# Validación de Typewriter

## Configuración conservada

- Dockerfile, store.py, requirements.txt, frontend/package.json, frontend/package-lock.json, frontend/next.config.mjs y workflow de Azure conservados del ZIP original.
- Mismos nombres de variables de entorno, puerto 8080, login GitHub, CSRF, rutas /api/session y /api/recados, respuestas recado/recados y campos id/owner/body/created.
- Misma base y contenedor Cosmos: no se requiere migración. Los textos anteriores siguen disponibles para su propietario.
- El backend solo cambia la redacción de errores y conserva los espacios y saltos de línea al guardar. El límite sigue siendo 2000 caracteres e incluye los espacios.

## Comprobar después de subir

1. Comprueba que GitHub Actions termina correctamente.
2. Visita la web existente y prueba escribir sin iniciar sesión.
3. Pulsa Sonido y comprueba que activa y silencia los dos WAV.
4. Prueba una tecla en el editor y un botón. El sonido depende también del volumen y permisos de reproducción del navegador.
5. Guarda un texto, completa el acceso GitHub habitual y pulsa Guardar texto al volver.
6. Recarga: el texto aparece en Mis textos. Ábrelo y confirma que conserva espacios y saltos.
7. Modifica el texto y pulsa Guardar copia: aparecen ambos textos.
8. Comprueba Descargar .txt y Nueva hoja.
9. Accede con otra cuenta: solo debe mostrar los textos de esa cuenta.
10. Prueba Borrar con un texto de prueba.

Las pruebas locales no modifican tu Cosmos ni tu Azure. La comprobación real de OAuth, secretos de GitHub Actions y conectividad de Cosmos se realiza en el despliegue existente.

## Resultado de la verificación local

- TypeScript: comprobación correcta.
- Next.js: compilación de producción y exportación estática correctas con las versiones originales del package-lock.json.
- Servidor: 22 pruebas correctas, incluida la entrega de la exportación Next.js y la política CSP.
- Navegador: escritura, guardado, recarga, reapertura y Ctrl+S para guardar una copia comprobados en una sesión de prueba local; sin errores de consola.
- Sonidos: archivos originales comprobados por hash y servidos correctamente por Flask; el editor solicita teclado.wav al pulsar teclas y boton.wav al pulsar controles.
- Integridad: Dockerfile, store.py, requirements.txt, dependencias, configuración Next.js/TypeScript y workflow Azure coinciden con el ZIP original.

No se efectuó un despliegue en Azure ni se utilizaron credenciales reales de GitHub o Cosmos DB.
