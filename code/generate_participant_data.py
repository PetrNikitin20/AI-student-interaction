#!/usr/bin/env python3
from pathlib import Path
import numpy as np, pandas as pd
OUT=Path(__file__).resolve().parents[1]/'data'; OUT.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(20261001)
n_exp,n_ctrl=27,29
group=np.r_[np.ones(n_exp,dtype=int),np.zeros(n_ctrl,dtype=int)]
ids=[f'EXP{i:03d}' for i in range(1,n_exp+1)]+[f'CTRL{i:03d}' for i in range(1,n_ctrl+1)]
pre=np.clip(np.round(rng.normal(49,10,56),1),25,75)
prog=np.clip(np.round(rng.normal(2.8+0.15*group,1.0,56),1),0,5)
noise=rng.normal(0,6.0,56)
post=np.clip(np.round(23+0.66*pre+10.0*group+1.0*prog+noise,1),0,100)
delayed=np.clip(np.round(13+0.72*pre+9.0*group+0.8*prog+rng.normal(0,6.2,56),1),0,100)
ai_lit=np.clip(np.round(8+0.34*pre+7.0*group+rng.normal(0,3.8,56),1),0,40)
transfer=np.clip(np.round(2+0.17*pre+4.0*group+0.35*prog+rng.normal(0,2.1,56),1),0,20)
# latent rubric scores; two raters
rubric_names=['question','hypothesis','sources','design','provenance','reproducibility','model_choice','reflection']
base_ctrl=np.array([2.7,2.6,2.5,2.7,2.2,2.5,2.5,2.3]); bonus=np.array([.65,.7,.85,.6,1.15,.85,.85,.7])
latent=np.vstack([np.clip(base_ctrl+bonus*g+rng.normal(0,.42,8),0,4) for g in group])
ratings={}
for r in [1,2]:
  for j,nm in enumerate(rubric_names): ratings[f'{nm}_r{r}']=np.clip(np.rint(latent[:,j]+rng.normal(0,.28,56)),0,4).astype(int)
# behavior per student with denominators
refs_total=rng.integers(8,18,56)
pver=np.where(group==1,.94,.81)
refs_verified=np.array([rng.binomial(t,p) for t,p in zip(refs_total,pver)])
words=rng.integers(1800,4200,56)
rate=np.where(group==1,.40,1.50)/1000
unsupported=rng.poisson(words*rate)
reproduced=rng.binomial(1,np.where(group==1,.88,.60))
model_justified=rng.binomial(1,np.where(group==1,.90,.61))
# exp-only process
log_complete=np.where(group==1,np.clip(rng.normal(.84,.09,56),0.55,1),np.nan)
verification=np.where(group==1,np.clip(rng.normal(.78,.12,56),0.35,1),np.nan)
ai_requests=np.where(group==1,rng.integers(12,52,56),np.nan)
ai_error_found=np.where(group==1,rng.binomial(1,.93,56),np.nan)
df=pd.DataFrame({'id':ids,'group_code':group,'group':np.where(group==1,'experimental','comparison'),'pre_score':pre,'post_score':post,'delayed_score':delayed,'ai_literacy':ai_lit,'transfer_score':transfer,'programming_experience':prog,**ratings,'references_total':refs_total,'references_verified':refs_verified,'words_reviewed':words,'unsupported_claims':unsupported,'reproduced':reproduced,'model_justified':model_justified,'log_completeness':log_complete,'verification_quality':verification,'ai_requests':ai_requests,'ai_error_found':ai_error_found})
df.to_csv(OUT/'participants.csv',index=False,encoding='utf-8-sig')
# interview codes: synthetic, no quotations
exp_ids=df.loc[df.group_code==1].sort_values('transfer_score').iloc[[0,2,5,8,10,13,15,18,20,22,24,26]].id.tolist()
themes=['AI_as_critic','verification_habit','alternative_generation','time_cost','overtrust_risk','authorship_awareness']
probs=[.83,.92,.75,.67,.50,.83]
rows=[]
for pid in exp_ids:
 for theme,p in zip(themes,probs): rows.append({'id':pid,'theme':theme,'present':int(rng.random()<p),'data_status':'synthetic coded indicator; no quotation'})
pd.DataFrame(rows).to_csv(OUT/'interview_codes.csv',index=False,encoding='utf-8-sig')
# data dictionary
fields=[]
for c in df.columns:
 desc={'id':'Обезличенный идентификатор','group_code':'1=экспериментальная; 0=сравнения','group':'Название группы','pre_score':'Входной тест, 0–100','post_score':'Итоговый тест, 0–100','delayed_score':'Отложенный тест, 0–100','ai_literacy':'Критическая ИИ-грамотность, 0–40','transfer_score':'Задача переноса, 0–20','programming_experience':'Самооценка опыта программирования, 0–5','references_total':'Число проверяемых библиографических записей','references_verified':'Число подтверждённых записей','words_reviewed':'Объём текста для подсчёта утверждений','unsupported_claims':'Число неподтверждённых утверждений','reproduced':'Независимое воспроизведение: 1=успешно','model_justified':'Выбор модели обоснован: 1=да','log_completeness':'Полнота журнала, 0–1; только экспериментальная группа','verification_quality':'Качество проверки ответов ИИ, 0–1; только экспериментальная группа','ai_requests':'Число обращений к ИИ; только экспериментальная группа','ai_error_found':'Обнаружена ошибка ИИ: 1=да; только экспериментальная группа'}.get(c)
 if desc is None and '_r' in c: desc=f'Оценка эксперта {c[-1]} по шкале {c[:-3]}, 0–4'
 fields.append({'variable':c,'description':desc or c,'missing_rule':'NA допускается только для процессуальных показателей группы сравнения','status':'synthetic'})
pd.DataFrame(fields).to_csv(OUT/'data_dictionary.csv',index=False,encoding='utf-8-sig')
print(f'Created {len(df)} participant records')
