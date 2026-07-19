# ⚠️ Este proyecto debe moverse a su propio repositorio

Este directorio (`experiments/wheres-the-ball/`) vive **temporalmente** dentro
de `personal-website` porque la sesión de Claude que lo desarrolló no tenía
permisos para crear repositorios (la integración de GitHub estaba limitada a
este repo). El diseño (entregable §9.1 del Nivel 1) pide un repo separado.

## Pasos para migrarlo (en local)

1. **Crear el repo vacío** en GitHub: `JaviMaligno/wheres-the-ball`
   (sin README ni .gitignore iniciales, para poder empujar historia limpia).

2. **Extraer el directorio conservando su historia** con `git subtree split`:

   ```bash
   cd personal-website
   git fetch origin
   git checkout claude/design-initial-code-c2ddpm   # rama donde vive el código
   git subtree split --prefix=experiments/wheres-the-ball -b wtb-split

   cd ..
   git clone --no-local personal-website wheres-the-ball-tmp --branch wtb-split
   cd wheres-the-ball-tmp
   git branch -m wtb-split main
   git remote set-url origin git@github.com:JaviMaligno/wheres-the-ball.git
   git push -u origin main
   ```

   (Alternativa rápida sin historia: copiar el directorio a un repo nuevo y
   hacer un commit inicial. La historia son pocos commits; no pasa nada por
   perderla.)

3. **Limpiar este repo**: una vez verificado el push,

   ```bash
   cd personal-website
   git checkout claude/design-initial-code-c2ddpm
   git rm -r experiments/wheres-the-ball
   git branch -D wtb-split
   git commit -m "chore: move wheres-the-ball experiment to its own repo"
   ```

   y enlazar el repo nuevo desde `docs/research/` (rama
   `claude/sports-object-prediction-4oejhu`) o desde donde acaben viviendo
   los documentos de diseño.

4. **Verificar en el repo nuevo**:

   ```bash
   python3 -m venv .venv && .venv/bin/pip install -e ".[dev,viz]"
   .venv/bin/pytest          # todo debe pasar sin red ni claves
   .venv/bin/python -m wheresball.demo
   ```

## Después de migrar

- Los documentos de diseño ya están copiados en `docs/` de este proyecto, así
  que el repo nuevo es autocontenido.
- El trabajo pendiente (datos reales, claves de API) está en [TODO.md](./TODO.md).
- Las referencias para escribir los artículos están en
  [`docs/referencias.md`](./docs/referencias.md) y
  [`docs/referencias.bib`](./docs/referencias.bib).
