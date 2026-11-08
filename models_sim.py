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

# ---------------------------------------------------------------------------
# Independent side models. Data collection only: nothing here feeds any pick,
# slip, record or track. Run:  python3 models_sim.py   (reads picks.json and
# league_base_rates.json, writes models_sim.json).
# ---------------------------------------------------------------------------
from math import lgamma, exp, log, factorial
MODELS=[
 {"id":"league","name":"League base rate","group":"own","desc":"How often games in the same league finished under the line this season. Needs no outlook data. Season-to-date rates include the games being scored."},
 {"id":"market","name":"Bet365 price","group":"own","desc":"Bet365 price converted to a chance, with an assumed 5% bookmaker margin removed. Needs no outlook data."},
 {"id":"poisson","name":"Poisson","group":"total","desc":"Plain Poisson goals around the projected total."},
 {"id":"negbin","name":"Negative binomial","group":"total","desc":"Like Poisson but allows more wild games (very low and very high scores) than Poisson does. Dispersion fixed at 12, not fitted."},
 {"id":"bivar","name":"Bivariate Poisson","group":"total","desc":"Home and away goals share a common source, so they move together and very high or very low totals are more likely than plain Poisson. Shared part fixed at 10%, not fitted."},
 {"id":"markov","name":"Markov chain","group":"total","desc":"Minute-by-minute score chain: the leader slows a little, the trailing team pushes a little."},
 {"id":"outlook","name":"Outlook chance","group":"outlook","desc":"The outlook data's own Under 2.5 chance, for reference. Not available for Under 3.5."},
 {"id":"blend","name":"Blend (equal mix)","group":"mix","desc":"Plain average of every model above that has a number for the game, excluding the outlook reference."},
]
MARGIN=1.05
def implied(o):
    return 100/(o+100) if o>0 else -o/(-o+100)
def nb_cdf(mean,k,r=12.0):
    p=r/(r+mean); s=0.0
    for i in range(int(k)+1):
        s+=exp(lgamma(i+r)-lgamma(r)-lgamma(i+1)+r*log(p)+i*log(1-p))
    return s
def bivar_under(total,c=0.10,mx=30):
    """Bivariate Poisson: home and away share a common goal source, so totals are more spread out.
    Total = A + 2Z with A~Poisson((1-2c)T), Z~Poisson(cT), so the mean stays equal to T."""
    la,lz=(1-2*c)*total,c*total
    pa=[exp(-la)*la**i/factorial(i) for i in range(mx+1)]
    pz=[exp(-lz)*lz**i/factorial(i) for i in range(mx//2+1)]
    tot=[0.0]*(mx+1)
    for i,x in enumerate(pa):
        for j,y in enumerate(pz):
            if i+2*j<=mx: tot[i+2*j]+=x*y
    return sum(tot[:3]),sum(tot[:4])
ALIAS={"Segunda División":"LaLiga 2","Segunda Division":"LaLiga 2","Bundesliga":"Bundesliga"}
def run_all():
    d=json.load(open('picks.json')); base=json.load(open('league_base_rates.json'))
    bl={x['league']:x for x in base['leagues']}
    games=collections.OrderedDict()
    for p in d['picks']:
        key=(p['date'],p['match'])
        g=games.setdefault(key,{"date":p['date'],"match":p['match'],"league":p.get('league'),"total":None,"hw":None,"aw":None,"dg_u25":None,"goals":None,"mk25":None,"mk35":None})
        if p.get('league') and not g['league']: g['league']=p['league']
        i=p.get('inputs') or {}
        if i.get('projected_total') and g['total'] is None: g['total']=i['projected_total']
        if i.get('home_win_pct') is not None: g['hw'],g['aw']=i['home_win_pct'],i['away_win_pct']
        if p['bet_type']=='single' and p.get('odds_american') is not None and p.get('side') in('over','under'):
            pr=min(0.98,max(0.02,implied(p['odds_american'])/MARGIN))
            pu=pr if p['side']=='under' else 1-pr
            if p.get('line')==2.5 and g['mk25'] is None: g['mk25']=pu
            if p.get('line')==3.5 and g['mk35'] is None: g['mk35']=pu
        if p['bet_type']=='single' and p.get('line')==2.5 and p.get('line_group')=='main' and p.get('model_prob') is not None:
            g['dg_u25']=1-p['model_prob'] if p['side']=='over' else p['model_prob']
        if p.get('home_goals') is not None and p.get('result') in('win','loss'):
            g['goals']=p['home_goals']+p['away_goals']
    out=[]
    for g in games.values():
        m25={};m35={}
        lg=bl.get(ALIAS.get(g['league'],g['league']))
        if lg: m25['league']=lg['under_2_5_pct']/100; m35['league']=lg['under_3_5_pct']/100
        if g['mk25'] is not None: m25['market']=g['mk25']
        if g['mk35'] is not None: m35['market']=g['mk35']
        if g['total']:
            T=g['total']; share=0.54 if g['hw'] is None else min(0.7,max(0.3,0.5+(g['hw']-g['aw'])/200))
            r=run(T,share)
            m25['poisson']=r['poisson_u25']; m35['poisson']=r['poisson_u35']
            m25['negbin']=nb_cdf(T,2); m35['negbin']=nb_cdf(T,3)
            a,b=bivar_under(T); m25['bivar']=a; m35['bivar']=b
            m25['markov']=r['u25']; m35['markov']=r['u35']
        if g['dg_u25'] is not None: m25['outlook']=g['dg_u25']
        for m in (m25,m35):
            v=[m[k] for k in ('league','market','poisson','negbin','bivar','markov') if k in m]
            if len(v)>=2: m['blend']=sum(v)/len(v)
        if not m25 and not m35: continue
        goals=g['goals']
        out.append({"date":g['date'],"match":g['match'],"league":g['league'],"projected_total":g['total'],
          "u25":{k:round(v,4) for k,v in m25.items()},"u35":{k:round(v,4) for k,v in m35.items()},
          "total_goals":goals,"res_u25":None if goals is None else int(goals<=2),"res_u35":None if goals is None else int(goals<=3)})
    out.sort(key=lambda x:(x['date'],x['match']))
    json.dump({"description":"Independent side models. Data collection only: nothing here feeds any pick, slip, record or track.",
      "built":__import__('datetime').date.today().isoformat(),"sample_target":300,"models":MODELS,"games":out},open('models_sim.json','w'),indent=1,ensure_ascii=False)
    return out
if __name__=="__main__":
    out=run_all(); print(len(out),"games")
    for mk in ('u25','u35'):
        done=[g for g in out if g['res_'+mk] is not None]
        ids=[m['id'] for m in MODELS if m['id']!='outlook' or mk=='u25']
        common=[g for g in done if all(i in g[mk] for i in ids)]
        print(mk,'scored',len(done),'common',len(common))
        for i in ids:
            v=[g for g in common]
            if v: print('  ',i,round(sum((g[mk][i]-g['res_'+mk])**2 for g in v)/len(v),4))
