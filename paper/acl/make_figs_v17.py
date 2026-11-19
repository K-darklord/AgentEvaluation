"""Figure 1 of v17: reached and selected questions at equal tokens in the three cells.
Numbers are read from the frozen read-outs (experiments/hle400/t3/*.json); nothing is typed by hand."""
import json, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
T='../../experiments/hle400/t3/'
E2=json.load(open(T+'equal_token_samples_readout.json')); BE=json.load(open(T+'bbeh_equal_token_readout.json'))
S1=json.load(open(T+'selection_confirmation_readout.json')); DS=json.load(open(T+'selection_confirmation_ds_readout.json')); BB=json.load(open(T+'second_benchmark_readout.json'))
def hle(o): c=o['conditions']; return [(c['equal-token samples']['selected'],c['equal-token samples']['reached']),(c['token-yoked generic doubt']['selected'],c['token-yoked generic doubt']['reached']),(c['critique']['selected'],c['critique']['reached'])]
b=BE['conditions']
CELLS=[('Qwen, HLE (800 new questions)',S1['conditions']['first answer']['selected'],hle(E2['qwen'])),
       ('DeepSeek, HLE (800 new questions)',DS['conditions']['first answer']['selected'],hle(E2['deepseek'])),
       ('Qwen, BBEH hard tasks (800 questions)',BB['hard']['first_answer_correct'],[(b[a]['selected'],b[a]['reached']) for a in ('A3Y','A2PY','C2')])]
NAMES=['Independent samples','Token-yoked doubt loop','Critique loop']
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],'font.size':8,'axes.linewidth':0.6})
INK='#1a1a19'; MUTED='#6b6a63'; GRID='#e3e2dc'; BLUE='#2a78d6'
fig,axes=plt.subplots(3,1,figsize=(3.03,3.1),gridspec_kw={'hspace':0.95})
for ax,(title,first,vals) in zip(axes,CELLS):
    for i,(name,(sel,rea)) in enumerate(zip(NAMES,vals)):
        ax.plot([sel,rea],[i,i],color=BLUE,lw=1.6,solid_capstyle='round',zorder=2)
        ax.plot(sel,i,'o',ms=5,mfc=BLUE,mec='white',mew=0.8,zorder=3); ax.plot(rea,i,'o',ms=5,mfc='white',mec=BLUE,mew=1.2,zorder=3)
        ax.text(sel-5,i,f'{sel:.0f}',ha='right',va='center',fontsize=7,color=INK); ax.text(rea+5,i,f'{rea:.0f}',ha='left',va='center',fontsize=7,color=INK)
    ax.axvline(first,color=MUTED,lw=0.7,ls=(0,(3,2)),zorder=1)
    ax.text(first,2.55,f'first answer {first:.0f}',ha='center',va='bottom',fontsize=6.5,color=MUTED)
    lo=first-25; hi=max(r for _,r in vals)+45; ax.set_xlim(lo,hi)
    ax.set_yticks(range(3)); ax.set_yticklabels(NAMES,color=INK); ax.set_ylim(-0.6,2.75)
    ax.set_title(title,loc='left',fontsize=8,color=INK,pad=11)
    for s in ('top','right','left'): ax.spines[s].set_visible(False)
    ax.tick_params(axis='y',length=0); ax.tick_params(axis='x',length=2,colors=MUTED,labelsize=7)
    ax.xaxis.grid(True,color=GRID,lw=0.5); ax.set_axisbelow(True)
axes[-1].set_xlabel('questions answered correctly (of 800)',color=INK)
h1,=axes[0].plot([],[],'o',ms=5,mfc=BLUE,mec='white',mew=0.8,label='selected'); h2,=axes[0].plot([],[],'o',ms=5,mfc='white',mec=BLUE,mew=1.2,label='reached')
fig.legend(handles=[h1,h2],loc='upper right',bbox_to_anchor=(0.99,1.01),ncol=2,frameon=False,fontsize=7,handletextpad=0.2,columnspacing=0.9)
fig.savefig('figs/equal_tokens.pdf',bbox_inches='tight',pad_inches=0.02); fig.savefig('figs/equal_tokens.png',dpi=220,bbox_inches='tight')
print([ (c[0],c[1],c[2]) for c in CELLS])
