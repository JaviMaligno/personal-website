# Pendiente

Organizado por las fases del plan de ejecución (diseño Nivel 1, §10). Las
tareas marcadas **[LOCAL]** necesitan algo que solo está disponible en local:
credenciales, claves de API, o descargas grandes.

## Fase 0 — Viabilidad

- [ ] **[LOCAL]** Pedir credenciales de SoccerNet (formulario NDA en
      [soccer-net.org](https://www.soccer-net.org/)) y descargar una muestra
      del split de tracking.
- [ ] **[LOCAL]** Verificar contra los ficheros reales lo que el parser asume
      (`src/wheresball/dataset/mot.py`): etiquetas exactas de `gameinfo.ini`,
      número de columnas de `gt/gt.txt`, `seqinfo.ini` (fps, tamaño de imagen).
- [ ] Comprobar que hay suficientes frames de oclusión natural por estrato
      (usar `masking.occlusion_stats` sobre las anotaciones descargadas).
- [ ] **[LOCAL]** Probar el prompt a mano con ~10 ítems en 2 modelos (claves API).

## Fase 1 — Construcción del dataset

- [ ] Implementar `dataset/soccernet.py` sobre el parser MOT ya escrito
      (descarga → secuencias → `tracking_to_item` → selección → estratificación).
- [ ] **Validar la heurística de estado del balón** (`mot.classify_ball_state`)
      contra ~50 clips etiquetados a mano; ajustar umbrales o etiquetar a mano
      los 500 ítems si la heurística no es fiable.
- [ ] Aplicar criterios de exclusión (§3): repeticiones, primeros planos,
      balón fuera de plano, paradas de juego. Probablemente manual/semiautomático.
- [ ] Comprobar disponibilidad de homografías/calibración en el split usado y
      conectarlas con `geometry.py` para reportar errores en metros.
- [ ] Congelar el conjunto (~500 ítems) con `dataset.freeze` y registrar el hash
      en el repo ANTES de ejecutar ningún modelo (pre-registro).
- [ ] (Si hace falta el estrato 3) Inpainting local + `harness.leakcheck` con un
      modelo barato como detector; reportar tasa de descarte.

## Fase 2 — Baselines

- [x] B0–B4 + B0' implementados y testeados.
- [ ] Ejecutarlos sobre el conjunto congelado real (sin coste, sin APIs).
- [ ] Techo especialista: decidir si se reproduce Kim et al. 2023 /
      TranSPORTmer o se citan sus números publicados como cota (§4).

## Fase 3 — Evaluación VLM

- [x] Clientes API de Anthropic / OpenAI / Gemini escritos y testeados con
      transporte falso (`harness/api_clients.py`).
- [ ] **[LOCAL]** Fijar model ids actuales (los defaults del código rotan),
      exportar `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` y
      hacer una ejecución de humo con ~10 ítems.
- [ ] Añadir cliente de un VLM abierto (Qwen-VL vía API compatible OpenAI o
      local) como referencia open-source (§4).
- [ ] Presupuestar el coste real de la matriz (~12k llamadas, §5) tras la
      ejecución de humo; recortar condiciones si excede.
- [ ] Soporte de vídeo nativo para Gemini (la condición clip, §5) — hoy solo
      multi-frame.
- [ ] Contabilidad de fallos de parseo por modelo (hoy `ApiVLMClient` lanza
      excepción; decidir política: descartar ítem vs. predicción nula, y
      reportar la tasa).
- [ ] **[LOCAL]** Ejecutar la matriz completa con caché (`ResponseCache`) y
      registrar versiones de modelo, fechas y coste en el repo.

## Fase 4 — Estudio humano (opcional, recomendado)

- [ ] Interfaz web simple (puede vivir en personal-website): mostrar ítem,
      click donde crees que está el balón, confianza. 5–10 personas,
      ~100 ítems cada una.
- [ ] Exportar respuestas al mismo formato `Prediction` para entrar por el
      mismo pipeline de métricas.

## Fase 5 — Análisis y artículo

- [x] Métricas, bootstrap, Wilcoxon+Holm y figuras base implementadas.
- [ ] Notebook/script de análisis final sobre resultados reales.
- [ ] Ejemplos cualitativos: render de aciertos/fallos con el razonamiento del
      modelo (`viz.render_item` con predicción superpuesta sobre el frame real).
- [ ] Artículo de blog EN/ES con la skill `blog-writer` de personal-website;
      esqueleto en [`docs/articulo-esqueleto.md`](./docs/articulo-esqueleto.md),
      referencias en [`docs/referencias.md`](./docs/referencias.md).
- [ ] Decisión go/no-go del Nivel 2 documentada en `docs/README.md`
      (registro de decisiones).

## Infraestructura

- [ ] **[LOCAL]** Migrar a repo propio — ver [MIGRATION.md](./MIGRATION.md).
- [ ] CI (GitHub Actions: pytest en push) una vez migrado.
- [ ] Revisar licencia de SoccerNet antes de publicar el dataset de evaluación
      (si no permite redistribuir: publicar solo IDs + scripts, §9.2).
