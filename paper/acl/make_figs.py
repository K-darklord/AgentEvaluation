import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'serif','font.serif':['STIXGeneral','Times New Roman','DejaVu Serif'],'mathtext.fontset':'stix','font.size':8,'axes.linewidth':0.6,'pdf.fonttype':42})
INK='#1a1a19'; MUTED='#6b6a63'; GRID='#e3e2dc'; BLUE='#2a78d6'; ORANGE='#eb6834'; AQUA='#1baf7a'
# ---------- Figure 1: reached vs selected ----------
data={'deepseek-v4-flash':dict(greedy=113,rows=[('Reassuring placebo',145.0,153),('Perturbing placebo',146.1,171),('Self-consistency (9)',136.7,190),('Bank critic',150.9,192),('Free critic',157.4,198)]),
      'qwen3.8-flash':dict(greedy=69,rows=[('Reassuring placebo',90.8,123),('Perturbing placebo',95.6,149),('Self-consistency (9)',91.0,171),('Free critic',114.1,182)])}
fig,axes=plt.subplots(2,1,figsize=(3.03,3.3),gridspec_kw={'height_ratios':[5,4],'hspace':0.55})
for ax,(model,d) in zip(axes,data.items()):
    rows=d['rows'][::-1]
    for i,(name,sel,ceil) in enumerate(rows):
        ax.plot([sel,ceil],[i,i],color=BLUE,lw=1.6,solid_capstyle='round',zorder=2)
        ax.plot(sel,i,'o',ms=5,mfc=BLUE,mec='white',mew=0.8,zorder=3)
        ax.plot(ceil,i,'o',ms=5,mfc='white',mec=BLUE,mew=1.2,zorder=3)
        ax.text(sel-4,i,f'{sel:.0f}',ha='right',va='center',fontsize=7,color=INK)
        ax.text(ceil+4,i,f'{ceil:.0f}',ha='left',va='center',fontsize=7,color=INK)
    ax.axvline(d['greedy'],color=MUTED,lw=0.7,ls=(0,(3,2)),zorder=1)
    ax.text(d['greedy'],len(rows)-0.42,f"greedy {d['greedy']}",ha='center',va='bottom',fontsize=6.5,color=MUTED)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows],color=INK)
    ax.set_ylim(-0.6,len(rows)-0.25); ax.set_xlim(40,222)
    ax.set_title(model,loc='left',fontsize=8,color=INK,pad=11)
    for s in ('top','right','left'): ax.spines[s].set_visible(False)
    ax.tick_params(axis='y',length=0); ax.tick_params(axis='x',length=2,colors=MUTED,labelsize=7)
    ax.xaxis.grid(True,color=GRID,lw=0.5); ax.set_axisbelow(True)
axes[1].set_xlabel('correct items (of 400)',color=INK)
h1,=axes[0].plot([],[],'o',ms=5,mfc=BLUE,mec='white',mew=0.8,label='selected'); h2,=axes[0].plot([],[],'o',ms=5,mfc='white',mec=BLUE,mew=1.2,label='reached')
fig.legend(handles=[h1,h2],loc='upper right',bbox_to_anchor=(0.99,1.0),ncol=2,frameon=False,fontsize=7,handletextpad=0.2,columnspacing=0.9)
fig.savefig('figs/reach_select.pdf',bbox_inches='tight',pad_inches=0.02); fig.savefig('figs/reach_select.png',dpi=220,bbox_inches='tight')
# ---------- Figure 2: forest plot ----------
comp=['Reassuring placebo','Perturbing placebo','Self-consistency']
series=[('deepseek-v4-flash',BLUE,'o',[(12.4,-1.6,25.6),(11.3,-0.8,23.7),(20.7,9.0,32.4)]),
        ('qwen3.8-flash',ORANGE,'s',[(23.3,8.8,39.2),(18.5,3.9,34.3),(23.1,9.6,38.6)]),
        ('mean of both',AQUA,'D',[(17.9,7.8,28.5),(14.9,5.3,25.7),(21.9,12.3,31.6)])]
fig,ax=plt.subplots(figsize=(3.03,2.0))
off=[0.24,0,-0.24]
for (name,col,mk,vals),o in zip(series,off):
    for j,(m,lo,hi) in enumerate(vals):
        y=len(comp)-1-j+o
        ax.plot([lo,hi],[y,y],color=col,lw=1.3,solid_capstyle='round',zorder=2)
        ax.plot(m,y,mk,ms=4.6,mfc=col,mec='white',mew=0.7,zorder=3,label=name if j==0 else None)
ax.axvline(0,color=INK,lw=0.7,zorder=1)
ax.set_yticks(range(len(comp))); ax.set_yticklabels(comp[::-1],color=INK); ax.set_ylim(-0.55,len(comp)-0.3)
ax.set_xlabel('free critic minus comparator, selected answer (items of 400)',color=INK,fontsize=7.5)
for s in ('top','right','left'): ax.spines[s].set_visible(False)
ax.tick_params(axis='y',length=0); ax.tick_params(axis='x',length=2,colors=MUTED,labelsize=7)
ax.xaxis.grid(True,color=GRID,lw=0.5); ax.set_axisbelow(True); ax.set_xlim(-6,42)
ax.legend(loc='lower center',bbox_to_anchor=(0.36,1.0),ncol=3,frameon=False,fontsize=7,handletextpad=0.1,columnspacing=0.8)
fig.savefig('figs/forest.pdf',bbox_inches='tight',pad_inches=0.02); fig.savefig('figs/forest.png',dpi=220,bbox_inches='tight')
