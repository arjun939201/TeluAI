import re
from functools import lru_cache
from app.melimi.root_morphology import load_root_dictionary, reduce_to_root, reapply_operations
TOKEN_RE=re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*")
FUNCTION_WORDS={"నేను","నాకు","నా","నువ్వు","నీ","నీకు","మీరు","మీకు","అతను","ఆమె","వారు","ఇది","అది","ఇవి","అవి","ఏమి","ఏం","ఏంటి","ఎలా","ఎందుకు","ఎక్కడ","ఎప్పుడు","ఎవరు","ఎంత","ఎన్ని","ఒక","మరియు","లేదా","కానీ","అయితే","కూడా","మాత్రం","ఇంకా","ఇప్పుడు","అప్పుడు","ఇక్కడ","అక్కడ","లో","కు","కి","తో","నుండి","నుంచి","పై","కింద","కోసం","వల్ల","గురించి","మధ్య","లా","గా","అని","అంటే","లేదు","లేను","లేవు","కాదు","వద్దు","ఉంది","ఉన్న","ఉన్నారు","ఉన్నాను","ఉన్నావు","చెప్పు","చెప్పండి","రా","రండి","వెళ్లు","వెళ్లి","చేయి","చేయండి","అవును","సరే","హా","హాయ్"}
def tokenize(t): return TOKEN_RE.findall(t or "")
def _values(entry,keys):
    out=[]
    for k in keys:
        v=entry.get(k)
        if isinstance(v,list): out += [str(x).strip() for x in v if str(x).strip()]
        elif isinstance(v,str) and v.strip(): out.append(v.strip())
    return out
@lru_cache(maxsize=16)
def lexical_inventory(version:int|None=None):
    from app.melimi.db_subject import language_space_version
    if version is None: version=language_space_version()
    registered=set(FUNCTION_WORDS); native=set(FUNCTION_WORDS); loan=set(); standard_to_melimi={}; melimi_to_standard={}; forbidden=set()
    try:
        roots=load_root_dictionary(version)
        for std,mel in roots.items(): standard_to_melimi[std]=mel; melimi_to_standard[mel]=std; registered.add(mel); forbidden.add(std)
    except Exception: pass
    try:
        from app.melimi.index import build_index
        for d in build_index(version):
            for e in d.entries:
                mel=_values(e,("melimi","word","headword","forms","variants")); std=_values(e,("standard","standard_or_source","source_word"))
                for m in mel: registered.add(m)
                for a in std:
                    for b in mel: standard_to_melimi[a]=b; melimi_to_standard[b]=a; forbidden.add(a)
                status=str(e.get("status","")).lower(); st=str(e.get("source_type","")).lower()
                if status in {"native","native_telugu","established","corpus-supported","derived-by-rule"} or st in {"native","native_telugu"}: native.update(mel); native.update(std)
                if status in {"loan","loanword","borrowed","foreign"} or st in {"loan","loanword","borrowed","foreign"}: loan.update(std)
    except Exception: pass
    return {"registered":frozenset(registered),"native":frozenset(native),"loan":frozenset(loan),"standard_to_melimi":standard_to_melimi,"melimi_to_standard":melimi_to_standard,"forbidden_standard":frozenset(forbidden)}
def reload_registry(): lexical_inventory.cache_clear()
def audit_response(text):
    inv=lexical_inventory(); out=[]
    for w in tokenize(text): out.append({"word":w,"registered":w in inv["registered"],"native":w in inv["native"],"loan":w in inv["loan"],"melimi_equivalent":inv["standard_to_melimi"].get(w,""),"clickable":w in inv["loan"] or w in inv["forbidden_standard"]})
    return out
def strict_violations(text):
    inv=lexical_inventory(); return [{"standard":w,"melimi":inv["standard_to_melimi"][w]} for w in tokenize(text) if w in inv["standard_to_melimi"]]
def analyze_word(word):
    inv=lexical_inventory(); form=reduce_to_root(word,load_root_dictionary()); mel=inv["standard_to_melimi"].get(form.root,""); transformed=reapply_operations(mel,form) if mel else ""
    return {"word":word,"registered":word in inv["registered"],"native":word in inv["native"],"loan":word in inv["loan"],"melimi_equivalent":transformed or mel,"root_candidate":form.root,"operations":[{"kind":k,"suffix":s} for k,s in form.operations]}
