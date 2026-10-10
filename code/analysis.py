#!/usr/bin/env python3
from pathlib import Path
import json, math
import numpy as np, pandas as pd
from scipy import stats, optimize
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; RES=ROOT/'results'; FIG=ROOT/'figures'; RES.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
df=pd.read_csv(DATA/'participants.csv'); exp=df[df.group_code==1].copy(); ctrl=df[df.group_code==0].copy()

def hedges(x,y):
 nx,ny=len(x),len(y); sp=math.sqrt(((nx-1)*np.var(x,ddof=1)+(ny-1)*np.var(y,ddof=1))/(nx+ny-2)); d=(np.mean(x)-np.mean(y))/sp; J=1-3/(4*(nx+ny)-9); return J*d

def welch(x,y):
 r=stats.ttest_ind(x,y,equal_var=False); vx,vy=np.var(x,ddof=1),np.var(y,ddof=1); nx,ny=len(x),len(y); se=math.sqrt(vx/nx+vy/ny); dfw=(vx/nx+vy/ny)**2/((vx/nx)**2/(nx-1)+(vy/ny)**2/(ny-1)); return {'t':r.statistic,'df':dfw,'p':r.pvalue,'diff':np.mean(x)-np.mean(y),'lo':np.mean(x)-np.mean(y)-stats.t.ppf(.975,dfw)*se,'hi':np.mean(x)-np.mean(y)+stats.t.ppf(.975,dfw)*se,'g':hedges(x,y)}

def ols(y,X):
 X=np.asarray(X,float); y=np.asarray(y,float); b=np.linalg.solve(X.T@X,X.T@y); e=y-X@b; n,p=X.shape; s2=e@e/(n-p); cov=s2*np.linalg.inv(X.T@X); se=np.sqrt(np.diag(cov)); t=b/se; pv=2*stats.t.sf(abs(t),n-p); return b,se,t,pv,e,cov,n-p

def ancova(outcome):
 y=df[outcome].values; X=np.c_[np.ones(len(df)),df.group_code,df.pre_score,df.programming_experience]; b,se,t,p,e,cov,dof=ols(y,X)
 # partial eta squared from t^2
 eta=t[1]**2/(t[1]**2+dof); return {'adjusted_difference':b[1],'se':se[1],'lo':b[1]-stats.t.ppf(.975,dof)*se[1],'hi':b[1]+stats.t.ppf(.975,dof)*se[1],'t':t[1],'df':dof,'F':t[1]**2,'p':p[1],'partial_eta2':eta,'g_unadjusted':hedges(exp[outcome],ctrl[outcome])}

def fisher_or(a,b,c,d):
 # Haldane only for interval stability, exact p from Fisher
 odds,p=stats.fisher_exact([[a,b],[c,d]]); aa,bb,cc,dd=[z+.5 for z in (a,b,c,d)]; se=math.sqrt(1/aa+1/bb+1/cc+1/dd); lo=math.exp(math.log(aa*dd/(bb*cc))-1.96*se); hi=math.exp(math.log(aa*dd/(bb*cc))+1.96*se); return {'or':odds,'lo':lo,'hi':hi,'p':p}

def glm_binomial_counts(success,total,g):
 # aggregated binomial logit, robust sandwich across students
 X=np.c_[np.ones(len(g)),g]; y=success/total
 b=np.zeros(2)
 for _ in range(100):
  eta=X@b; mu=1/(1+np.exp(-eta)); W=total*mu*(1-mu); z=eta+(y-mu)/(mu*(1-mu)); bn=np.linalg.solve(X.T@(W[:,None]*X),X.T@(W*z))
  if np.max(abs(bn-b))<1e-10: break
  b=bn
 bread=np.linalg.inv(X.T@(W[:,None]*X)); scores=X*((success-total*mu)[:,None]); meat=scores.T@scores; cov=bread@meat@bread; se=np.sqrt(np.diag(cov)); zval=b/se; p=2*stats.norm.sf(abs(zval)); return {'or':math.exp(b[1]),'lo':math.exp(b[1]-1.96*se[1]),'hi':math.exp(b[1]+1.96*se[1]),'p':p[1]}

def glm_poisson_offset(count,exposure,g):
 X=np.c_[np.ones(len(g)),g]; off=np.log(exposure); b=np.array([-7.0,0.0])
 for _ in range(100):
  mu=np.exp(off+X@b); W=mu; z=X@b+(count-mu)/mu; bn=np.linalg.solve(X.T@(W[:,None]*X),X.T@(W*(z)))
  if np.max(abs(bn-b))<1e-10: break
  b=bn
 bread=np.linalg.inv(X.T@(mu[:,None]*X)); scores=X*((count-mu)[:,None]); cov=bread@(scores.T@scores)@bread; se=np.sqrt(np.diag(cov)); z=b/se; p=2*stats.norm.sf(abs(z)); return {'irr':math.exp(b[1]),'lo':math.exp(b[1]-1.96*se[1]),'hi':math.exp(b[1]+1.96*se[1]),'p':p[1]}

def icc2k(a,b):
 Y=np.c_[a,b]; n,k=Y.shape; gm=Y.mean(); rm=Y.mean(1); cm=Y.mean(0); ssr=k*np.sum((rm-gm)**2); ssc=n*np.sum((cm-gm)**2); sse=np.sum((Y-rm[:,None]-cm[None,:]+gm)**2); msr=ssr/(n-1); msc=ssc/(k-1); mse=sse/((n-1)*(k-1)); return (msr-mse)/(msr+(msc-mse)/n)

results={'data_status':'SYNTHETIC / SIMULATION ONLY','n_experimental':len(exp),'n_comparison':len(ctrl),'seed':20261001}
results['baseline']=welch(exp.pre_score,ctrl.pre_score)
for o in ['post_score','delayed_score','ai_literacy','transfer_score']: results['ancova_'+o]=ancova(o)
# rubric means over raters
rubrics=['question','hypothesis','sources','design','provenance','reproducibility','model_choice','reflection']
art=[]
for v in rubrics:
 s=(df[v+'_r1']+df[v+'_r2'])/2; row={'criterion':v,'exp_mean':s[df.group_code==1].mean(),'exp_sd':s[df.group_code==1].std(ddof=1),'ctrl_mean':s[df.group_code==0].mean(),'ctrl_sd':s[df.group_code==0].std(ddof=1),'g':hedges(s[df.group_code==1],s[df.group_code==0])}; art.append(row)
df['artifact_total_r1']=df[[v+'_r1' for v in rubrics]].sum(axis=1); df['artifact_total_r2']=df[[v+'_r2' for v in rubrics]].sum(axis=1); df['artifact_total']=(df.artifact_total_r1+df.artifact_total_r2)/2
art.append({'criterion':'total_0_32','exp_mean':exp.index.map(df.artifact_total).to_series(index=exp.index).mean() if False else df.loc[df.group_code==1,'artifact_total'].mean(),'exp_sd':df.loc[df.group_code==1,'artifact_total'].std(ddof=1),'ctrl_mean':df.loc[df.group_code==0,'artifact_total'].mean(),'ctrl_sd':df.loc[df.group_code==0,'artifact_total'].std(ddof=1),'g':hedges(df.loc[df.group_code==1,'artifact_total'],df.loc[df.group_code==0,'artifact_total'])})
pd.DataFrame(art).to_csv(RES/'table_artifacts.csv',index=False,encoding='utf-8-sig'); results['icc2k_artifact_total']=icc2k(df.artifact_total_r1,df.artifact_total_r2)
results['verified_references']=glm_binomial_counts(df.references_verified.values,df.references_total.values,df.group_code.values)
results['unsupported_claims']=glm_poisson_offset(df.unsupported_claims.values,df.words_reviewed.values,df.group_code.values)
for v in ['reproduced','model_justified']:
 a=int(exp[v].sum()); b=len(exp)-a; c=int(ctrl[v].sum()); d=len(ctrl)-c; results[v]={'exp_n':a,'exp_N':len(exp),'ctrl_n':c,'ctrl_N':len(ctrl),**fisher_or(a,b,c,d)}
results['ai_error_found']={'n':int(exp.ai_error_found.sum()),'N':len(exp)}
# exp-only parsimonious regression: verification, log, pre (three predictors). Standardized, HC3, bootstrap CI
sub=exp.dropna(subset=['transfer_score','verification_quality','log_completeness','pre_score']).copy(); cols=['verification_quality','log_completeness','pre_score']; Z=(sub[cols]-sub[cols].mean())/sub[cols].std(ddof=1); y=(sub.transfer_score-sub.transfer_score.mean())/sub.transfer_score.std(ddof=1); X=np.c_[np.ones(len(sub)),Z]
b,se,t,p,e,cov,dof=ols(y,X); H=np.sum(X*(X@np.linalg.inv(X.T@X)),axis=1); bread=np.linalg.inv(X.T@X); meat=X.T@(((e/(1-H))**2)[:,None]*X); hc3=bread@meat@bread; seh=np.sqrt(np.diag(hc3)); ph=2*stats.t.sf(abs(b/seh),dof)
rng=np.random.default_rng(4201); boots=[]
for _ in range(2000):
 idx=rng.integers(0,len(sub),len(sub))
 try: boots.append(np.linalg.lstsq(X[idx],y.iloc[idx],rcond=None)[0])
 except: pass
boots=np.array(boots); results['regression']={cols[i]:{'beta':b[i+1],'se_hc3':seh[i+1],'p_hc3':ph[i+1],'boot_lo':np.quantile(boots[:,i+1],.025),'boot_hi':np.quantile(boots[:,i+1],.975)} for i in range(3)}; results['regression']['n']=len(sub); results['regression']['predictors']=3
# interview frequencies
ic=pd.read_csv(DATA/'interview_codes.csv'); themes=ic.groupby('theme').present.agg(['sum','count']).reset_index(); themes.to_csv(RES/'table_interviews.csv',index=False,encoding='utf-8-sig')
# descriptives
rows=[]
for v in ['pre_score','post_score','delayed_score','ai_literacy','transfer_score','artifact_total']:
 for label,d in [('experimental',df[df.group_code==1]),('comparison',df[df.group_code==0])]: rows.append({'outcome':v,'group':label,'n':len(d),'mean':d[v].mean(),'sd':d[v].std(ddof=1)})
pd.DataFrame(rows).to_csv(RES/'table_descriptives.csv',index=False,encoding='utf-8-sig')
# BH for four secondary ANCOVA p-values
pvals=np.array([results['ancova_'+o]['p'] for o in ['delayed_score','ai_literacy','transfer_score']]); order=np.argsort(pvals); adj=np.empty(3); ranked=pvals[order]*3/np.arange(1,4); ranked=np.minimum.accumulate(ranked[::-1])[::-1]; adj[order]=np.minimum(ranked,1); results['secondary_p_bh']=dict(zip(['delayed_score','ai_literacy','transfer_score'],adj.tolist()))
(RES/'analysis_results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
# compact markdown
with open(RES/'analysis_report.md','w',encoding='utf-8') as f:
 f.write('# Воспроизводимый отчёт по синтетическому набору\n\n**Статус данных: синтетические.** Результаты предназначены для проверки дизайна и кода.\n\n```json\n'+json.dumps(results,ensure_ascii=False,indent=2)+'\n```\n')
print(json.dumps(results,ensure_ascii=False,indent=2))
