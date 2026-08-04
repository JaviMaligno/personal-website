import type { APIRoute } from 'astro';

// The only on-demand route on the site; everything else stays prerendered.
export const prerender = false;

const BREVO_API = 'https://api.brevo.com/v3';
const SITE = 'https://www.javieraguilar.ai';

// Brand palette, inlined because email clients drop <style> blocks and support
// neither CSS variables nor flexbox/grid. Tables and inline styles only.
const INK = '#0f1115';
const PAPER = '#ffffff';
const MUTED = '#6b7280';
const LINE = '#e5e7eb';
const ACCENT = '#6366f1';
const EMPTY = '#f3f4f6';

interface Payload {
  email: string;
  lang: 'en' | 'es';
  /** "Category: Level" per line, exactly as shown on screen. */
  result: string;
  /** Unknown-category count, so the email can lead with it. */
  unknown: number;
  /** Whether they left the marketing box ticked. */
  subscribe: boolean;
  /** Summary as shown on screen; the email must not contradict it. */
  headline?: string;
}

const COPY = {
  en: {
    subject: 'Your map',
    title: 'Your map',
    intro: 'Here is the map you just filled in.',
    unknownLine: (n: number) =>
      n === 1
        ? 'One category you did not know was a category. That is where to start — knowing it exists is enough to start asking.'
        : `${n} categories you did not know were categories. That is where to start — knowing they exist is enough to start asking.`,
    noUnknown:
      'No blind spots on the list itself. From here the question is whether every box has someone checking it — you, a test, a service, or another person.',
    levelHeading: 'Level',
    categoryHeading: 'Category',
    outro:
      'If you want to go through this with your actual project, just reply to this email and we will find a time.',
    readArticle: 'Read the whole system',
    seeMentoring: 'How I do this with teams',
    attachmentNote: 'Your map is attached as well, so you can keep it or print it.',
    footer: 'You received this because you asked for your map at javieraguilar.ai.',
    fileName: 'your-map.html'
  },
  es: {
    subject: 'Tu mapa',
    title: 'Tu mapa',
    intro: 'Aquí tienes el mapa que acabas de rellenar.',
    unknownLine: (n: number) =>
      n === 1
        ? 'Una categoría que no sabías que era una categoría. Por ahí se empieza: saber que existe basta para empezar a preguntar.'
        : `${n} categorías que no sabías que eran categorías. Por ahí se empieza: saber que existen basta para empezar a preguntar.`,
    noUnknown:
      'Ningún punto ciego en la lista. A partir de aquí la pregunta es si cada casilla tiene quien la compruebe: tú, un test, un servicio u otra persona.',
    levelHeading: 'Nivel',
    categoryHeading: 'Categoría',
    outro:
      'Si quieres recorrer esto con tu proyecto real delante, responde a este correo y buscamos un hueco.',
    readArticle: 'Leer el sistema completo',
    seeMentoring: 'Cómo lo hago con equipos',
    attachmentNote: 'Te adjunto también el mapa, para que lo guardes o lo imprimas.',
    footer: 'Recibes esto porque pediste tu mapa en javieraguilar.ai.',
    fileName: 'tu-mapa.html'
  }
} as const;

function escapeHtml(value: string): string {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/** "Category: Level" lines, with the level position worked out from the names. */
function parseRows(result: string, levelNames: string[]): Array<{ category: string; level: number; label: string }> {
  return result
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const at = line.lastIndexOf(':');
      const category = at === -1 ? line : line.slice(0, at).trim();
      const label = at === -1 ? '' : line.slice(at + 1).trim();
      const level = Math.max(0, levelNames.indexOf(label));
      return { category, level, label };
    });
}

/** Three cells per meter — coloured table cells are the one thing every client renders. */
function meter(level: number): string {
  const cell = (filled: boolean) =>
    `<td width="18" height="9" style="width:18px;height:9px;background:${
      filled ? ACCENT : EMPTY
    };border-radius:2px;font-size:0;line-height:0;">&nbsp;</td>`;
  const gap = '<td width="4" style="width:4px;font-size:0;line-height:0;">&nbsp;</td>';
  return `<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>${cell(
    level >= 1
  )}${gap}${cell(level >= 2)}${gap}${cell(level >= 3)}</tr></table>`;
}

function buildTable(rows: ReturnType<typeof parseRows>, copy: (typeof COPY)['en']): string {
  const header = `<tr>
    <th align="left" style="padding:0 0 8px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:${MUTED};font-weight:600;">${copy.categoryHeading}</th>
    <th align="left" style="padding:0 0 8px;"></th>
    <th align="right" style="padding:0 0 8px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:${MUTED};font-weight:600;">${copy.levelHeading}</th>
  </tr>`;

  const body = rows
    .map((row) => {
      const isEmpty = row.level === 0;
      const background = isEmpty ? '#fafafa' : PAPER;
      return `<tr>
      <td style="padding:10px 12px;border-top:1px solid ${LINE};background:${background};font-size:15px;color:${INK};${
        isEmpty ? 'font-weight:600;' : ''
      }">${escapeHtml(row.category)}</td>
      <td style="padding:10px 12px;border-top:1px solid ${LINE};background:${background};">${meter(row.level)}</td>
      <td align="right" style="padding:10px 12px;border-top:1px solid ${LINE};background:${background};font-size:13px;color:${MUTED};white-space:nowrap;">${escapeHtml(
        row.label
      )}</td>
    </tr>`;
    })
    .join('');

  return `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;margin:20px 0;">${header}${body}</table>`;
}

function buildEmail(payload: Payload, lang: 'en' | 'es', levelNames: string[]): string {
  const copy = COPY[lang];
  const rows = parseRows(payload.result, levelNames);
  const headline =
    payload.headline || (payload.unknown > 0 ? copy.unknownLine(payload.unknown) : copy.noUnknown);

  return `<!doctype html>
<html lang="${lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${copy.title}</title>
</head>
<body style="margin:0;padding:0;background:#f6f7f9;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f6f7f9;padding:32px 16px;">
<tr><td align="center">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;background:${PAPER};border-radius:12px;padding:32px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
    <tr><td>
      <h1 style="margin:0 0 4px;font-size:26px;line-height:1.2;color:${INK};">${copy.title}</h1>
      <p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:${MUTED};">${copy.intro}</p>
      <p style="margin:0;padding:14px 16px;background:#f5f5ff;border-left:3px solid ${ACCENT};font-size:15px;line-height:1.6;color:${INK};">${escapeHtml(
    headline
  )}</p>
      ${buildTable(rows, copy)}
      <p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:${INK};">${copy.outro}</p>
      <p style="margin:0 0 24px;font-size:14px;line-height:1.6;color:${MUTED};">${copy.attachmentNote}</p>
      <p style="margin:0;font-size:15px;">
        <a href="${SITE}/${lang}/blog/what-you-still-need-to-know-to-ship" style="color:${ACCENT};text-decoration:none;">${copy.readArticle}</a>
        <span style="color:${LINE};">&nbsp;·&nbsp;</span>
        <a href="${SITE}/${lang}/mentoring" style="color:${ACCENT};text-decoration:none;">${copy.seeMentoring}</a>
      </p>
      <hr style="border:none;border-top:1px solid ${LINE};margin:28px 0 16px;">
      <p style="margin:0;font-size:12px;line-height:1.5;color:${MUTED};">${copy.footer}</p>
    </td></tr>
  </table>
</td></tr>
</table>
</body>
</html>`;
}

/** Standalone copy to keep: opens in any browser, prints to PDF. */
function buildAttachment(payload: Payload, lang: 'en' | 'es', levelNames: string[]): string {
  const copy = COPY[lang];
  const rows = parseRows(payload.result, levelNames);
  const headline =
    payload.headline || (payload.unknown > 0 ? copy.unknownLine(payload.unknown) : copy.noUnknown);

  return `<!doctype html>
<html lang="${lang}">
<head>
<meta charset="utf-8">
<title>${copy.title} — javieraguilar.ai</title>
</head>
<body style="margin:0;padding:40px 20px;background:${PAPER};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:${INK};">
<div style="max-width:620px;margin:0 auto;">
  <h1 style="font-size:30px;margin:0 0 6px;">${copy.title}</h1>
  <p style="margin:0 0 24px;color:${MUTED};font-size:15px;">javieraguilar.ai</p>
  <p style="padding:14px 16px;background:#f5f5ff;border-left:3px solid ${ACCENT};font-size:15px;line-height:1.6;margin:0;">${escapeHtml(
    headline
  )}</p>
  ${buildTable(rows, copy)}
  <p style="font-size:15px;line-height:1.6;">${copy.outro}</p>
  <p style="font-size:13px;color:${MUTED};margin-top:32px;">${copy.footer}</p>
</div>
</body>
</html>`;
}

async function brevo(path: string, body: unknown, apiKey: string): Promise<Response> {
  return fetch(`${BREVO_API}${path}`, {
    method: 'POST',
    headers: {
      'api-key': apiKey,
      // charset matters: without it accented characters come out mangled.
      'content-type': 'application/json; charset=utf-8',
      accept: 'application/json'
    },
    body: JSON.stringify(body)
  });
}

export const POST: APIRoute = async ({ request }) => {
  const env = import.meta.env;
  const apiKey = env.BREVO_API_KEY;
  const sender = env.BREVO_SENDER_EMAIL;

  if (!apiKey || !sender) {
    console.error('[assessment] Brevo is not configured (missing key or sender)');
    return new Response(JSON.stringify({ ok: false, error: 'not_configured' }), { status: 500 });
  }

  let payload: Payload;
  try {
    payload = (await request.json()) as Payload;
  } catch {
    return new Response(JSON.stringify({ ok: false, error: 'bad_request' }), { status: 400 });
  }

  const email = String(payload.email ?? '').trim();
  if (!email || !email.includes('@') || !payload.result) {
    return new Response(JSON.stringify({ ok: false, error: 'bad_request' }), { status: 400 });
  }

  const lang: 'en' | 'es' = payload.lang === 'es' ? 'es' : 'en';
  const copy = COPY[lang];
  const levelNames =
    lang === 'es'
      ? ['No lo sé', 'Consciente', 'Con soltura', 'Con criterio']
      : ["Didn't know", 'Aware', 'Fluent', 'Opinionated'];

  const attachment = Buffer.from(buildAttachment(payload, lang, levelNames), 'utf8').toString('base64');

  // 1. Send them their map. This is what they asked for, so it must not depend
  //    on anything else succeeding.
  const send = await brevo(
    '/smtp/email',
    {
      sender: { email: sender, name: env.BREVO_SENDER_NAME || 'Javier Aguilar' },
      replyTo: env.BREVO_REPLY_TO ? { email: env.BREVO_REPLY_TO } : undefined,
      to: [{ email }],
      subject: copy.subject,
      htmlContent: buildEmail(payload, lang, levelNames),
      attachment: [{ content: attachment, name: copy.fileName }]
    },
    apiKey
  );

  if (!send.ok) {
    console.error('[assessment] send failed', send.status, await send.text());
    return new Response(JSON.stringify({ ok: false, error: 'send_failed' }), { status: 502 });
  }

  // 2. Add to the list only if they left the box ticked. A failure here must
  //    not make the request look failed to someone who already got their map.
  if (payload.subscribe && env.BREVO_LIST_ID) {
    const add = await brevo(
      '/contacts',
      {
        email,
        listIds: [Number(env.BREVO_LIST_ID)],
        updateEnabled: true,
        attributes: { ASSESSMENT_UNKNOWN: payload.unknown, ASSESSMENT_LANG: lang }
      },
      apiKey
    );
    if (!add.ok) {
      const detail = await add.text();
      // 400 duplicate_parameter just means they were already on the list.
      if (!detail.includes('duplicate_parameter')) {
        console.error('[assessment] list add failed', add.status, detail);
      }
    }
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 200,
    headers: { 'content-type': 'application/json; charset=utf-8' }
  });
};
