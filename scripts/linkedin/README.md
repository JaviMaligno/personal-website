# 🔗 LinkedIn Automation

Automatización completa de publicación Blog → LinkedIn usando GitHub Actions.

## 🎯 Cómo Funciona

Cuando haces push a `main` con un nuevo post en `src/content/blog/en/`:

1. **GitHub Actions detecta** el nuevo post
2. **Gemini 3.0 Flash** genera un resumen optimizado para LinkedIn
3. **Publica automáticamente** en tu perfil de LinkedIn con:
   - Resumen generado por IA
   - Link al artículo completo
   - Hashtags desde los tags del post
   - Imagen opcional (si `linkedinImage` está presente en frontmatter)

**Sin intervención manual. Completamente automático.**

---

## 📋 Secrets Configurados

Todos los secrets están en GitHub → Settings → Secrets and variables → Actions:

| Secret | Descripción | Status |
|--------|-------------|--------|
| `GEMINI_API_KEY` | API key de Gemini para generar resúmenes | ✅ Configurado |
| `LINKEDIN_ACCESS_TOKEN` | Token de acceso de LinkedIn (**expira en 60 días**) | ✅ Configurado |
| `LINKEDIN_CLIENT_ID` | Client ID de tu LinkedIn App | ✅ Configurado |
| `LINKEDIN_CLIENT_SECRET` | Client Secret de tu LinkedIn App | ✅ Configurado |
| `LINKEDIN_PERSON_URN` | Tu Person URN (`32sJkQwhsF`) | ✅ Configurado |

---

## ⚠️ Renovación del Access Token (cada 60 días)

El `LINKEDIN_ACCESS_TOKEN` expira después de **60 días**. Esta app **no tiene
programmatic refresh tokens** (el OAuth devuelve `refresh_token: undefined`),
así que el token **no se puede renovar automáticamente** — hay que regenerarlo
con el flujo OAuth.

### Aviso automático de caducidad

El workflow `.github/workflows/linkedin-token-check.yml` corre a diario, consulta
la caducidad real vía la [Token Introspection API](https://learn.microsoft.com/en-us/linkedin/shared/authentication/token-introspection)
y **abre un issue con la etiqueta `linkedin-token`** cuando quedan ≤ 7 días
(deduplicado: no abre un segundo issue si ya hay uno abierto). Así el token nunca
caduca en silencio a mitad de una publicación.

Comprobación manual en local:
```bash
set -a; . ./.env; set +a
node scripts/linkedin/check-token-expiry.js          # umbral por defecto: 7 días
node scripts/linkedin/check-token-expiry.js --threshold 14
```

### Cuando el token expire (o el issue avise):

Verás un error en GitHub Actions similar a:
```
❌ LinkedIn post creation failed (401): EXPIRED_ACCESS_TOKEN
```

### Para renovar el token:

1. **Ejecuta el script OAuth**:
   ```bash
   export LINKEDIN_CLIENT_ID=your_client_id
   export LINKEDIN_CLIENT_SECRET=your_client_secret
   node scripts/linkedin-oauth-setup.js
   ```

   (Usa tus credenciales de LinkedIn App desde https://www.linkedin.com/developers/apps)

2. **Autoriza en LinkedIn** (abrirá navegador)

3. **Copia el nuevo LINKEDIN_ACCESS_TOKEN**

4. **Actualiza el secret**:
   ```bash
   gh secret set LINKEDIN_ACCESS_TOKEN --body "tu_nuevo_token"
   ```

**O manualmente**:
- Ve a GitHub → Settings → Secrets and variables → Actions
- Edita `LINKEDIN_ACCESS_TOKEN`
- Pega el nuevo token

---

## 🧪 Testing

### Tests sin credenciales:
```bash
npm run test:detect    # Detección de posts
npm run test:summary   # Formato de resumen (mock)
```

### Test con Gemini API:
```bash
export GEMINI_API_KEY=tu_key
npm run test:gemini
```

### Suite completa:
```bash
npm run test:linkedin
```

Ver documentación completa en: `scripts/linkedin/README-TESTING.md`

---

## 📝 Uso

### Escribir un post con imagen de LinkedIn:

```yaml
---
title: "Mi Artículo"
description: "Descripción del artículo"
pubDate: 2026-01-07
tags: ["AI", "Automation"]
lang: en
translationKey: mi-articulo
linkedinImage: /blog/linkedin-card.png  # Opcional
---
```

### Escribir un post sin imagen:

Simplemente omite el campo `linkedinImage`:

```yaml
---
title: "Mi Artículo"
description: "Descripción del artículo"
pubDate: 2026-01-07
tags: ["AI", "Automation"]
lang: en
translationKey: mi-articulo
---
```

### Resultado en LinkedIn:

```
[Resumen generado por Gemini 3.0 Flash - 2-3 párrafos]

📖 Read more: https://javieraguilar.ai/en/blog/mi-articulo

#AI #Automation
```

---

## 🖼️ Posts Standalone: Múltiples Imágenes

`post-standalone.js` busca media en este orden de prioridad:

1. **Vídeo** en la raíz del repo: `video-linkedin.mov/.mp4/...` (un solo vídeo, excluye imágenes)
2. **Carpeta con el mismo nombre que el post**: para `scripts/linkedin/posts/mi-post.txt`, crea `scripts/linkedin/posts/mi-post/` y mete dentro las imágenes (`.png/.jpg/.jpeg/.gif`). Se publican **todas**, ordenadas con sort natural (`1-cover.png`, `2-diagram.png`, `10-final.png` quedan en ese orden)
3. **Imágenes numeradas** en la raíz del repo: `image-1.png`, `image-2.jpg`, ... (orden numérico, hasta 20)
4. **Imagen única** en la raíz del repo: `image.png` (comportamiento legacy)

```bash
# Ejemplo multi-imagen con carpeta:
mkdir scripts/linkedin/posts/mi-post
cp diagrama1.png diagrama2.png scripts/linkedin/posts/mi-post/
node scripts/linkedin/post-standalone.js scripts/linkedin/posts/mi-post.txt --dry-run
```

La API `ugcPosts` acepta varios elementos en el array `media` con `shareMediaCategory: IMAGE` — LinkedIn los renderiza como post multi-imagen (collage). Límite práctico: ~20 imágenes.

En `utils.js`, `createLinkedInPost` acepta `imageUrns` (array) y mantiene compatibilidad con `imageUrn` (string), que sigue usando `publish-to-linkedin.js`.

---

## 🏷️ Menciones a Empresas y Personas

### Sintaxis en los .txt de posts

```
Gracias a @[LangChain](urn:li:organization:25507109) por la librería,
y a @[Jane Doe](urn:li:person:abc123) por el review.
```

- El texto visible publicado será `LangChain` / `Jane Doe` (el marcador se elimina).
- El script genera `shareCommentary.attributes` con `start`/`length` calculados sobre el **texto ya limpio**:
  - `urn:li:organization:*` → `com.linkedin.common.CompanyAttributedEntity` (campo `company`)
  - `urn:li:person:*` → `com.linkedin.common.MemberAttributedEntity` (campo `member`)

### ⚠️ Reglas importantes

1. **El texto visible debe coincidir EXACTAMENTE (case-sensitive) con el nombre real** de la empresa/persona en LinkedIn. Si no coincide, LinkedIn lo muestra como texto plano sin link.
2. **Offsets en UTF-16 code units**: la doc oficial no especifica el encoding, pero los strings de JavaScript son UTF-16 nativamente y es el comportamiento observado de LinkedIn. Los emojis fuera del BMP (🚀, 🤖...) cuentan como **2 unidades**. El parser (`parseMentions` en `utils.js`) usa aritmética nativa de JS, así que esto es automático — **no recalcules offsets a mano** contando "caracteres".
3. Verifica siempre con `--dry-run` antes de publicar: imprime las menciones detectadas y el JSON de `attributes`.

```bash
node scripts/linkedin/post-standalone.js scripts/linkedin/posts/_example-mentions.txt --dry-run
```

> `_example-mentions.txt` es solo un ejemplo: el cron diario **solo publica posts listados en `schedule.json`**, así que nunca se publicará solo.

### Cómo obtener el URN de una organización

**Opción A — API** (requiere Community Management API / `r_organization_lookup` en tu LinkedIn App):

```bash
export LINKEDIN_ACCESS_TOKEN=tu_token
node scripts/get-linkedin-urn.js --org langchain   # vanity name = slug de linkedin.com/company/<slug>
```

**Opción B — Manual** (funciona siempre):
1. Abre la página de empresa: `linkedin.com/company/<nombre>`
2. Ver código fuente de la página (Cmd+Opt+U) y busca `urn:li:organization:` o `fsd_company:` — el número es el ID
3. Alternativa: si administras la página, el ID numérico aparece en la URL del panel de admin (`linkedin.com/company/12345678/admin/`)
4. Úsalo como `urn:li:organization:12345678`

Para personas: el person URN no se puede buscar por nombre con permisos básicos. Para tu propio URN usa `node scripts/get-linkedin-urn.js`. Para terceros, pídeles su URN o usa el ID que aparece en herramientas de su perfil.

Referencia API: [UGC Post API — Attribute schema](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/ugc-post-api)

---

## 🔧 Arquitectura

```
Blog Post (push to main)
    ↓
GitHub Actions Workflow
    ↓
1. Detect new English posts (git diff)
    ↓
2. Generate summary (Gemini 3.0 Flash → 2.5 fallback)
    ↓
3. Upload image (if linkedinImage exists)
    ↓
4. Publish to LinkedIn (UGC API)
    ↓
✅ Post live at linkedin.com/in/javier-aguilar-ai
```

---

## 📂 Estructura de Archivos

```
scripts/linkedin/
├── detect-new-posts.js      # Detecta posts via git diff
├── generate-summary.js      # Gemini API integration
├── publish-to-linkedin.js   # Orquestador principal
├── utils.js                 # LinkedIn API helpers
├── refresh-token.js         # (Deprecated - no usado)
├── test-*.js                # Suite de tests
├── README.md                # Este archivo
└── README-TESTING.md        # Documentación de testing

.github/workflows/
└── linkedin-post.yml        # Workflow de automatización
```

---

## 🚨 Troubleshooting

### Error: "LinkedIn post creation failed (401)"
→ El access token expiró. Sigue los pasos de renovación arriba.

### Error: "GEMINI_API_KEY not set"
→ Verifica que el secret está configurado en GitHub.

### Error: "Image not found"
→ Verifica que la imagen existe en `public/blog/` y la ruta en frontmatter es correcta.

### Post no se publicó
→ Verifica en GitHub Actions (Actions tab) los logs del workflow.

---

## 📊 Costos

- **Gemini API**: ~$0.00001 por post (Flash 3.0). Mensual: <$0.01
- **LinkedIn API**: Gratuito
- **GitHub Actions**: Free tier suficiente (2000 min/mes)

**Total estimado mensual**: < $0.01 USD

---

## 🔐 Seguridad

- ✅ Todos los tokens en GitHub Secrets (nunca en código)
- ✅ Scripts OAuth excluidos de git (.gitignore)
- ✅ Access token válido solo 60 días
- ✅ Sin refresh token (renovación manual para mayor seguridad)

---

## 📅 Próxima Renovación de Token

**Configurado**: 2026-01-07
**Expira**: ~2026-03-08 (60 días)
**Recordatorio**: Revisar GitHub Actions en marzo 2026

---

**Creado por**: Javier Aguilar (AI Agent Architect)
**LinkedIn**: https://linkedin.com/in/javier-aguilar-ai
**Website**: https://javieraguilar.ai
