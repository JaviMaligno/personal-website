# Dos regímenes de memoria: la personal y la que escribe un modelo solo

Fecha: 2026-09-11
Estado: diseño aprobado en brainstorming, pendiente de plan de implementación
Artículo previo: [`make-yourself-replaceable`](../../../src/content/blog/es/make-yourself-replaceable.md) (publicación programada 2026-09-19)

## Origen

El artículo 1 cierra con una pregunta abierta —dónde vive cada tipo de contexto— y
promete que hay "bastante ingeniería detrás, suficiente para otro artículo". Este
documento define ese artículo 2.

El encuadre cambió dos veces durante el brainstorming, y las dos veces por una
objeción del autor que conviene dejar escrita, porque delimita el alcance:

1. **"Esta versión rudimentaria es algo que Claude Code ya hace en gran medida."**
   Cierto. Carpeta por proyecto, un archivo por idea, frontmatter tipado, índice
   cargado por sesión, recuperación por relevancia y enlaces entre memorias ya
   existen. Añadir un campo de visibilidad y versionarlo en git es configuración,
   no ingeniería, y no puede presentarse como contribución.

2. **"La mitad no comprobable es la realmente interesante, y ya se maneja bien."**
   También cierto, y afina la tesis (§2).

El resultado es que el artículo **no construye un sistema nuevo**. Compara dos que
ya funcionan y mide uno de ellos.

## 1. Tesis

El autor opera hoy dos sistemas de memoria con decisiones de diseño opuestas:

- **Régimen personal**: la memoria de Claude Code en sus repos. La escribe el
  agente al cerrar sesión, bajo supervisión humana, a partir de conversaciones en
  las que el autor estuvo presente.
- **Régimen de producción**: el sistema de conocimiento de un bot interno de
  DevOps. Lo escribe un modelo pequeño después de cada respuesta, sin supervisión,
  a partir de interacciones con terceros que el autor nunca ha leído.

La tesis: **la diferencia entre ambos no es sofisticación, es quién escribe y con
cuánta supervisión.** Cuando escribes tú, la confianza sale gratis y por eso la
experiencia es ligera. Cuando escribe un modelo solo, a partir de material que
nadie revisa, hay que construir toda la maquinaria de la confianza —promoción por
evidencia repetida, detección de contradicción, olvido, medición de utilidad— y sin
ella el sistema se degrada solo.

Corolario que evita el error de bulto: **portar la maquinaria del régimen de
producción al personal es overkill**, y es exactamente lo que este diseño estuvo a
punto de proponer antes de que el autor lo parara.

## 2. Qué envejece y qué no

Distinción central, y criterio de diseño más que limitación:

- **Una preferencia no se vuelve falsa sola.** Cambia cuando la persona cambia de
  opinión, y entonces lo dice. Es la mitad que hace agradable el trabajo diario y
  la que Claude Code ya maneja bien. No necesita verificación mecánica.
- **Un hecho sobre el sistema caduca solo, en silencio**, porque el mundo se mueve
  sin avisar a nadie. Esta es la única mitad sobre la que tiene sentido construir
  comprobación.

## 3. Evidencia ya recogida

Durante el propio brainstorming apareció el caso que sostiene el artículo.

La memoria personal `project_blog_publishing_mechanism` (fechada 2026-07-30)
afirma que programar un artículo consiste en crear un workflow de un solo uso
`scheduled-publish-<slug>.yml`. Ese mecanismo fue sustituido por el manifiesto
`.github/publish-schedule.json`, y en `main` quedan **cero** workflows de ese tipo.

Tres detalles que hacen el caso:

- La memoria **no se equivocó**: fue cierta y dejó de serlo mientras nadie miraba.
- Se sirvió como contexto al arrancar la sesión del 2026-09-11, ya obsoleta.
- El `CLAUDE.md` del repositorio repite el mismo error, así que no es un fallo del
  sistema de memoria sino de todo lo que se escribe una vez y no se revisa.

No guió mal por casualidad: el agente fue a leer el archivo real antes de programar.
De haberse fiado de la memoria, habría creado un workflow del mecanismo antiguo.

## 4. Lo único que se construye: la auditoría

Alcance deliberadamente pequeño. Es lo que da el dato que sostiene la tesis.

### 4.1 Entrada

Las **35 memorias** del proyecto `personal-website`, más el índice `MEMORY.md`
(36 archivos en total): 12 `feedback`, 18 `project`, 3 `reference` y 2 que no
declaran tipo —`feedback_test_in_browser` y `project_vitamind_integration`—, lo
cual ya es un hallazgo menor: el propio formato se aplica de forma desigual.

### 4.2 Paso previo

Las memorias no llevan comprobación. Un agente recorre cada una y **propone** una
cuando la admite; el autor revisa. Son 35 archivos, es acotado, y la revisión
humana es parte del experimento: mide cuántas admiten comprobación sin forzarla.

### 4.3 Vocabulario de comprobación

Declarativo e interpretado por el verificador, **nunca por la shell**. Un comando
arbitrario dentro de un archivo que redacta un agente es ejecución arbitraria; se
descarta por eso, no por complejidad.

Las comprobaciones viven en `scripts/memory-audit/checks.json`, **dentro del
repositorio**, indexadas por nombre de memoria. No en el frontmatter de la memoria:
se intentó así y el parser de YAML a mano resultó ser la causa común de casi todos
los fallos encontrados en revisión. La consecuencia importante es que el verificador
**no lee nunca el cuerpo de una memoria** —recibe solo la lista de nombres—, así que
la privacidad de §6 es una propiedad del diseño y no depende de sanear el informe.

```json
{
  "memories": {
    "project_blog_publishing_mechanism": {
      "checks": [{ "file_matches": ".github/workflows/scheduled-publish-*.yml" }]
    }
  }
}
```

Vocabulario: `file_exists`, `file_matches` (al menos uno casa), `file_absent`
(ninguno casa), `file_contains` y `date_passed`.

**Principio de polaridad.** Una comprobación codifica *lo que la memoria afirma*,
no el estado actual del mundo. Es el error más fácil de cometer y el más difícil de
ver: las primeras comprobaciones que se escribieron describían el mecanismo nuevo,
pasaban trivialmente y salían verdes. **Una comprobación que siempre pasa es peor
que ninguna**, porque da confianza falsa. Prueba antes de añadir una entrada: escriba
qué hecho la pondría roja, y descártela si ese hecho podría ocurrir sin que la memoria
dejase de ser cierta.

Lo que no se deje expresar así queda como pregunta de revalidación en texto libre,
marcada explícitamente como no determinista, para no confundir una comprobación con
una opinión.

**Un verde certifica lo codificado, no la memoria entera.** Una memoria puede salir
verde porque los ficheros que nombra existen y contener a la vez una afirmación
caducada que ninguna comprobación toca. El artículo tiene que decirlo: si no, vende
la herramienta como algo que no es.

### 4.4 Salida

Cada memoria cae en un montón:

| estado | significado |
|---|---|
| **verde** | la comprobación pasa: sigue siendo cierta |
| **rojo** | la comprobación falla: afirma algo que ya no es verdad |
| **gris** | no admite comprobación, y está bien que así sea |

El resultado publicable es el reparto de los tres montones y, sobre todo, cuántas
rojas aparecen. Llevamos una confirmada antes de empezar.

**Predicción a registrar antes de correr la auditoría** (para que el resultado
signifique algo): el montón gris será el mayor, y el rojo será pequeño pero no
cero. Si el rojo sale en cero, la tesis se debilita y hay que decirlo.

## 5. Lo que NO se construye

- **Vigencia activa en el repo personal.** Overkill reconocido. La web es un
  proyecto de una sola persona: no hay a quién traspasar nada, y el coste no se
  justifica.
- **Campo de visibilidad y filtros de publicación.** Sin nadie con quien compartir,
  resuelve un problema que aquí no existe. Pasa a trabajo futuro.
- **Cualquier reimplementación de lo que ya hace el régimen de producción.**

## 6. Anonimización

El repositorio del blog es público y el material de referencia es de trabajo. La
anonimización es parte del trabajo, no un repaso final.

Fuera de la spec, del artículo y de cualquier figura:

- nombres de compañeros y de clientes;
- nombres de servicios de cliente y de productos internos;
- hostnames, nombres de cluster, rutas de infraestructura y cadenas de conexión;
- el nombre del bot y el de la empresa;
- ejemplos de hechos almacenados que contengan cualquiera de los anteriores.

Lo que sí puede publicarse: las decisiones de diseño (umbrales, estados, ciclo de
mantenimiento), porque son el contenido técnico y no identifican a nadie. Los
ejemplos se reescriben con un dominio inventado y equivalente.

## 7. Estructura tentativa del artículo

1. La pregunta que dejó abierta el artículo anterior.
2. Los dos regímenes, descritos por lo que hacen distinto.
3. Qué envejece solo y qué no (§2).
4. El caso real: una memoria que fue cierta (§3).
5. La auditoría y sus tres montones (§4).
6. Por qué el régimen personal no debe parecerse al de producción.
7. Lo que aparece solo cuando hay equipo, como trabajo en curso.

Elementos visuales, calibrados con los artículos publicados del blog: la tabla
comparativa de los dos regímenes, el bloque de comprobaciones, el reparto de los
tres montones y negritas de remate. Sin muro de párrafos: fue la crítica explícita
al borrador del artículo 1.

## 8. Riesgos

- **Que la auditoría salga en verde.** Se publica igual, con la predicción fallada
  a la vista. Un resultado negativo honesto sigue siendo el artículo.
- **Que la comparación se lea como publicidad del sistema de producción.** Se
  mitiga publicando también lo que ese sistema hace mal o no resuelve.
- **Fuga de material de trabajo.** Ver §6. Es el riesgo más serio y el único que no
  admite corrección después de publicar.

## 9. Trabajo futuro

Compartir memoria entre personas —visibilidad, permisos y mantener lo vigente
cuando el archivo no tiene dueño— queda fuera. El autor está trabajando en ello;
no es algo resuelto, y el artículo lo presenta como tal, sin fingir un problema de
equipo que el proyecto personal no tiene.
