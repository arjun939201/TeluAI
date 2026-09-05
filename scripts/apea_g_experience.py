"""Persistent, bounded experience learning for APEA-G."""
from __future__ import annotations
import json, time
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
EXPERIENCE_DIR=ROOT/".apea"/"experience"
OUTCOMES_PATH=EXPERIENCE_DIR/"outcomes.jsonl"
STRATEGIES_PATH=EXPERIENCE_DIR/"strategies.json"
LESSONS_PATH=EXPERIENCE_DIR/"lessons.jsonl"
PATTERNS_PATH=EXPERIENCE_DIR/"patterns.json"
MAX_PATTERNS=500

def _load_json(path:Path, default:Any)->Any:
    if not path.exists(): return default
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError): return default

def save_json(path:Path,value:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def _append(path:Path,record:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f: f.write(json.dumps(record,ensure_ascii=False,sort_keys=True)+"\n")

def record_outcome(*,capability:str,step:str,outcome:str,commit:str|None=None,ci:dict[str,Any]|None=None,action:str|None=None,diagnosis:str|None=None,repair_attempt:int=0)->dict[str,Any]:
    ci=ci or {}; failure=ci.get("failure") or {}
    record={"timestamp":int(time.time()),"capability":capability,"step":step,"outcome":outcome,"commit":commit,"ci_run_id":ci.get("run_id"),"ci_conclusion":ci.get("conclusion"),"failure_kind":failure.get("kind"),"failure_signature":failure.get("signature"),"action":action,"repair_attempt":repair_attempt}
    _append(OUTCOMES_PATH,record)
    if action:
        strategies=_load_json(STRATEGIES_PATH,{})
        e=strategies.setdefault(action,{"attempts":0,"successes":0,"failures":0}); e["attempts"]+=1
        if outcome in {"success","repaired"}: e["successes"]+=1
        elif outcome in {"failure","repair_failed"}: e["failures"]+=1
        e["confidence"]=round(e["successes"]/e["attempts"],4); e["updated_at"]=int(time.time()); save_json(STRATEGIES_PATH,strategies)
    sig=failure.get("signature")
    if sig:
        patterns=_load_json(PATTERNS_PATH,{})
        p=patterns.setdefault(sig,{"attempts":0,"successes":0,"failures":0,"actions":{}}); p["attempts"]+=1
        if outcome in {"success","repaired"}: p["successes"]+=1
        elif outcome in {"failure","repair_failed"}: p["failures"]+=1
        if action:
            a=p["actions"].setdefault(action,{"attempts":0,"successes":0,"failures":0}); a["attempts"]+=1
            if outcome in {"success","repaired"}: a["successes"]+=1
            elif outcome in {"failure","repair_failed"}: a["failures"]+=1
        if len(patterns)>MAX_PATTERNS: patterns=dict(list(patterns.items())[-MAX_PATTERNS:])
        save_json(PATTERNS_PATH,patterns)
    if outcome in {"success","repaired","repair_failed","blocked"}:
        _append(LESSONS_PATH,{"timestamp":record["timestamp"],"capability":capability,"step":step,"outcome":outcome,"failure_kind":failure.get("kind"),"failure_signature":sig,"action":action,"diagnosis":diagnosis,"commit":commit})
    return record

def recent_experience(*,capability:str|None=None,failure_signature:str|None=None,limit:int=8)->list[dict[str,Any]]:
    if not OUTCOMES_PATH.exists(): return []
    try: lines=OUTCOMES_PATH.read_text(encoding="utf-8").splitlines()
    except OSError: return []
    out=[]
    for line in reversed(lines):
        try: item=json.loads(line)
        except json.JSONDecodeError: continue
        if capability and item.get("capability")!=capability: continue
        if failure_signature and item.get("failure_signature")!=failure_signature: continue
        out.append(item)
        if len(out)>=limit: break
    return out

def best_strategy(action_candidates:list[str],*,capability:str|None=None,failure_signature:str|None=None)->dict[str,Any]|None:
    strategies=_load_json(STRATEGIES_PATH,{}); patterns=_load_json(PATTERNS_PATH,{})
    scored=[]
    for action in action_candidates:
        item=strategies.get(action,{}); attempts=int(item.get("attempts",0)); confidence=float(item.get("confidence",0.0)) if attempts else 0.0; relevant=0
        if failure_signature and failure_signature in patterns:
            stats=patterns[failure_signature].get("actions",{}).get(action,{}) ; pa=int(stats.get("attempts",0)); ps=int(stats.get("successes",0)); relevant=ps
            if pa: confidence=ps/pa
        else:
            history=recent_experience(capability=capability,limit=20); relevant=sum(1 for r in history if r.get("action")==action and r.get("outcome") in {"success","repaired"})
        scored.append((confidence,relevant,-int(item.get("failures",0)),action,attempts))
    if not scored: return None
    confidence,relevant,_,action,attempts=max(scored)
    return {"action":action,"confidence":confidence,"relevant_successes":relevant,"attempts":attempts}

def render_context(*,capability:str,failure_signature:str|None=None)->str:
    return json.dumps({"recent":recent_experience(capability=capability,failure_signature=failure_signature,limit=6),"preferred_strategy":best_strategy(["repair_contract","repair_fixture","repair","repair_workflow","retry_ci","diagnose"],capability=capability,failure_signature=failure_signature),"learning_policy":{"experience_is_evidence_not_authority":True,"never_weaken_tests_or_ci":True}},ensure_ascii=False)
