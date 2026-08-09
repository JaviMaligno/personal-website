# Taller de equipo — guion de facilitación

Date: 2026-08-06
Estado: v1, sin entregar todavía. La primera entrega es la que produce el único
caso, así que se prepara antes y se ajusta después con lo aprendido.

Producto descrito en
[`2026-08-04-mentoring-page-design.md`](../superpowers/specs/2026-08-04-mentoring-page-design.md).
Sistema en
[`2026-08-02-vibe-coding-skills-series-design.md`](../superpowers/specs/2026-08-02-vibe-coding-skills-series-design.md).

## Qué se vende y qué se entrega

**La promesa:** el equipo sale con el mapa de su propio proyecto — qué casillas
están vacías, quién cubre cada una, y qué se cubre primero. Un diagnóstico, no un
curso.

**Formato base:** día completo online, grupo entero, hasta 8 personas.
**Versión reducida:** media jornada, solo diagnóstico y plan, sin práctica.

**Decisiones de diseño ya tomadas:**

1. **Se trabaja sobre un proyecto común del equipo**, no uno por persona. El que
   firma quiere saber el riesgo de lo que su gente ha construido; el mapa por
   proyecto responde a eso. El vector individual sale como subproducto y cada
   uno se lo lleva.
2. **Día completo es el producto**, porque es lo que permite practicar el bucle
   en vivo. Media jornada diagnostica pero no cambia hábitos.
3. **La preparación previa es obligatoria.** Sin ella el primer tercio se va en
   averiguar qué han construido, que es justo lo que en el mercado se cobra como
   "preparación incluida".

## La regla que sostiene todo lo demás: el facilitador no toca el teclado

El riesgo real de este taller no es quedarse corto de contenido. Es que se
convierta en **Javi resolviéndoles los problemas técnicos**, con el equipo
mirando. Si eso pasa:

- no aprenden nada, porque la sesión la ejecuta otro;
- el producto deja de ser un diagnóstico y pasa a ser consultoría regalada;
- y el posicionamiento se invierte: pasas a ser el técnico que arregla cosas, no
  quien enseña a que no vuelvan a pasar.

**Regla: teclean ellos, siempre.** También cuando sea más lento, también cuando
la solución sea obvia, también si aparece algo urgente. Se dirige, se pregunta,
se señala dónde mirar. No se toca su proyecto.

Corolario que además demuestra el método: cuando alguien pregunta *"¿y cómo se
hace esto?"*, la respuesta no es la solución — es **"pregúntaselo al agente y
vemos qué contesta"**. Eso es literalmente el nivel *con soltura* del sistema, y
verlo funcionar en vivo vale más que explicarlo.

## Antes: el cuestionario previo

Se envía al contacto con una semana de margen. Respuestas cortas; el objetivo no
es un documento, es no llegar a ciegas.

```text
Sobre lo que habéis construido

1. ¿Qué es y para qué sirve? Dos frases.
2. ¿Quién lo usa hoy? ¿Sólo vosotros, otros equipos, clientes?
3. ¿Con qué lo habéis construido? (Claude Code, Codex, Cursor, Copilot,
   ChatGPT, una plataforma no-code…)
4. ¿Dónde está funcionando? ¿En un portátil, en algún servicio, no lo sabéis?
5. ¿Guarda datos? ¿De qué tipo, y de quién?
6. ¿Hay alguien técnico que lo haya mirado en algún momento?
7. ¿Qué es lo que más miedo os da de esto? Una frase, sin filtrar.
```

La 7 es la más útil de las siete. Suele señalar la casilla por la que empezar, y
da la primera frase con la que abrir el taller.

**Antes del día:** rellenar el mapa en borrador con lo que se deduzca de las
respuestas. No se comparte — sirve para saber dónde va a doler y para no
improvisar el recorrido.

## Agenda — día completo (6 h con descansos)

### 1. Apertura — 30 min

Qué es esto y qué no. **No es un curso de programación**, y decirlo en voz alta
descoloca al que venía a defenderse.

Se presenta el bucle: especificar → construir → comprobar → corregir. Y el punto
que lo justifica: el agente está en las cuatro fases, pero dos dejan residuo
humano y dos no. Construir y corregir se delegan enteras; especificar y
comprobar, no.

Se abre con su propia respuesta a la pregunta 7 del cuestionario.

### 2. El bucle en vivo — 60 min

Ejercicio, no demostración. Piden un cambio pequeño y real sobre su propio
proyecto, y se les obliga a **usarlo antes de pedir el siguiente**.

Lo que hay que conseguir que noten: cuántas veces habrían seguido pidiendo sin
comprobar, y que comprobar cuesta diez segundos.

Si el equipo no tiene un entorno donde tocar sin miedo, esto se convierte en el
primer hallazgo del día y se anota en el mapa (categoría *dónde vive*).

*Descanso 15 min.*

### 3. El mapa, recorrido por familias — 75 min

**No es una clase sobre las trece categorías.** Es un interrogatorio a su
proyecto, familia por familia, rellenando el mapa en pantalla mientras se habla.

Por cada familia, se hace la pregunta en cristiano y se busca la respuesta en
vivo:

| Familia | La pregunta que se hace en la sala |
|---|---|
| El techo | ¿Qué le habéis pedido y qué habéis dado por imposible sin preguntar? |
| Dónde está y cómo se recupera | Si esto se borrase esta noche, ¿qué vuelve y qué no? ¿Dónde está la copia? |
| Quién sale herido | ¿Dónde están vuestras claves ahora mismo? ¿Puede alguien leer los datos sin pasar por el login? |
| Qué os va a sorprender | ¿Cuánto costó el mes pasado? ¿De qué servicios ajenos dependéis? |
| Cómo sabéis que sigue bien | ¿Cómo os enteraríais de que algo se ha roto? |

**Regla de facilitación:** cuando nadie sabe responder, eso *es* el resultado. No
se rescata al equipo con la respuesta genérica — se anota la casilla como vacía y
se sigue. La incomodidad de no saber es el mecanismo de aprendizaje del día.

*Comida / descanso largo.*

### 4. Cerrar dos agujeros — 60 min

Se eligen dos o tres casillas y **las cierran ellos en vivo**, con su agente,
empezando siempre por la familia "quién sale herido". Salir con algo arreglado y
no solo diagnosticado es lo que convierte el taller en algo que se recomienda —
pero solo si lo han arreglado ellos. Si lo arregla el facilitador, el equipo sale
con el problema resuelto y sin haber aprendido a resolverlo, que es el peor de
los dos resultados posibles.

Candidatas habituales, por orden de qué suele estar peor:

- una clave que está en el código → sacarla, y explicar que además hay que
  sustituirla porque sigue en el historial;
- ninguna copia de seguridad → montar una y **restaurarla** para comprobar que
  sirve;
- un endpoint que responde sin autenticación → cerrarlo y comprobarlo.

### 5. Verificación que no dependa de vosotros — 45 min

El bloque que sostiene todo lo demás a medio plazo. Se monta **un** mecanismo, en
vivo, sobre lo que más miedo les dé:

- pedirle al agente un test de ese comportamiento, descrito en palabras —
  *"alguien que no ha iniciado sesión no recibe nada de aquí"*;
- verlo fallar a propósito, para que el test signifique algo;
- pedir la prueba en vez de la afirmación: que devuelva una captura de la cosa
  funcionando, no un "ya está".

Aquí se dice explícitamente lo que queda humano: **la sospecha, no la
inspección.**

### 6. El plan — 30 min

Se cierra el mapa con dos columnas que son el verdadero entregable: **quién
comprueba cada casilla** y **qué se hace en las próximas cuatro semanas**.

Nada de trece acciones. Tres, con nombre y fecha.

## Agenda — media jornada (3 h)

Apertura (20) → mapa por familias (90) → cerrar un agujero (40) → plan (30).

Se cae la práctica del bucle y el bloque de verificación. Hay que decirlo al
vender: diagnostica, pero no cambia hábitos.

## El entregable

Se envía en 48 h. Un documento corto, no una presentación.

```text
MAPA — <equipo / proyecto>              <fecha>

| Categoría                  | Nivel | Quién lo comprueba | Prioridad |
|----------------------------|-------|--------------------|-----------|
| Qué se puede pedir         |       |                    |           |
| Dónde vive                 |       |                    |           |
| Código y datos             |       |                    |           |
| Volver atrás               |       |                    |           |
| Secretos                   |       |                    |           |
| Quién puede entrar         |       |                    |           |
| Datos de otras personas    |       |                    |           |
| Lo que cuesta              |       |                    |           |
| De quién dependes          |       |                    |           |
| Aguantar carga             |       |                    |           |
| Tests y fallos             |       |                    |           |
| Seis meses después         |       |                    |           |
| Criterio propio            |       |                    |           |

Nivel: no lo sabíamos / conscientes / con soltura / con criterio
Quién lo comprueba: una persona, un test, un servicio, o NADIE

ARREGLADO EN EL TALLER
- …

LAS TRES PRÓXIMAS CUATRO SEMANAS
1. <qué>  — <quién> — <fecha>
2. …
3. …

CASILLAS QUE SIGUEN VACÍAS Y LO SABÉIS
- …
```

La última sección es la que más valor tiene y la más fácil de omitir por quedar
bien. Una casilla vacía que el equipo conoce es un riesgo gestionado; el
documento tiene que dejarlas por escrito.

## Notas de facilitación

**Si el equipo se pone a la defensiva.** Suele pasar en la familia "quién sale
herido". Se corta con lo mismo que dice el artículo: nadie les dijo que esas
categorías existían, y el agente no las menciona por su cuenta. El fallo es de
formación, no de cabeza.

**Si aparece algo grave en vivo** — una clave de producción expuesta, datos de
clientes accesibles. Se para el recorrido y se arregla en ese momento; un taller
que descubre una fuga y sigue con el guion como si nada no vuelve a venderse.
Pero **lo arreglan ellos igualmente**, dirigidos paso a paso. La urgencia es la
excusa más tentadora para saltarse la regla del teclado, y es justo cuando más
caro sale: el equipo se queda con la sensación de que estas cosas las arregla
alguien de fuera.

**Si hay alguien técnico en la sala.** Es un aliado, no un obstáculo: normalmente
es quien hereda el problema. Conviene darle un papel explícito — que sea quien
compruebe en vivo — en lugar de dejar que corrija desde el fondo.

**Si nadie tiene permisos** para tocar nada de lo que hace falta. Ocurre en
empresas medianas. Se anota y se convierte en la primera acción del plan: sin
permisos no hay bucle.

## Pendientes antes de la primera entrega

- **Traducir el cuestionario y el entregable al inglés**, que es el mercado
  principal. El guion puede seguir en español, es de uso interno.
- **Decidir la herramienta de pizarra** para rellenar el mapa en pantalla y que
  todos lo vean.
- **Probar los tiempos** con alguien de confianza antes de cobrarlo. Los bloques
  están estimados, no medidos. Criterio acordado mientras tanto: los tiempos
  dependen mucho del caso, así que se ajustan sobre la marcha y **lo que no cabe
  se convierte en follow-up**, no en prisa. Vale más cerrar bien dos casillas que
  recorrer trece de pasada.
- **Probar el orden en las dos variantes.** El guion practica el bucle antes de
  diagnosticar, para que la evaluación se apoye en algo que acaba de pasar. La
  alternativa — diagnosticar primero y practicar después sobre un agujero real —
  no está descartada; hay que verla en vivo antes de decidir.
- **Preparar el caso del equipo que no tiene nada construido todavía** — quiere
  empezar bien. El mapa sigue sirviendo, pero el recorrido cambia: se pregunta en
  futuro y el entregable es una lista de guardas por poner, no de agujeros por
  tapar.
