# 🧪 Testing LinkedIn Automation

Este directorio contiene scripts de test para validar la automatización Blog → LinkedIn **sin necesitar configurar OAuth**.

## Tests Disponibles

### 1️⃣ Test de Detección de Posts
```bash
node scripts/linkedin/test-detect-posts.js
```

**Qué valida:**
- ✅ Lectura de archivos markdown del blog
- ✅ Parseo de frontmatter (gray-matter)
- ✅ Extracción de: título, descripción, tags, linkedinImage
- ✅ Generación de URL del post
- ✅ Generación de hashtags desde tags

**No requiere:**
- ❌ API keys
- ❌ Credenciales de LinkedIn

---

### 2️⃣ Test de Formato de Resumen (Mock)
```bash
node scripts/linkedin/test-summary.js
```

**Qué valida:**
- ✅ Estructura del prompt para Gemini
- ✅ Formato del post de LinkedIn (texto + link + hashtags)
- ✅ Límite de caracteres (3000 max)
- ✅ Muestra un ejemplo mock de resumen

**No requiere:**
- ❌ API keys
- ❌ Credenciales

---

### 3️⃣ Test de Gemini API (Real)
```bash
export GEMINI_API_KEY=tu_api_key
node scripts/linkedin/test-gemini.js
```

**Qué valida:**
- ✅ Generación real de resumen con Gemini 3.0 Flash
- ✅ Fallback automático a Gemini 2.5 Flash si falla
- ✅ Post completo de LinkedIn con resumen real
- ✅ Verificación de límite de caracteres

**Requiere:**
- ✅ `GEMINI_API_KEY` (obtén una gratis en https://aistudio.google.com/apikey)

---

### 4️⃣ Suite Completa
```bash
node scripts/linkedin/test-all.js
```

Ejecuta todos los tests en secuencia y muestra un resumen de resultados.

**Salida esperada:**
```
🧪 Running LinkedIn Automation Test Suite
═══════════════════════════════════════════════════════════

🧪 Test: Post Detection & Parsing
✅ Test passed!

🧪 Test: Summary Preparation (Mock)
✅ Test passed!

🧪 Test: Gemini API Integration
⏭️  Skipped (requires GEMINI_API_KEY)

═══════════════════════════════════════════════════════════
📊 Test Results:
  ✅ Passed: 2
  ❌ Failed: 0
  ⏭️  Skipped: 1
  📝 Total: 3
```

---

## Orden Recomendado

1. **Primero**: Instala dependencias
   ```bash
   npm install
   ```

2. **Test básico** (sin credenciales):
   ```bash
   node scripts/linkedin/test-detect-posts.js
   ```

3. **Test de formato** (sin credenciales):
   ```bash
   node scripts/linkedin/test-summary.js
   ```

4. **Obtén Gemini API key**: https://aistudio.google.com/apikey

5. **Test de Gemini** (con API key):
   ```bash
   export GEMINI_API_KEY=tu_key
   node scripts/linkedin/test-gemini.js
   ```

6. **Suite completa**:
   ```bash
   node scripts/linkedin/test-all.js
   ```

---

## Modelos Gemini Usados

- **Primary**: `gemini-3-flash-preview` (Gemini 3.0 Flash, enero 2026)
- **Fallback**: `gemini-2.5-flash` (Gemini 2.5 Flash)

Si Gemini 3.0 falla (rate limit, error temporal), el sistema automáticamente reintenta con 2.5 Flash.

---

## Troubleshooting

### Error: "Cannot find module 'gray-matter'"
```bash
npm install
```

### Error: "GEMINI_API_KEY not set"
```bash
export GEMINI_API_KEY=tu_api_key_aqui
node scripts/linkedin/test-gemini.js
```

### Error: "Post file not found"
Asegúrate de ejecutar los scripts desde la raíz del proyecto:
```bash
cd /ruta/a/personal-website
node scripts/linkedin/test-detect-posts.js
```

---

## Siguientes Pasos

Una vez que todos los tests pasen:

1. ✅ Configurar LinkedIn OAuth (ver README principal)
2. ✅ Añadir GitHub Secrets
3. ✅ Push a `main` y ver la magia ocurrir

---

**Nota**: Estos tests NO publican nada en LinkedIn. Son solo para validar que el código funciona correctamente antes del setup completo.
