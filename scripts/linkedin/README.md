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

El `LINKEDIN_ACCESS_TOKEN` expira después de **60 días** (configurado el 2026-01-07, expira ~2026-03-08).

### Cuando el token expire:

Verás un error en GitHub Actions similar a:
```
❌ LinkedIn post creation failed (401): Unauthorized
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
