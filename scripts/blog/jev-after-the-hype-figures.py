"""Figures for the readable Jev article. Aggregate data only.
Run: python scripts/blog/jev-after-the-hype-figures.py
Email costs are offline pilot estimates for the second analysis stage.
"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parents[2] / 'public' / 'blog'
BG, FG, MUTED, TEAL, AMBER = '#1a1a24', '#f8fafc', '#94a3b8', '#2dd4bf', '#fbbf24'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,
    'text.color':FG,'axes.labelcolor':FG,'xtick.color':MUTED,'ytick.color':FG,
    'axes.facecolor':BG,'figure.facecolor':BG,'savefig.facecolor':BG})
for lang in ('es','en'):
    es = lang == 'es'
    fig,ax=plt.subplots(figsize=(10,5.0))
    ax.set_xlim(0,10); ax.set_ylim(0,5); ax.axis('off')
    ax.text(.2,4.65,'Dónde he probado Jev' if es else 'Where I have tested Jev',fontsize=23,weight='bold')
    rows=([('PERSONAL','Mi trabajo con agentes','Elegir modelo y revisar comandos'),
           ('PRODUCTIVO','Los productos que desarrollo','Detectar fraude y comprobar datos'),
           ('INFRAESTRUCTURA','El entorno donde puedo usarlo','Respetar las condiciones del cliente')]
          if es else
          [('PERSONAL','My work with agents','Choose models and assess commands'),
           ('PRODUCT','The products I develop','Detect fraud and check data'),
           ('INFRASTRUCTURE','Where I can use it','Meet the client’s requirements')])
    for i,(label,example,purpose) in enumerate(rows):
        y=3.15-i*1.3
        ax.add_patch(FancyBboxPatch((.15,y),9.7,1.05,boxstyle='round,pad=.08',facecolor='#242432',edgecolor='#455064'))
        ax.text(.4,y+.65,label,fontsize=11,weight='bold',color=TEAL if i<2 else AMBER)
        ax.text(.4,y+.22,example,fontsize=13)
        ax.text(5.25,y+.42,purpose,fontsize=12,va='center')
    fig.subplots_adjust(left=.02,right=.98,top=.98,bottom=.02)
    fig.savefig(OUT/f'jev-after-the-hype-levels-{lang}.png',dpi=160);plt.close(fig)

    fig,ax=plt.subplots(figsize=(10,4.6))
    values=[11.90,5.30]
    labels=['Sonnet en cada revisión','Jev filtra; Sonnet revisa las dudas'] if es else ['Sonnet for every review','Jev filters; Sonnet reviews uncertain cases']
    ax.barh([0,1],values,color=[MUTED,TEAL],height=.42)
    ax.set_yticks([0,1],labels,fontsize=11);ax.invert_yaxis()
    ax.set_xlim(0,13.8);ax.set_xticks([0,4,8,12])
    ax.set_xlabel('Dólares por 1.000 correos' if es else 'Dollars per 1,000 emails',labelpad=10)
    ax.spines[['top','left','right']].set_visible(False)
    ax.spines['bottom'].set_color('#64748b');ax.tick_params(axis='y',length=0,pad=12)
    for y,value in enumerate(values):
        label=(f'{value:.2f} $'.replace('.',',') if es else f'$'+f'{value:.2f}')
        ax.text(value+.2,y,label,va='center',fontsize=15,weight='bold')
    fig.suptitle('Correo: reservar el modelo caro para las dudas' if es else 'Email: reserve the expensive model for uncertain cases',fontsize=18,x=.04,ha='left',y=.95)
    fig.text(.04,.055,'Coste estimado de la segunda revisión en el piloto, no del servicio completo.' if es else 'Estimated cost of the second review in the pilot, not the complete service.',fontsize=10,color=MUTED)
    fig.subplots_adjust(left=.39,right=.96,top=.75,bottom=.27)
    fig.savefig(OUT/f'jev-after-the-hype-cost-{lang}.png',dpi=160);plt.close(fig)
print('Rendered four article figures.')
