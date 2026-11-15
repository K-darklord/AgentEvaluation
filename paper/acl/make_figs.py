"""Figures for the three-model paper. Numbers are copied from the frozen read-outs
(two_model_scores.json, third_model_readout.json, search_not_verification.json)."""
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'serif','font.serif':['STIXGeneral','Times New Roman','DejaVu Serif'],'mathtext.fontset':'stix','font.size':8,'axes.linewidth':0.6,'pdf.fonttype':42})
INK='#1a1a19'; MUTED='#6b6a63'; GRID='#e3e2dc'; BLUE='#2a78d6'; ORANGE='#eb6834'; AQUA='#1baf7a'; VIOLET='#7a5cd6'
NAMES=['Reassuring loop','Generic-doubt loop','Independent samples','Critique loop']
# (selected, reached) per condition, same order as NAMES
D={'DeepSeek':dict(greedy=113,v=[(145.0,153),(146.1,171),(136.7,190),(157.4,198)]),
   'Qwen':dict(greedy=69,v=[(90.8,123),(95.6,149),(91.0,171),(114.1,182)]),
   'MiniMax':dict(greedy=81,v=[(101.7,125),(102.3,128),(94.7,173),(106.9,152)])}
fig,axes=plt.subplots(3,1,figsize=(3.03,2.95),gridspec_kw={"hspace":0.72})
for ax,(model,d) in zip(axes,D.items()):
    rows=list(zip(NAMES,d['v']))[::-1]
    for i,(name,(sel,ceil)) in enumerate(rows):
        ax.plot([sel,ceil],[i,i],color=BLUE,lw=1.6,solid_capstyle='round',zorder=2)
        ax.plot(sel,i,'o',ms=5,mfc=BLUE,mec='white',mew=0.8,zorder=3); ax.plot(ceil,i,'o',ms=5,mfc='white',mec=BLUE,mew=1.2,zorder=3)
        ax.text(sel-4,i,f'{sel:.0f}',ha='right',va='center',fontsize=7,color=INK); ax.text(ceil+4,i,f'{ceil:.0f}',ha='left',va='center',fontsize=7,color=INK)
    ax.axvline(d['greedy'],color=MUTED,lw=0.7,ls=(0,(3,2)),zorder=1)
    ax.text(d['greedy'],len(rows)-0.42,f"first answer {d['greedy']}",ha='center',va='bottom',fontsize=6.5,color=MUTED)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows],color=INK)
    ax.set_ylim(-0.6,len(rows)-0.25); ax.set_xlim(40,222)
    ax.set_title(model,loc='left',fontsize=8,color=INK,pad=10)
    for s in ('top','right','left'): ax.spines[s].set_visible(False)
    ax.tick_params(axis='y',length=0); ax.tick_params(axis='x',length=2,colors=MUTED,labelsize=7)
    ax.xaxis.grid(True,color=GRID,lw=0.5); ax.set_axisbelow(True)
axes[-1].set_xlabel('questions answered correctly (of 400)',color=INK)
h1,=axes[0].plot([],[],'o',ms=5,mfc=BLUE,mec='white',mew=0.8,label='selected'); h2,=axes[0].plot([],[],'o',ms=5,mfc='white',mec=BLUE,mew=1.2,label='reached')
fig.legend(handles=[h1,h2],loc='upper right',bbox_to_anchor=(0.99,1.0),ncol=2,frameon=False,fontsize=7,handletextpad=0.2,columnspacing=0.9)
fig.savefig('figs/reach_select.pdf',bbox_inches='tight',pad_inches=0.02); fig.savefig('figs/reach_select.png',dpi=200,bbox_inches='tight')
# ---------- Figure 2: conversion against how often the answer changes ----------
SW={'DeepSeek':[.372,.497,.631,.661],'Qwen':[.404,.561,.707,.672],'MiniMax':[.364,.412,.682,.593]}
CV={'DeepSeek':[.947,.854,.720,.795],'Qwen':[.738,.642,.532,.627],'MiniMax':[.813,.799,.548,.703]}
MK=['o','s','^','D']; COL={'DeepSeek':BLUE,'Qwen':ORANGE,'MiniMax':AQUA}
fig,ax=plt.subplots(figsize=(3.03,2.0))
for m in SW:
    order=sorted(range(4),key=lambda i:SW[m][i])
    ax.plot([SW[m][i] for i in order],[CV[m][i] for i in order],color=COL[m],lw=0.9,alpha=0.55,zorder=1)
    for i in range(4): ax.plot(SW[m][i],CV[m][i],MK[i],ms=5.2,mfc=COL[m],mec='white',mew=0.7,zorder=3)
    j=min(range(4),key=lambda i:SW[m][i]); ax.text(SW[m][j]-0.012,CV[m][j],m,ha='right',va='center',fontsize=7,color=INK)
hs=[ax.plot([],[],MK[i],ms=5,mfc=MUTED,mec='white',mew=0.7,label=NAMES[i])[0] for i in range(4)]
ax.legend(handles=hs,loc='lower left',frameon=False,fontsize=6.6,handletextpad=0.2,borderaxespad=0.1,labelspacing=0.25)
ax.set_xlabel('probability that the next answer differs',color=INK); ax.set_ylabel('conversion (selected / reached)',color=INK)
ax.set_xlim(0.24,0.74); ax.set_ylim(0.45,1.0)
for s in ('top','right'): ax.spines[s].set_visible(False)
ax.tick_params(length=2,colors=MUTED,labelsize=7); ax.yaxis.grid(True,color=GRID,lw=0.5); ax.set_axisbelow(True)
fig.savefig('figs/conversion.pdf',bbox_inches='tight',pad_inches=0.02); fig.savefig('figs/conversion.png',dpi=200,bbox_inches='tight')
# ---------- Figure 3 (appendix): selected-answer differences ----------
comp=['Reassuring loop','Generic-doubt loop','Independent samples']
series=[('DeepSeek',BLUE,'o',[(12.4,-1.6,25.6),(11.3,-0.8,23.7),(20.7,9.0,32.4)]),
        ('Qwen',ORANGE,'s',[(23.3,8.8,39.2),(18.5,3.9,34.3),(23.1,9.6,38.6)]),
        ('MiniMax',AQUA,'^',[(5.2,-6.9,18.0),(4.6,-8.4,16.8),(12.2,1.0,24.0)]),
        ('mean of three',VIOLET,'D',[(13.6,5.1,22.2),(11.5,3.4,20.1),(18.7,10.7,26.4)])]
fig,ax=plt.subplots(figsize=(3.03,2.3)); off=[0.3,0.1,-0.1,-0.3]
for (name,col,mk,vals),o in zip(series,off):
    for j,(m,lo,hi) in enumerate(vals):
        y=len(comp)-1-j+o; ax.plot([lo,hi],[y,y],color=col,lw=1.3,solid_capstyle='round',zorder=2)
        ax.plot(m,y,mk,ms=4.4,mfc=col,mec='white',mew=0.7,zorder=3,label=name if j==0 else None)
ax.axvline(0,color=INK,lw=0.7,zorder=1); ax.set_yticks(range(len(comp))); ax.set_yticklabels(comp[::-1],color=INK); ax.set_ylim(-0.6,len(comp)-0.35)
ax.set_xlabel('critique loop minus comparator, selected (questions of 400)',color=INK,fontsize=7.5)
for s in ('top','right','left'): ax.spines[s].set_visible(False)
ax.tick_params(axis='y',length=0); ax.tick_params(axis='x',length=2,colors=MUTED,labelsize=7); ax.xaxis.grid(True,color=GRID,lw=0.5); ax.set_axisbelow(True); ax.set_xlim(-10,42)
ax.legend(loc='lower center',bbox_to_anchor=(0.36,1.0),ncol=4,frameon=False,fontsize=6.6,handletextpad=0.1,columnspacing=0.6)
fig.savefig('figs/forest.pdf',bbox_inches='tight',pad_inches=0.02); fig.savefig('figs/forest.png',dpi=200,bbox_inches='tight')
