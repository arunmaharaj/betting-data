import json, math, collections
N=12  # max goals tracked per side
import numpy as np
def dist(base_h, base_a, lead=0.92, trail=1.10, steps=90, h1=45):
    """Exact minute-by-minute Markov chain on (home goals, away goals).
    Each minute: at most one goal. Rate depends on game state (leader slows, trailer pushes)."""
    M=N+1; S=np.zeros((M,M)); S[0,0]=1.0; half=None
    I,J=np.indices((M,M))
    mh=np.where(I>J,lead,np.where(I<J,trail,1.0)); ma=np.where(J>I,lead,np.where(J<I,trail,1.0))
    ph=np.minimum(base_h*mh,0.5); pa=np.minimum(base_a*ma,0.5)
    for m in range(steps):
        nx=S*(1-ph-pa)
        nx[1:,:]+=(S*ph)[:-1,:]; nx[:,1:]+=(S*pa)[:,:-1]
        S=nx
        if m+1==h1: half=S.copy()
    return S,half
def tot_dist(S):
    t=collections.defaultdict(float)
    for h in range(S.shape[0]):
        for a in range(S.shape[1]): t[h+a]+=S[h,a]
    return t
def expected(S):
    I,J=np.indices(S.shape); return float(((I+J)*S).sum())
def calibrate(total, share, **kw):
    lo,hi=0.0,3.0
    for _ in range(30):
        s=(lo+hi)/2
        St,_=dist(total*share*s/90, total*(1-share)*s/90, **kw)
        if expected(St)<total: lo=s
        else: hi=s
    s=(lo+hi)/2
    return (total*share*s)/90,(total*(1-share)*s)/90
def poisson_under(total,k):
    return sum(math.exp(-total)*total**i/math.factorial(i) for i in range(int(k)+1))
def run(total, share):
    bh,ba=calibrate(total,share)
    st,half=dist(bh,ba)
    t=tot_dist(st); th=tot_dist(half)
    cum=lambda d,k: sum(p for g,p in d.items() if g<=k)
    return {"u15":cum(t,1),"u25":cum(t,2),"u35":cum(t,3),"h1_u15":cum(th,1),"exp_total":round(expected(st),3),
            "poisson_u25":poisson_under(total,2),"poisson_u35":poisson_under(total,3)}
if __name__=="__main__":
    d=json.load(open('/home/claude/bd-repo/picks.json'))
    games=collections.OrderedDict()
    for p in d['picks']:
        key=(p['date'],p['match'])
        g=games.setdefault(key,{"date":p['date'],"match":p['match'],"league":p.get('league'),"total":None,"hw":None,"aw":None,"dg_over25":None,"goals":None,"void":True})
        i=p.get('inputs') or {}
        if i.get('projected_total') and g['total'] is None: g['total']=i['projected_total']
        if i.get('home_win_pct') is not None: g['hw'],g['aw']=i['home_win_pct'],i['away_win_pct']
        if p['bet_type']=='single' and p.get('line')==2.5 and p.get('line_group')=='main' and p.get('model_prob') is not None:
            g['dg_over25']=p['model_prob'] if p['side']=='over' else 1-p['model_prob']
        if p.get('home_goals') is not None and p.get('result') in ('win','loss'):
            g['goals']=p['home_goals']+p['away_goals']; g['void']=False
    out=[]
    for g in games.values():
        if not g['total']: continue
        share=0.54 if g['hw'] is None else min(0.7,max(0.3,0.5+(g['hw']-g['aw'])/200))
        r=run(g['total'],share)
        out.append({"date":g['date'],"match":g['match'],"league":g['league'],"projected_total":g['total'],"home_share":round(share,2),
          "markov_u25":round(r['u25'],4),"markov_u35":round(r['u35'],4),"markov_u15":round(r['u15'],4),"markov_h1_u15":round(r['h1_u15'],4),
          "poisson_u25":round(r['poisson_u25'],4),"poisson_u35":round(r['poisson_u35'],4),
          "dg_u25":None if g['dg_over25'] is None else round(1-g['dg_over25'],4),
          "total_goals":g['goals'],"result_u25":None if g['goals'] is None else int(g['goals']<=2),"result_u35":None if g['goals'] is None else int(g['goals']<=3)})
    json.dump({"description":"Side experiment, not used for any pick. Markov chain on the score, minute by minute, with a leader-slows and trailer-pushes effect, calibrated to the projected total. Compared with DataGaffer's own chance and a plain Poisson model.",
      "model":{"minutes":90,"leader_rate_multiplier":0.92,"trailing_rate_multiplier":1.10,"first_half_minutes":45,"home_share":"from win percents, else 54%"},
      "built":"2026-11-07","games":out},open('/home/claude/bd-repo/markov_sim.json','w'),indent=1)
    print(len(out))
    # quick scoring
    def brier(key):
        v=[(g[key],g['result_u25']) for g in out if g[key] is not None and g['result_u25'] is not None]
        return len(v),sum((p-y)**2 for p,y in v)/len(v) if v else None
    for k in ('markov_u25','poisson_u25','dg_u25'): print(k,brier(k))
    v=[g for g in out if g['dg_u25'] is not None and g['result_u25'] is not None]
    print('common',len(v),[ (k,round(sum((g[k]-g['result_u25'])**2 for g in v)/len(v),4)) for k in ('markov_u25','poisson_u25','dg_u25')])
    print('avg p',[round(sum(g[k] for g in v)/len(v),3) for k in ('markov_u25','poisson_u25','dg_u25')],'actual',round(sum(g['result_u25'] for g in v)/len(v),3))
