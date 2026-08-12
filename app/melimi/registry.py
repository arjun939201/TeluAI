
import re
from functools import lru_cache
from app.melimi.index import build_index
from app.linguistics.parser import case_variants

TOKEN_RE=re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*")

FUNCTION_WORDS={
"నేను","నాకు","నా","నువ్వు","నీ","నీకు","మీరు","మీకు","అతను","ఆమె","వారు",
"ఇది","అది","ఇవి","అవి","ఏమి","ఏం","ఏంటి","ఎలా","ఎందుకు","ఎక్కడ","ఎప్పుడు",
"ఎవరు","ఎంత","ఎన్ని","ఒక","మరియు","లేదా","కానీ","అయితే","కూడా","మాత్రం","ఇంకా",
"ఇప్పుడు","అప్పుడు","ఇక్కడ","అక్కడ","లో","కు","కి","తో","నుండి","నుంచి","పై","కింద",
"కోసం","వల్ల","గురించి","మధ్య","లా","గా","అని","అంటే","లేదు","లేను","లేవు","కాదు",
"వద్దు","ఉంది","ఉన్న","ఉన్నారు","ఉన్నాను","ఉన్నావు","చెప్పు","చెప్పండి","రా","రండి",
"వెళ్లు","వెళ్లి","చేయి","చేయండి","అవును","సరే","హా","హాయ్","టేంకణములు"
}

def tokenize(t): return TOKEN_RE.findall(t or "")

@lru_cache(maxsize=1)
def lexical_inventory():
    registered=set(FUNCTION_WORDS)
    loan=set()
    standard_to_melimi={}
    native=set()

    for d in build_index():
        if d.kind=="vocabulary":
            for e in d.entries:
                mel=e.get("melimi")
                std=e.get("standard") or e.get("standard_or_source")
                status=str(e.get("status","")).lower()
                source_type=str(e.get("source_type","")).lower()
                if isinstance(mel,str) and mel.strip():
                    registered.add(mel.strip())
                if isinstance(mel,list):
                    registered.update(str(x).strip() for x in mel if str(x).strip())
                if isinstance(std,str) and isinstance(mel,str) and mel.strip():
                    standard_to_melimi[std.strip()]=mel.strip()
                if status in {"loan","loanword","foreign","borrowed"} or source_type in {"loan","loanword","foreign","borrowed"}:
                    if isinstance(std,str): loan.add(std.strip())
                    if isinstance(mel,str): loan.add(mel.strip())
                if status in {"native","native_telugu","established_native"} or source_type in {"native","native_telugu"}:
                    for v in (std,mel):
                        if isinstance(v,str) and v.strip(): native.add(v.strip())

    return {
        "registered":frozenset(registered),
        "loan":frozenset(loan),
        "native":frozenset(native),
        "standard_to_melimi":standard_to_melimi
    }

def reload_registry(): lexical_inventory.cache_clear()

def _any_in(variants, pool):
    return any(v in pool for v in variants)


def _mapped_equivalent(variants, standard_to_melimi):
    for v in variants:
        if v in standard_to_melimi:
            return standard_to_melimi[v]
    return ""


def audit_response(text):
    inv=lexical_inventory()
    out=[]
    for w in tokenize(text):
        # Strip common case/plural clitics first (e.g. -లో, -కు, -లు) so
        # inflected variants of a registered/loan word are still recognized
        # strictly, instead of only matching the bare dictionary form.
        variants=case_variants(w)
        is_loan=_any_in(variants, inv["loan"])
        is_registered=_any_in(variants, inv["registered"]) or w in FUNCTION_WORDS
        # Only explicitly known loan/foreign words, or an explicitly mapped
        # Standard/loan word whose Melimi form is still unregistered, are
        # red by default. Ordinary Telugu words remain normal.
        has_melimi_gap=_any_in(variants, inv["standard_to_melimi"]) and not is_registered
        clickable=is_loan or has_melimi_gap
        out.append({
            "word":w,
            "registered":is_registered,
            "native":_any_in(variants, inv["native"]) or w in FUNCTION_WORDS,
            "loan":is_loan,
            "melimi_gap":has_melimi_gap,
            "clickable":clickable
        })
    return out

def analyze_word(word):
    inv=lexical_inventory()
    variants=case_variants(word)
    return {
        "word":word,
        "registered":_any_in(variants, inv["registered"]),
        "native":_any_in(variants, inv["native"]),
        "loan":_any_in(variants, inv["loan"]),
        "melimi_equivalent":_mapped_equivalent(variants, inv["standard_to_melimi"]),
        "root_candidate":variants[-1] if variants else word
    }
