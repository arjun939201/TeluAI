"""Event-driven APEA-G controller: commit, persist, exit; resume from CI events."""
from __future__ import annotations
import json, os, subprocess, time
from pathlib import Path
from scripts import apea_g_loop as core
ROOT=Path(__file__).resolve().parents[1]
STATE_PATH=ROOT/'.apea/continuous-state.json'; PLAN_PATH=ROOT/'.apea/continuous-plan.json'
MAX_PATCH_RETRIES=3

def sh(*args,check=False):
 p=subprocess.run(args,cwd=ROOT,text=True,capture_output=True); out=(p.stdout+p.stderr).strip()
 if check and p.returncode: raise RuntimeError(out)
 return out

def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def load(path):
 try: return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
 except (OSError,json.JSONDecodeError): return None

def step_for(plan,state):
 done=set(state.get('completed',[]))
 for i,s in enumerate(plan.get('steps',[])):
  if s.get('id') not in done: return i,s
 return None,None

def branch_for(state):
 branch=state.get('branch') or f"apea-g/continuous-{int(time.time())}"; state['branch']=branch
 if not state.get('branch_initialized'):
  sh('git','switch','-c',branch,check=True); state['branch_initialized']=True
 return branch

def ensure_plan(state):
 cap=core.next_capability(state)
 if not cap: return None
 state['capability']=cap; plan=load(PLAN_PATH)
 if not plan or plan.get('capability')!=cap: plan=core.make_capability_plan(cap); save(PLAN_PATH,plan)
 return plan

def generated_patch(prompt,repair_context=''):
 last_error=''
 for attempt in range(1,MAX_PATCH_RETRIES+1):
  request=prompt
  if repair_context:
   request += f"\nPREVIOUS_GENERATION_ERROR={repair_context}\nThis is retry {attempt}. Return a concrete unified diff containing recognized repository file paths; never return prose-only output."
  result=core.provider(request)
  if result.get('action')=='blocked': raise RuntimeError(result.get('reason','step blocked'))
  patch=result.get('patch')
  if not isinstance(patch,str) or not patch.strip():
   last_error='model returned an empty patch'
   repair_context=last_error
   continue
  try:
   core.apply_patch(patch); return result
  except (RuntimeError,ValueError) as exc:
   last_error=str(exc)
   repair_context=last_error
 raise RuntimeError(f"APEA-G could not produce an applicable patch after {MAX_PATCH_RETRIES} attempts: {last_error}")

def commit_step(plan,state,branch,index,step,repair=False):
 learning=core.render_context(capability=plan['capability'],failure_signature=(state.get('pending') or {}).get('failure_signature'))
 prompt=(f"Implement exactly ONE current step and no later step. Return JSON action implement|blocked and patch unified diff. PLAN={json.dumps(plan)} STEP={json.dumps(step)} PRIOR_LEARNING={learning} REPO={json.dumps(core.snapshot())}")
 result=generated_patch(prompt)
 core.validate_local()
 state['status']='awaiting_ci'; state['pending']={'capability':plan['capability'],'step':step['id'],'step_index':index,'repairs':int((state.get('pending') or {}).get('repairs',0))}
 save(STATE_PATH,state)
 head=core.push(branch,(f"fix: APEA-G {plan['capability']} step {index+1} attempt {state['pending']['repairs']}" if repair else f"feat: APEA-G {plan['capability']} step {index+1} - {step.get('title',step['id'])}"))
 pr=core.ensure_pr(branch); state['pull_request']=core.inspect_pr(pr)
 print(json.dumps({'status':'AWAITING_CI','commit':head,'branch':branch,'pr':state['pull_request']}))

def start(state,branch):
 while True:
  plan=ensure_plan(state)
  if not plan:
   state['status']='complete'; save(STATE_PATH,state); print(json.dumps({'status':'COMPLETE'})); return
  i,s=step_for(plan,state)
  if s is None:
   state.setdefault('completed_capabilities',[]).append(plan['capability']); state['completed_capabilities']=list(dict.fromkeys(state['completed_capabilities'])); state['completed']=[]; save(STATE_PATH,state); continue
  commit_step(plan,state,branch,i,s); return

def latest_ci(head):
 runs=core.gh('actions/runs?head_sha='+head+'&per_page=20').get('workflow_runs',[])
 runs=[r for r in runs if r.get('path')=='.github/workflows/ci.yml']
 return runs[0] if runs else None

def resume(state,branch):
 pending=state.get('pending') or {}
 if state.get('status')!='awaiting_ci' or not pending: return start(state,branch)
 head=sh('git','rev-parse','HEAD'); run=latest_ci(head)
 if not run or run.get('status')!='completed': print(json.dumps({'status':'WAITING_FOR_CI','commit':head})); return
 evidence=core.ci_evidence(run); cap=pending['capability']; sid=pending['step']
 state.setdefault('history',[]).append({'capability':cap,'step':sid,'head':head,'ci':evidence,'pr':state.get('pull_request')})
 if evidence.get('conclusion')=='success':
  core.record_outcome(capability=cap,step=sid,outcome='success',commit=head,ci=evidence,action='implement')
  state.setdefault('completed',[]).append(sid); state['completed']=list(dict.fromkeys(state['completed'])); state.pop('pending',None); state['status']='advancing'; save(STATE_PATH,state); return start(state,branch)
 failure=evidence.get('failure',{}); action=failure.get('action','diagnose'); repairs=int(pending.get('repairs',0))
 core.record_outcome(capability=cap,step=sid,outcome='failure',commit=head,ci=evidence,action=action)
 if repairs>=core.MAX_REPAIRS: raise RuntimeError(f'step {sid} exceeded repair budget')
 plan=load(PLAN_PATH); _,step=next(((i,s) for i,s in enumerate(plan.get('steps',[])) if s.get('id')==sid),(None,None))
 if not step: raise RuntimeError('pending step is missing from persisted plan')
 repairs+=1
 learning=core.render_context(capability=cap,failure_signature=failure.get('signature'))
 repair_prompt=core.repair_prompt(plan,step,evidence,learning) if hasattr(core,'repair_prompt') else f"Repair exactly this failed step. PLAN={json.dumps(plan)} STEP={json.dumps(step)} EVIDENCE={json.dumps(evidence)} LEARNING={learning} Return JSON with a concrete unified diff."
 generated_patch(repair_prompt,repair_context='The previous repair patch was missing or rejected by APEA-G preflight.')
 core.validate_local(); state['pending']['repairs']=repairs; state['pending']['failure_signature']=failure.get('signature'); state['status']='awaiting_ci'; save(STATE_PATH,state)
 new_head=core.push(branch,f"fix: APEA-G {cap} step {pending.get('step_index',0)+1} attempt {repairs}"); print(json.dumps({'status':'AWAITING_CI','commit':new_head,'repair':repairs}))

def main():
 state=load(STATE_PATH) or {'completed':[],'completed_capabilities':[],'history':[]}; branch=branch_for(state); save(STATE_PATH,state)
 if os.environ.get('APEA_MODE')=='resume': resume(state,branch)
 else: start(state,branch)

if __name__=='__main__': main()
