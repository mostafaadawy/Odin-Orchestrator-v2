import json,os,datetime
import sys
CONS=sys.argv[1] if len(sys.argv)>1 else "."
L=sorted([json.loads(l) for l in open(CONS+"/_consolidation/results/claude_calls.jsonl")],key=lambda x:x["t_start"])
S=CONS+"/_research/phase4/results/scenarios/"
out={}
for f in ['normal_r1','jev_r1','normal_r2','jev_r2','normal_r3']:
    runs=json.load(open(S+f+'.json')); end=os.path.getmtime(S+f+'.json')
    # walk back: each run's end = next run's start (approx); gaps absorbed
    wins=[]
    for r in reversed(runs):
        wins.append((end-r['seconds']-2,end+1,r)); end=end-r['seconds']-1.5
    for lo,hi,r in reversed(wins):
        if r['kind']!='project_run': continue
        C=[x for x in L if lo<=x['t_start']<=hi]
        st=[(round(x['t_start']-lo,1),round((x['t_end']-x['t_start']),1),x.get('num_turns')) for x in C]
        llm=sum(x['t_end']-x['t_start'] for x in C)
        print(f"{f:10} {r['pid'][:12]:12} total {r['seconds']:6.1f}s  llm_calls {len(C)}  llm_time {llm:6.1f}s  other {r['seconds']-llm:5.1f}s  calls(start,dur,turns)={st}")
import statistics as st
agg={'normal':{'pre':[],'agent':[],'review':[],'turns':[],'total':[]},'jev':{'pre':[],'agent':[],'review':[],'turns':[],'total':[]}}
for f in ['normal_r1','jev_r1','normal_r2','jev_r2','normal_r3']:
    runs=json.load(open(S+f+'.json')); end=os.path.getmtime(S+f+'.json'); wins=[]
    for r in reversed(runs): wins.append((end-r['seconds']-2,end+1,r)); end=end-r['seconds']-1.5
    m='jev' if f.startswith('jev') else 'normal'
    for lo,hi,r in wins:
        if r['kind']!='project_run': continue
        C=[x for x in L if lo<=x['t_start']<=hi]; d=[x['t_end']-x['t_start'] for x in C]
        agg[m]['pre'].append(sum(d[:-2])+C[0]['t_start']-lo); agg[m]['agent'].append(d[-2]); agg[m]['review'].append(d[-1]); agg[m]['turns'].append(C[-2]['num_turns']); agg[m]['total'].append(r['seconds'])
for m,a in agg.items(): print(m, len(a['total']), {k:(round(st.mean(v),1), round(st.median(v),1)) for k,v in a.items()})
