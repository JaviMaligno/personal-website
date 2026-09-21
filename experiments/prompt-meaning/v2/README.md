# Segundo piloto: explicaciones y efecto de instrucciones sin definición

**Completado:** [resultados del 21 de septiembre de 2026](results/pilot-2026-09-21-v2/findings.md).
220 llamadas completadas. Un caso sintético produjo una discrepancia estable entre
predicción y ejecución; los ocho traspasos naturales fueron explícitos y acertaron
las 384 decisiones examinadas. El informe conserva las abstenciones y los fallos
de formato, junto con los límites de la muestra.

[Protocolo fijado antes de ejecutar](DESIGN.md). Esta versión conserva el primer
piloto y sus fuentes sin cambios; utiliza una copia independiente del instrumento.

Las dos partes responden a preguntas distintas:

- Ocho conversaciones de tres rondas permiten observar qué información y términos
  llegan al prompt final. Se ejecutan todos los traspasos, contengan jerga o no.
- Ocho casos con etiquetas sin definición, introducidas deliberadamente, permiten
  contrastar predicciones con efectos observados sin depender de que aparezca jerga
  espontánea. No se presentan como expresiones descubiertas en conversaciones.

Los explicadores no ven la política de referencia, la conversación previa ni la
condición explícita. Se hacen dos repeticiones por ejecutor y variante. Los
resultados estables entre esas dos repeticiones se desglosan por separado.

## Ejecución

Python estándar, sin dependencias nuevas. Misma configuración privada y rutas
verificadas en el primer piloto; `selection_limit: 4`, `repetitions: 2`.

```bash
python3 -m unittest -v test_v2
python3 run.py validate-bank
python3 run.py init --run runs/pilot-02 --config runs/config.private.json
python3 run.py draft --run runs/pilot-02 --live --max-calls 8
python3 run.py revise --run runs/pilot-02 --live --max-calls 8
python3 run.py generate --run runs/pilot-02 --live --max-calls 8
python3 run.py prepare-review --run runs/pilot-02
```

Revisar los ocho prompts finales y sus conversaciones. Registrar cada exclusión;
para elegibles, fijar término, cláusula, sustitución y requisito correspondiente
antes de observar decisiones. Identificar a quien realiza la revisión.

```bash
python3 run.py freeze-selection --run runs/pilot-02
python3 run.py explain --run runs/pilot-02 --live --max-calls 28
python3 run.py freeze-predictions --run runs/pilot-02
python3 run.py prepare-probes --run runs/pilot-02
```

No se solicitan sondas en esta versión. Registrar el revisor del archivo vacío
`probe-review.json`, sin añadir entradas después de ver las predicciones.

```bash
python3 run.py freeze-execution --run runs/pilot-02
python3 run.py execute --run runs/pilot-02 --live --max-calls 240
python3 analyze.py --run runs/pilot-02
python3 export.py --run runs/pilot-02 --out results/pilot-02
```

El máximo de ejecución es 240 llamadas si hay cuatro candidatos naturales con
cuatro variantes; sin candidatos, 176. El plan sin `--live` muestra el número real.
Concurrencia máxima de dos, archivos por petición e historial de intentos. Nunca
se reintenta una salida inválida para conseguir una predicción conveniente.

Si falla la obtención local del token de `gcloud`, `resume_auth.py` permite reanudar
obteniéndolo una vez y conservándolo solo en la memoria del proceso. Mantiene las
peticiones y sus parámetros, registra la recuperación y conserva los intentos
interrumpidos. No imprime ni guarda el token en disco. Se usó esta recuperación
en la corrida del 21 de septiembre, después de 94 ejecuciones completadas.

## Lectura de resultados

`report.json` distingue `synthetic`, `natural`, `unmodified`, `positive` y
`redundant`. `policy_benchmarks` comprueba las políticas parcial y completa contra
sus oráculos. `prediction_comparisons` conserva pares esperados, abstenciones,
aciertos exactos, detección de cambios y la referencia de «sin cambio»; también
cuenta inputs estables/inestables y aciertos sobre los estables.

No sumar estos renglones como si fueran tareas independientes: comparten políticas,
inputs, ejecutores y predicciones. La ausencia de definición no implica que un
nombre no aporte pistas. Tampoco convierte cualquier explicación en inventada.

La exportación elimina rutas y configuración privada, conservando las 24 respuestas
de diseño y los prompts completos de cada llamada. `runs/` permanece fuera de Git.
