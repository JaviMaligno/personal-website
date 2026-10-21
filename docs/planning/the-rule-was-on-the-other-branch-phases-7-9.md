# Fases 7–9 de la ejecución con Codex — notas para el artículo

Material para la sección «Live, and handed over» de
`src/content/blog/{en,es}/the-rule-was-on-the-other-branch.md`. Ya anonimizado:
sin ticket, empresa, servicio, nombres de campos, tenant, equipos ni identificadores
internos. Estado a 2026-10-21, ~17:30 UTC+1; la ejecución sigue parada desde entonces.

## Resumen

La ejecución **no llegó a las fases 8 ni 9**, y la 7 se quedó a medias: terminó una
primera pasada de QA en vivo, encontró un fallo, volvió sola a las fases 4–6 para
arreglarlo y se paró esperando a que el pipeline construyera la imagen corregida.

## Fase 6 (lo que se comprobó antes de la QA en vivo)

- Merge de la PR en la rama de integración y comprobación del linaje en esa rama.
- El build publicó la imagen con el nombre exacto esperado; se verificó el manifiesto
  y su digest en el log del build (no el veredicto del build).
- La subida de versión en el repositorio de configuración del entorno de pruebas se
  mergeó y el bucle esperó al despliegue sin tocar la imagen a mano.
- Las dos réplicas estaban listas con esa imagen exacta; el commit horneado en la
  imagen y el que expone el endpoint público de salud coincidían con el merge; el
  despliegue figuraba como sincronizado y sano.
- Un detalle honesto del log: la primera verificación comparaba un prefijo de 8
  caracteres contra el SHA de 7 que expone el build y dio un falso aviso; el bucle
  corrigió el verificador (prefijo de ≥7 caracteres del SHA completo + digest exacto)
  y dejó escrita la corrección en lugar de borrar la entrada anterior.

## Fase 7 — verificación en vivo en el entorno de pruebas

Primera pasada, punto por punto de la especificación:

- **Contrato publicado** (tres de los cinco puntos): pasan contra el Swagger que
  sirve el despliegue, que es byte a byte el YAML mergeado (hash guardado como evidencia).
- **La ruta rara (el caso del filtro de contenido)**: pasa con sondas deterministas
  ejecutadas sobre el módulo desplegado, en tres modos, incluido el bloqueo en la
  búsqueda de apertura. El bucle deja escrito que **no** midió un filtro de contenido
  real del proveedor: distingue la sonda determinista del tráfico HTTP normal.
- **Smoke HTTP real**: 200, pero el servicio se abstuvo al agotar su plazo de
  investigación, y el bucle lo registra explícitamente como «no es una prueba de
  acierto». Se observaron decenas de filas de fuentes y de entradas de traza.
  Una petición sin credenciales devuelve 401.
- **Limpieza de datos de prueba**: usó un tenant dedicado a esta QA; el script borra
  solo la caché de ese tenant y comprueba que queda en 0 (1 fila borrada, 0 restantes).
  La auditoría se conserva.
- **El fallo**: una comparación recursiva de la respuesta real contra el contrato
  publicado encontró **dos campos anidados que el servicio ya devolvía y el contrato
  no declaraba**. El PASS anterior de ese punto venía de fixtures; el bucle lo marcó
  como superado por el FAIL contra la respuesta real hasta arreglarlo.

### Vuelta a las fases 4–6 (el bucle de arreglo)

- Tests nuevos en rojo primero (3 fallos reproducidos), luego en verde (119 tests);
  revisión independiente aprobada sin bloqueos. Sin cambio de comportamiento: solo
  declara en el contrato lo que ya se emitía.
- Mientras tanto la rama de integración había avanzado con una PR ajena. El
  fast-forward protegido se paró; el bucle hizo un merge de prueba (limpio), integró
  con merge commit para no perder ese avance y repitió las pruebas sobre el resultado
  (146 tests, incluida la regresión del cambio ajeno).
- Reapuntó la PR de configuración del entorno de pruebas al nuevo SHA y archivó la
  evidencia de la primera pasada antes de repetirla.
- **Ahí se detuvo**: el build de la imagen corregida estaba en cola sin runner. La PR de
  configuración sigue sin mergear (por diseño: no se despliega lo que no tiene
  manifiesto verificado) y la segunda pasada de QA no se ha hecho.

## Fase 8 — traspaso

**No ocurrió.** Lo único que existe es la decisión registrada en la fase 6: la
promoción más allá del entorno de pruebas la hace otro equipo de la organización con
sus propios tickets de despliegue, y el entorno de pruebas es lo último que toca el
bucle. El despliegue del entorno siguiente sigue en la versión anterior. No hay
material de traspaso preparado todavía.

## Fase 9 — cierre

- **Ticket**: no verificado (sin acceso al gestor desde la sesión que escribe esto).
  El plan registrado era cerrarlo y devolverlo al responsable tras la QA en vivo, que
  no ha terminado.
- **Worktree**: sigue existiendo, en el SHA del merge corregido.
- **Ramas remotas**: siguen las tres de la tarea (la del cambio, la del arreglo en
  vivo y una de evidencia).
- **Pendiente de limpieza registrado**: solo la caché del tenant de QA, ya vacía.

## Cómo usarlo en el artículo

Dos opciones:

1. Esperar a que se reanude la ejecución (segunda pasada, traspaso y cierre).
2. Contarlo tal cual: la QA en vivo encontró dos omisiones que los fixtures no veían,
   y el bucle volvió solo a las fases 4–6, se adaptó a una rama de integración que se
   había movido y no desplegó sin manifiesto verificado. Probablemente es lo mejor de
   la sección. Mantener la misma anonimización que el resto del artículo.
