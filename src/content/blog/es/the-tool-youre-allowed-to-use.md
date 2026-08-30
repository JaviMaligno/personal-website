---
title: "La herramienta que te dejan usar"
description: "Todos los consejos sobre trabajar con agentes dan por hecho que elegiste la herramienta. Mucha gente no. Qué cambia cuando la elección no es tuya — y qué argumento usar si lo es en parte."
pubDate: 2026-08-27
tags: ["IA", "Empresa", "Software", "Ingeniería", "Herramientas"]
lang: es
translationKey: the-tool-youre-allowed-to-use
heroImage: "/blog/the-tool-youre-allowed-to-use-es.png"
---

Todo lo que he escrito sobre trabajar con agentes — [el mapa](/es/blog/what-you-still-need-to-know-to-ship), [por dónde empezar](/es/blog/if-youre-starting-from-zero), [en qué se equivocan los ingenieros](/es/blog/if-you-came-from-engineering) — da por hecho algo que para mucha gente no es cierto: que elegiste tu herramienta.

Yo soy autónomo. Elijo lo que uso, lo cambio cuando aparece algo mejor, y el coste de equivocarme es mío. Esa es una posición poco común, y escribir como si fuera universal es un punto ciego que prefiero nombrar antes de que me lo señalen.

A mucha gente le dan una licencia de algo y le dicen que se apañe. Así que: qué cambia de verdad, y qué se puede hacer.

## Dos situaciones, y no son el mismo problema

**Tienes alguna influencia sobre qué se adopta.** Entonces esto es un problema de persuasión, y el argumento que funciona no es el que casi todo el mundo usa.

**No la tienes, ni la vas a tener.** Entonces es un problema de trabajo, y la mayoría de los consejos habituales hay que ajustarlos en vez de seguirlos.

## Si puedes influir: la objeción rara vez es el precio

Cuando una empresa no da el paso a un agente potente, el motivo declarado suele ser el coste. Casi nunca es el real. El real es que mandar código de la empresa o datos de clientes a un proveedor externo se siente inaceptable — y hasta hace poco ese instinto estaba bien fundado.

Los hechos se movieron y mucha gente no se ha actualizado. A día de hoy, en los dos proveedores que he comprobado directamente:

**Anthropic** declara que no entrena modelos con contenido de clientes de sus productos comerciales — la API, Claude for Work, Enterprise, Education. A los clientes comerciales se les dejó explícitamente fuera de los cambios de política de consumo. Las entradas y salidas de la API se borran de su backend en 30 días por defecto, y los clientes enterprise que califican pueden tener un acuerdo de retención cero, donde entradas y salidas no se almacenan más allá del filtrado antiabuso.

**OpenAI** declara que por defecto no usa datos de ChatGPT Enterprise, Business, Edu ni de la plataforma de API — ni entradas ni salidas — para entrenar o mejorar modelos. Entrenar con datos de empresa exige que el cliente lo active explícitamente. La retención cero está disponible para clientes enterprise que califican, en los endpoints soportados.

Dos cosas que conviene decir con precisión, porque sobrevender esto es como se pierde la discusión en la reunión:

**La retención cero no lo cubre todo.** En Anthropic aplica a las APIs de Messages y Token Counting, y explícitamente no a funciones con estado como Batch, la API de ficheros, los Managed Agents o la consola. "Tenemos retención cero" no es la misma frase que "no se guarda nada nunca".

**Por defecto no es lo mismo que garantizado.** Son compromisos contractuales y de política que pueden cambiar, y hacer cumplir las políticas de uso implica que algunas señales se retienen igualmente. Es un riesgo de proveedor normal, el mismo que ya aceptas con tu nube y con tu CRM — pero hay que defenderlo como riesgo gestionado, no como ausencia de riesgo.

El reencuadre útil para la conversación con quien dice que no: **tu empresa ya manda sus datos a terceros.** El correo, el control de versiones, la CI, el CRM, el sistema de errores. La pregunta nunca fue si confiar en un proveedor externo — es si las condiciones de este son aceptables, con el mismo criterio con el que evaluaste las de los otros. Eso es una conversación de compras, y tiene respuesta.

Hay un segundo argumento, y es el que aterriza en finanzas y no en seguridad: **las licencias que ya compraste están en su mayoría sin abrir.** Pagar por capacidad que nadie usa es el resultado caro, no el precio de la licencia.

## Si no puedes influir: qué cambia de verdad

Aquí piso terreno menos firme y prefiero decirlo. Mi experiencia reciente es con agentes potentes; lo que sé de trabajar con restricciones de verdad es de hace unos años, de cuando usar IA era pegar código en una ventana de chat y traerlo de vuelta — una versión en directo de Stack Overflow — o autocompletado donde seguías escribiendo tú. Las dos cosas han avanzado desde entonces, y estaría adivinando cuánto exactamente.

De lo que sí estoy razonablemente seguro es de la forma.

**Unidades de trabajo más pequeñas.** La mayor diferencia entre un agente potente y un asistente limitado es cuánto puedes entregarle de una vez. Si la herramienta pierde el hilo a los dos ficheros, la respuesta no es insistir: es darle trabajo del tamaño que le cabe. Eso no es una forma peor de operar; es la forma correcta de operar con esa herramienta.

**Más andamiaje, y lo construyes tú.** Con un agente potente tender vías es barato: instrucciones permanentes, ficheros de especificación, herramientas que puede ejecutar solo. Con menos, cargas tú con eso, en tu cabeza o en tu proceso. El trabajo no desaparece, se muda — hacia ti.

**Verificar sale más caro, lo que lo hace más importante.** El consejo que he dado en otro sitio — monta mecanismos para no comprobar a mano — vale igual. Pero si tu herramienta no puede ejecutar sus propios tests ni manejar un navegador, alguien tiene que montar eso. Sigue mereciendo la pena. Simplemente no sale gratis.

**El bucle sobrevive intacto.** Especificar, construir, comprobar, corregir. Nada de eso depende de qué herramienta tengas en la mano, y sigue siendo lo que separa a quien lanza cosas de quien tiene un historial de chat muy largo.

**El mapa también sobrevive intacto.** Las claves no van en el código, lo escriba quien lo escriba. Los datos siguen sin poder regenerarse. Las trece categorías van sobre el software, no sobre el asistente.

Así que el resumen honesto es: **el método se transfiere, el ritmo no.** Quien te diga que con una herramienta limitada los fundamentos son distintos te está vendiendo algo.

## La parte que no es justa

Se está abriendo una brecha real entre quien elige sus herramientas y quien las recibe, y no se corresponde en nada con el talento. Dos ingenieros de idéntica capacidad, uno con un agente potente y permiso para usarlo, otro con un asistente limitado y una política que le prohíbe pegar nada dentro, van a producir resultados visiblemente distintos en un trimestre. Y esa diferencia se va a leer como una diferencia entre ellos.

No tengo arreglo para eso, y desconfío de quien diga que lo tiene: la formación no cierra una brecha que es estructural y no educativa. Lo que sí le diría a quien está en el segundo grupo es más estrecho y creo que es cierto: **la parte de esto que es de verdad una habilidad es la que sí puedes construir.** Saber qué pedir, saber qué comprobar, saber qué categorías existen. Eso viaja contigo, incluido a tu siguiente trabajo, donde a lo mejor la decisión de herramientas la ha tomado mejor otra persona.

---

*Cuarta pieza sobre lo que construir software con agentes exige de verdad, y la que cuestiona una suposición que las tres primeras estaban haciendo. Las otras: [el mapa](/es/blog/what-you-still-need-to-know-to-ship), [empezar desde cero](/es/blog/if-youre-starting-from-zero), [venir de la ingeniería](/es/blog/if-you-came-from-engineering).*

*Fuentes de las políticas de proveedor, ambas consultadas el 2026-08-10: [Centro de privacidad de Anthropic sobre retención cero](https://privacy.claude.com/en/articles/8956058-i-have-a-zero-data-retention-agreement-with-anthropic-what-products-does-it-apply-to) y [OpenAI sobre privacidad de datos de empresa](https://openai.com/business-data/). Las políticas cambian — compruébalas tú antes de citarlas en una reunión.*
