"""Bilingual article figures; observed decisions come from the frozen export."""
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR','/tmp/prompt-meaning-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import protocol

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'public/blog'
SLUG='now-it-seems-to-mean-something'
DATA=json.loads((HERE/'results/supplement-data.json').read_text())
BG,FG,MUTED,TEAL,AMBER,RED,SLATE='#1a1a24','#f8fafc','#a8b5c8','#2dd4bf','#fbbf24','#fb7185','#64748b'
plt.rcParams.update({'font.family':'DejaVu Sans','text.color':FG,'figure.facecolor':BG,
                     'axes.facecolor':BG,'savefig.facecolor':BG})


def canvas(height):
    fig,ax=plt.subplots(figsize=(12,height),dpi=160)
    fig.subplots_adjust(0,0,1,1);ax.set(xlim=(0,12),ylim=(0,height));ax.axis('off')
    return fig,ax


def save(fig,n,lang):
    suffix='-es' if lang=='es' else ''
    fig.savefig(OUT/f'{SLUG}-fig-{n}{suffix}.png');plt.close(fig)


def handoffs(lang):
    es=lang=='es';fig,ax=canvas(4)
    ax.text(.4,3.5,'La condición se pierde en la primera nota' if es else
            'The condition is lost in the first note',fontsize=23,weight='bold')
    labels=[('Código + tests','Dentro del bucle'),('GPT','Primera nota'),('Claude','Nota de revisión'),('GPT','Nota final')] if es else [
        ('Code + tests','Inside the loop'),('GPT','First note'),('Claude','Reviewer brief'),('GPT','Final note')]
    for i,(title,sub) in enumerate(labels):
        x=.4+i*2.95;color=TEAL if i==0 else AMBER
        ax.add_patch(FancyBboxPatch((x,1.8),2.25,1.1,boxstyle='round,pad=0.06',
                                   facecolor='#222635',edgecolor=color,lw=1.5))
        ax.text(x+1.125,2.48,title,ha='center',fontsize=18,weight='bold',color=color)
        ax.text(x+1.125,2.05,sub,ha='center',fontsize=15)
        if i<3:ax.annotate('',xy=(x+2.84,2.35),xytext=(x+2.36,2.35),
                          arrowprops=dict(arrowstyle='->',color=MUTED,lw=1.8))
    ax.plot([3.35,3.35,11.5,11.5],[1.5,1.25,1.25,1.5],color=AMBER,lw=1.2)
    ax.text(7.4,.88,'La definición abreviada se conserva' if es else
            'The shortened definition is preserved',ha='center',fontsize=18,color=AMBER)
    ax.text(.4,.28,'Sesiones nuevas; cada receptor ve solo la nota anterior.' if es else
            'Fresh sessions; each recipient sees only the previous note.',fontsize=14,color=MUTED)
    save(fig,1,lang)


def decision(model,variant,rep):
    rec=next(r for r in DATA['records'] if r['job']['model_id']==model and
             r['job']['variant']==variant and r['job']['rep']==rep)
    response=rec['attempts'][-1]
    try:
        if response['status']!='ok' or response.get('truncated'):return 'invalid'
        return protocol.parse(response['text'],DATA['tasks'][0]['cases'])['s01']['decision']
    except (ValueError,TypeError,KeyError):return 'invalid'


def results(lang):
    es=lang=='es';fig,ax=canvas(6.4)
    ax.text(.4,5.92,'¿Aceptaría devolver True con cero iteraciones?' if es else
            'Would it accept returning True with zero iterations?',fontsize=22,weight='bold')
    ax.text(.4,5.43,'El código devuelve False: rechazar el cambio es correcto.' if es else
            'The code returns False: rejecting the change is correct.',fontsize=17,color=MUTED)
    ax.text(6.25,4.82,'GPT-5.6 Sol',ha='center',fontsize=19,weight='bold')
    ax.text(9.75,4.82,'Claude Opus 5',ha='center',fontsize=19,weight='bold')
    rows=[('full','Código, planes y tests' if es else 'Code, plans and tests'),
          ('first','Primera nota' if es else 'First note'),
          ('last','Tercera nota' if es else 'Third note'),
          ('opaque','Tercera nota renombrada' if es else 'Third note, renamed')]
    labels={'accept':'Acepta' if es else 'Accept', 'reject':'Rechaza' if es else 'Reject',
            'needs_context':'Contexto' if es else 'Context', 'invalid':'Inválida' if es else 'Invalid'}
    colors={'accept':RED,'reject':TEAL,'needs_context':AMBER,'invalid':MUTED}
    for idx,(variant,label) in enumerate(rows):
        y=4.1-idx*.82
        ax.text(.4,y,label,fontsize=17,va='center')
        for model,xs in [('gpt-sol',(5.45,7.05)),('claude-opus',(8.95,10.55))]:
            for rep,x in enumerate(xs):
                d=decision(model,variant,rep);color=colors[d]
                ax.add_patch(FancyBboxPatch((x-.68,y-.22),1.36,.44,boxstyle='round,pad=0.04',
                                           facecolor='#252938',edgecolor=color,lw=1))
                ax.text(x,y,labels[d],color=color,ha='center',va='center',fontsize=15,weight='bold')
        ax.plot([.4,11.6],[y-.4,y-.4],color=SLATE,lw=.5,alpha=.6)
    ax.text(.4,.74,'Cada celda es una llamada. Contexto = pide información adicional.' if es else
            'Each cell is one call. Context = asks for additional information.',fontsize=14,color=MUTED)
    ax.text(.4,.32,'Un solo caso; una respuesta con JSON incompleto se excluye entera.' if es else
            'One case; one response with incomplete JSON is excluded in full.',fontsize=14,color=MUTED)
    save(fig,2,lang)


if __name__=='__main__':
    for lang in ('es','en'):handoffs(lang);results(lang)
    print('Rendered four bilingual figures from the fourth study.')
