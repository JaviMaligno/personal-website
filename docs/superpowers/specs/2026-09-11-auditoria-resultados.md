# Auditoría de vigencia de memorias — resultados

Fecha: 2026-09-11
Spec: [`2026-09-11-dos-regimenes-de-memoria-design.md`](2026-09-11-dos-regimenes-de-memoria-design.md) §4
Plan: [`../plans/2026-09-11-auditoria-vigencia-memorias.md`](../plans/2026-09-11-auditoria-vigencia-memorias.md)
Herramienta: `scripts/memory-audit/` (commit `44058c0`)

## Predicción registrada antes de ejecutar

De §4.4 de la spec, escrita antes de correr nada:

> El montón gris será el mayor y el rojo será pequeño pero no cero. Si el rojo sale
> en cero, la tesis del artículo se debilita y hay que decirlo.

**Se cumplió**: gris 25 (el mayor), rojo 3 (pequeño, no cero).

## Resultado

35 memorias del proyecto `personal-website`, con 10 anotadas en `checks.json`:

| estado | nº | qué significa |
|---|---|---|
| **verde** | 7 | la comprobación pasa |
| **rojo** | 3 | afirma algo que ya no es cierto |
| **gris** | 25 | no admite comprobación, y está bien |
| error | 0 | ninguna comprobación ilegible o inevaluable |
| huérfanas | 0 | ninguna comprobación sin su memoria |

## Las tres rojas, verificadas a mano

Una roja es una acusación, así que se comprobó cada una contra el repositorio.

| memoria | qué afirma | realidad |
|---|---|---|
| `project_blog_publishing_mechanism` | programar un artículo se hace con un workflow de un solo uso `scheduled-publish-<slug>.yml` | sustituido por `.github/publish-schedule.json`; **cero** workflows de ese tipo en `main` |
| `project_agent_code_practices_campaign` | su artículo sigue pendiente en una rama | publicado el 2026-08-30 |
| `project_language_limits_experiment` | dos artículos pendientes de merge y de revisión | publicados el 2026-07-15 y el 2026-07-30 |

**Las tres comparten forma, y es el hallazgo del experimento.** Ninguna se
equivocó al escribirse: las tres describían un **estado transitorio** —«esto está
pendiente»— que caducó solo, en silencio, el día en que el trabajo avanzó. Nadie
volvió a tocarlas porque nada obliga a hacerlo. La memoria que registra un hecho
estable envejece bien; la que registra una situación en curso empieza a caducar
desde el momento en que se escribe.

Y una de ellas se sirvió como contexto al arrancar la sesión del 2026-09-11, ya
obsoleta.

## Las 25 grises

De las 31 memorias sin comprobación al empezar, cinco agentes recorrieron todas y
propusieron comprobación solo para **7**. Un revisor adversarial rechazó una por
forzada (`feedback_agilabs_own_cv_section`: es una preferencia acordada, y la
comprobación la sustituía por la presencia de un encabezado literal, que falla en
las dos direcciones). Quedaron 6.

Es decir: **~80 % de las memorias no admiten comprobación mecánica**, y eso no es
un déficit de la herramienta. Son preferencias, criterios y formas de trabajar, que
no se vuelven falsas solas: cambian cuando la persona cambia de opinión, y entonces
lo dice. Es la mitad que Claude Code ya maneja bien (§2 de la spec) y la que hace
agradable el trabajo diario.

La instrucción a los agentes fue explícitamente conservadora —ante la duda, gris—
porque una comprobación forzada infla el verde y falsea el único producto de todo
esto, que es este número.

## Tres preguntas de revalidación

No todo lo caducable es expresable con el vocabulario. Tres memorias llevan una
pregunta para una persona, y **siguen contando como grises**: una pregunta pendiente
no es una comprobación.

La más interesante es `project_linkedin_api_automation`: la memoria fija una fecha
de caducidad de credencial **ya pasada**, y aun así la memoria sale **verde**,
porque lo que se codificó es que sus siete artefactos existen. `date_passed` no
sirve aquí: afirma «esta fecha ya pasó», así que saldría verde justo desde el día
en que la memoria deja de valer. Es la inversión de polaridad que el README advierte.

## Lo que este resultado NO dice

- **Un verde certifica lo codificado, no la memoria entera.** El caso de arriba lo
  demuestra dentro del propio experimento.
- **El reparto depende de cuántas memorias se anoten.** Con 10 de 35 anotadas, «25
  grises» mezcla «no admite comprobación» con «nadie le ha escrito una todavía».
  Las 6 nuevas salieron de recorrer las 31, así que el sesgo es pequeño, pero
  existe y conviene decirlo.
- **Tres rojas sobre 35 no es una tasa de obsolescencia.** Es el resultado de un
  corpus pequeño, de una sola persona y un solo proyecto.

## Nota sobre el proceso

La herramienta que produjo este dato necesitó cinco rondas de revisión adversarial.
Los fallos graves que se encontraron compartían forma con lo que el artículo
denuncia: **eran silenciosos y sesgaban hacia «todo correcto»**. Falso verde cuando
el directorio del patrón no existía; falso gris cuando la palabra `checks:` aparecía
antes en otro campo; y comprobaciones cuya polaridad describía el presente en vez de
lo que la memoria afirma, y que por tanto no podían fallar nunca.

Esa última la escribí en la spec, y salía verde. La verificación de la vigencia puede
estar mal escrita exactamente de la misma forma que la memoria que vigila, y con la
misma consecuencia: nadie lo nota, porque el informe dice que todo está bien.
