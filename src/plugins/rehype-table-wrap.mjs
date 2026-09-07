/**
 * Envuelve cada <table> del markdown en <div class="table-wrap">.
 *
 * BlogLayout ya tenía los estilos de `.table-wrap` —scroll horizontal en
 * pantallas estrechas y sangrado hacia los dos márgenes en anchas— pero nada
 * generaba nunca esa clase: ni un plugin ni los propios artículos. Así que era
 * CSS muerto, y las tablas de los 38 artículos que las usan se salían del
 * viewport en móvil (661px de tabla dentro de 390px de pantalla).
 *
 * Sin dependencias: el árbol hast se recorre a mano, que para esto es media
 * docena de líneas y evita añadir unist-util-visit al proyecto.
 */
export default function rehypeTableWrap() {
  return (tree) => {
    const walk = (node) => {
      if (!Array.isArray(node.children)) return;

      node.children = node.children.map((child) => {
        walk(child);

        if (child.type !== 'element' || child.tagName !== 'table') return child;

        return {
          type: 'element',
          tagName: 'div',
          properties: { className: ['table-wrap'] },
          children: [child],
        };
      });
    };

    walk(tree);
  };
}
