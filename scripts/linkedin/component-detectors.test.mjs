/**
 * Los detectores de la regla de componentes, contra los dos unicos textos de
 * los que sabemos la respuesta: el post que salio publicado el 2026-09-21 con
 * los tres bloques amontonados, y la version corregida a mano ese mismo dia.
 *
 * Sin esto, el experimento component-rule.mjs mide con una regla de la que no
 * sabemos si mide algo. El README de experiments/ ya avisa de lo contrario: la
 * primera version de un detector dio 3 de 12 donde leyendo habia 12 de 12.
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { componentes, listaInventada } from './experiments/scores.mjs';

const BLOQUES = [
  { name: 'frontend', re: /frontend/i },
  { name: 'application backend', re: /application backend|app backend|the backend/i },
  { name: 'agentic engine', re: /agentic engine|the engine/i },
];

// Publicado el 2026-09-21 (urn:li:share:7507817874519019520), generado por el prompt.
const PUBLICADO = `Changing how an agent investigates a data source requires different work than changing how a user reviews and accepts the results.

A consistent separation has appeared in my projects between the frontend, the application backend, and the agentic engine. This engine handles the workflows, prompts, tools, and context management. Giving it its own identity does not require making it a microservice, but it recognizes that these components have distinct reasons to change.

In a data source automation pipeline, the engine generates specifications while an evaluation set compares stage outputs against corrected references. The application backend remains responsible for the work lifecycle, permissions, and rules. This architecture ensures that the mechanics of the agent do not become entangled with the core product logic.`;

// La correccion que se pego a mano: una linea por bloque, con su responsabilidad.
const CORREGIDO = `Changing how an agent investigates a data source is different work from changing how a user reviews and accepts the results. Both need server code. Their reasons to change are not the same.

That is why a separation keeps appearing in the projects I work on, as three blocks of responsibility:

Frontend — interaction, supervision, results.

Application backend — permissions, rules, the lifecycle of the work.

Agentic engine — workflows, prompts, tools, context management, and the evaluations that say whether all of that does its job.

They are responsibilities, not deployment units. The three can share a repository or a process, and giving the engine an identity of its own does not require making it a microservice.`;

test('el post publicado amontona los tres bloques en una frase', () => {
  const r = componentes(PUBLICADO, BLOQUES);
  assert.equal(r.amontonados, true, 'la frase que los enumera tiene que detectarse');
  assert.ok(r.atribuidos < 3, `atribuidos=${r.atribuidos}: no los tres llevan responsabilidad propia`);
});

test('el post corregido da responsabilidad propia a los tres', () => {
  const r = componentes(CORREGIDO, BLOQUES);
  assert.equal(r.atribuidos, 3, 'los tres tienen linea propia con su responsabilidad');
  assert.equal(r.amontonados, false, 'ninguna frase los enumera de corrido');
});

test('una mencion suelta no cuenta como responsabilidad', () => {
  const suelto = 'Frontend.\n\nApplication backend.\n\nAgentic engine.';
  assert.equal(componentes(suelto, BLOQUES).atribuidos, 0);
});

test('listaInventada marca tres lineas de lista y no la prosa', () => {
  assert.equal(listaInventada(CORREGIDO), true);
  assert.equal(listaInventada(PUBLICADO), false);
});

test('sin componentes declarados el detector se abstiene', () => {
  assert.equal(componentes(PUBLICADO, []), null);
});

// 2026-09-22: el formato que la regla produce de verdad en los posts generados
// usa dos puntos, no guion largo. El detector partia las frases por ":" y
// contaba estos tres como no atribuidos.
const CON_DOS_PUNTOS = `Changing how an agent investigates a data source requires a different cycle than updating how a user approves its results.

This structure defines three clear layers:

Frontend: Handles interaction, user supervision, and displaying results.

Application backend: Manages permissions, rules, and the work lifecycle.

Agentic engine: Runs workflows, manages context, connects tools, and executes evaluations.`;

test('el formato "Componente: responsabilidad" cuenta como atribuido', () => {
  const r = componentes(CON_DOS_PUNTOS, BLOQUES);
  assert.equal(r.atribuidos, 3, 'los dos puntos no deben partir nombre y responsabilidad');
  assert.equal(r.amontonados, false);
});

test('una enumeracion con dos puntos delante sigue siendo amontonamiento', () => {
  const enumerado = 'I separate code into three blocks: the frontend, the application backend, and the agentic engine.';
  assert.equal(componentes(enumerado, BLOQUES).amontonados, true);
});
