# memory-audit

Auditor de vigencia de memorias: dice cuáles de las memorias del agente siguen
siendo ciertas y cuáles afirman algo que el repositorio ya contradice.

```bash
node scripts/memory-audit/audit.mjs \
  --memory-dir ~/.claude/projects/<proyecto>/memory \
  --repo-root . \
  [--checks scripts/memory-audit/checks.json]
```

El auditor **no lee nunca el cuerpo de una memoria**. Sólo recibe los NOMBRES
de los ficheros del directorio de memorias y busca sus comprobaciones en
`checks.json`, que vive en este repositorio. Las memorias son privadas y este
repositorio es público: por aquí no puede escaparse el contenido de ninguna.

## Estados

| Estado | Significado |
| --- | --- |
| **verde** | todas sus comprobaciones pasan: lo que afirma sigue siendo cierto |
| **rojo** | alguna comprobación falla: afirma algo que ya no es cierto |
| **gris** | no tiene comprobaciones. Es el estado correcto para criterios, preferencias y acuerdos con personas: no hay nada en el repositorio que pueda contradecirlos |
| **error** | la comprobación es ilegible o no se puede evaluar |

**Regla de oro: si no se puede saber si algo es cierto, el estado es `error`,
nunca verde ni rojo.** Un falso verde deja pasar una memoria caducada; un falso
rojo acusa a una memoria sana. Por eso basta con que una sola comprobación de
una memoria no se pueda evaluar para que toda la memoria salga en `error`,
aunque otra haya fallado limpiamente: con una comprobación ciega ya no se puede
afirmar ni que está viva ni que está muerta.

## Vocabulario de verbos

Vocabulario cerrado, interpretado por `checks.mjs`. **Nunca se ejecuta shell.**

| Verbo | Qué afirma |
| --- | --- |
| `{"file_exists": "ruta"}` | esa ruta exacta existe. No admite comodines |
| `{"file_matches": "dir/patron*"}` | existe **al menos un** fichero que casa con el patrón |
| `{"file_absent": "dir/patron*"}` | **no** existe ninguno que case. Complemento exacto del anterior |
| `{"file_contains": {"path": "ruta", "text": "..."}}` | ese fichero sigue conteniendo ese texto |
| `{"date_passed": "AAAA-MM-DD"}` | esa fecha ya pasó |

Reglas de forma que el cargador y el ejecutor aplican igual:

- el glob sólo entiende `*` y sólo en el **último** segmento; la interrogación
  es un carácter literal;
- las rutas se resuelven contra `--repo-root` y no pueden salir de él;
- las comparaciones **distinguen mayúsculas y minúsculas** en los cuatro verbos
  de fichero, también sobre APFS o NTFS, que no las distinguen: la caja se
  comprueba contra el nombre real de la entrada en el listado de su directorio,
  para que el veredicto no dependa del sistema de ficheros;
- se rechazan las comprobaciones tautológicas (ver abajo);
- `date_passed` exige `AAAA-MM-DD` real y compara contra la fecha del
  **calendario local**, no contra UTC.

## Códigos de salida

| Código | Cuándo |
| --- | --- |
| `0` | ninguna memoria roja ni con error, ninguna comprobación huérfana y ningún problema de `checks.json` |
| `1` | al menos una memoria roja, una memoria con error, una comprobación huérfana (su memoria se renombró o se borró, así que ya no vigila nada) o un problema de `checks.json` que deja alguna comprobación sin aplicar |
| `2` | error de invocación: falta un argumento, la raíz del repositorio no existe / no es un directorio / no parece una raíz (no contiene `.git`), o el directorio de memorias o el fichero de comprobaciones no se pueden usar. Con `2` no se imprime informe |

Una comprobación huérfana cuenta como problema y no como un `0`: basta
renombrar una memoria para que su comprobación deje de vigilar nada y la
memoria caiga a gris sin que nadie lo note. Ésa es justo la decadencia
silenciosa que esta herramienta existe para detectar.

`--repo-root` se valida antes de auditar nada. Con una raíz equivocada todas
las rutas relativas fallan a la vez y el auditor declararía obsoletas todas las
memorias con total seguridad: un fallo masivo, seguro de sí mismo y en la
dirección que infla el dato. No hay heurística que intente adivinar la raíz
buena; fallar pronto y en voz alta es lo que se quiere.

## Principio de polaridad

**Una comprobación codifica LO QUE LA MEMORIA AFIRMA, no el estado actual del
mundo.** Sólo así la realidad puede contradecirla: si la memoria dice "esto
existe", la comprobación pregunta por eso, y el día que deje de existir la
memoria sale roja.

Escribir en su lugar lo que hay hoy ("ya no existe aquello, y ahora existe esto
otro") produce una comprobación que pasa siempre: describe el presente, y el
presente no se contradice a sí mismo.

**Una comprobación que siempre pasa es peor que ninguna**, porque da confianza
falsa; sin entrada la memoria sale gris, que es un resultado honesto. Por eso
`validateCheck` rechaza los patrones que no pueden fallar: un `file_matches` o
un `file_absent` cuyo último segmento sea sólo comodines (`*`, `**`, `dir/*`)
casa con cualquier entrada y no discrimina nada.

**Prueba antes de añadir una entrada**: escriba qué hecho concreto la volvería
roja. Si no se le ocurre ninguno, la comprobación no vigila nada y no debe
entrar. Y si ese hecho podría ocurrir sin que la memoria dejase de ser cierta
(un fichero movido de carpeta, un emoji cambiado), tampoco: un falso rojo acusa
a una memoria sana.

Cuidado con `date_passed`: afirma "esta fecha ya pasó" y **pasa** cuando ya
pasó. No sirve para caducar nada ("el token vence el X"): saldría verde
precisamente a partir del día en que la memoria deja de valer.

## Modelo de amenaza asumido

La contención de rutas (`resolveInRepo`) defiende de dos cosas: de los **enlaces
simbólicos** que apuntan fuera del árbol de trabajo y de las **rutas que
escapan** de la raíz (`../../etc/passwd`). La comprobación se hace sobre la ruta
real, ya resuelta, y sobre esa misma ruta se opera después, para que decisión y
lectura no puedan referirse a ficheros distintos.

**No defiende de un enlace duro plantado dentro del árbol de trabajo.** Un
enlace duro es indistinguible del fichero original por ruta: no hay nada que
`lstat` ni `realpath` puedan mirar para saber que ese nombre es otra entrada
del mismo inodo de fuera del repositorio. Es una limitación conocida y asumida,
no un problema resuelto.

Se asume, además, que quien puede escribir en el repositorio ya tiene acceso
local a las memorias: las memorias viven en el disco de la misma persona que
edita este repositorio. Un enlace duro dentro del árbol de trabajo no amplía,
por tanto, el acceso de nadie — sólo permitiría que quien ya podía leer esos
ficheros los leyese también a través de `file_contains`.

Lo que sí se defiende con cuidado, porque sí cambia el veredicto:

- el informe nunca incluye el cuerpo de una memoria (el programa no lo lee);
- los nombres de fichero y las claves de `checks.json` son entrada hostil y se
  sanean antes de interpolarlos: si no, un nombre con saltos de línea podría
  fabricar secciones y contadores falsos dentro del informe;
- no se construye ningún `RegExp` a partir de la entrada (nada de ReDoS), no se
  abre ningún FIFO (un FIFO sin escritor cuelga el proceso para siempre y un
  cuelgue no lo atrapa ningún `try/catch`) y las claves duplicadas de
  `checks.json` se buscan sobre el texto, porque `JSON.parse` se queda con la
  última en silencio.
