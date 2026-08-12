
import re
from functools import lru_cache
from app.melimi.index import build_index

TOKEN_RE = re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*")

FUNCTION_WORDS = {
    "నేను","నాకు","నా","నువ్వు","నీ","నీకు","మీరు","మీకు","అతను","ఆమె","వారు",
    "ఇది","అది","ఇవి","అవి","ఏమి","ఏం","ఏంటి","ఎలా","ఎందుకు","ఎక్కడ","ఎప్పుడు",
    "ఎవరు","ఎంత","ఎన్ని","ఒక","మరియు","లేదా","కానీ","అయితే","కూడా","మాత్రం","ఇంకా",
    "ఇప్పుడు","అప్పుడు","ఇక్కడ","అక్కడ","లో","కు","కి","తో","నుండి","నుంచి","పై","కింద",
    "కోసం","వల్ల","గురించి","మధ్య","లా","గా","అని","అంటే","లేదు","లేను","లేవు","కాదు",
    "వద్దు","ఉంది","ఉన్న","ఉన్నారు","ఉన్నాను","ఉన్నావు","చెప్పు","చెప్పండి","రా","రండి",
    "వెళ్లు","వెళ్లి","చేయి","చేయండి","అవును","సరే","హా","హాయ్","టేంకణములు"
}

LOAN_STATUSES={"loan","loanword","borrowed","foreign","sanskrit_loan","sanskrit-derived","non_native"}
NATIVE_STATUSES={"native","native_telugu","established_native","corpus-supported","derived-by-rule","established"}

def tokenize(text):
    return TOKEN_RE.findall(text or "")

def _values(entry, keys):
    out=[]
    for key in keys:
        value=entry.get(key)
        if isinstance(value,list):
            out.extend(str(x).strip() for x in value if str(x).strip())
        elif isinstance(value,str) and value.strip():
            out.append(value.strip())
    return out

@lru_cache(maxsize=1)
def lexical_inventory():
    registered=set(FUNCTION_WORDS)
    native=set(FUNCTION_WORDS)
    loan=set()
    standard_to_melimi={}
    melimi_to_standard={}
    provenance={}
    unresolved_loan=set()

    for doc in build_index():
        if doc.kind!="vocabulary":
            continue
        for entry in doc.entries:
            mel=_values(entry,("melimi","word","headword","forms","variants"))
            std=_values(entry,("standard","standard_or_source","source_word"))
            status=str(entry.get("status","")).strip().lower()
            source_type=str(entry.get("source_type","")).strip().lower()
            classification=status or source_type

            # Only the Melimi side becomes a registered Melimi lexical item.
            registered.update(mel)

            if classification in NATIVE_STATUSES or source_type in NATIVE_STATUSES:
                native.update(mel)
                native.update(std)

            if classification in LOAN_STATUSES or source_type in LOAN_STATUSES:
                for word in std:
                    loan.add(word)
                    provenance[word]="loan"
                # A loan is unresolved only when no Melimi form is registered.
                if not mel:
                    unresolved_loan.update(std)

            for standard in std:
                for melimi in mel:
                    standard_to_melimi[standard]=melimi
                    melimi_to_standard[melimi]=standard
                    # An explicit mapping is a stronger signal than a generic
                    # unknown-word heuristic.
                    provenance.setdefault(standard, "mapped_standard")

            for word in mel:
                provenance.setdefault(word, "melimi")

    # chat_registered entries are user_verified and therefore immediately
    # registered Melimi vocabulary after a successful GitHub/local save.
    return {
        "registered":frozenset(registered),
        "native":frozenset(native),
        "loan":frozenset(loan),
        "unresolved_loan":frozenset(unresolved_loan),
        "standard_to_melimi":standard_to_melimi,
        "melimi_to_standard":melimi_to_standard,
        "provenance":provenance,
    }

def reload_registry():
    lexical_inventory.cache_clear()

def audit_response(text):
    inv=lexical_inventory()
    result=[]
    for word in tokenize(text):
        loan=word in inv["loan"]
        unresolved=word in inv["unresolved_loan"]
        mapped_gap=word in inv["standard_to_melimi"] and word not in inv["registered"]
        clickable=unresolved or mapped_gap

        # IMPORTANT: a normal Telugu word is not "Melimi" merely because it
        # passed through the audit. Only explicit Melimi vocabulary is registered.
        result.append({
            "word":word,
            "registered":word in inv["registered"],
            "native":word in inv["native"],
            "loan":loan,
            "unresolved_loan":unresolved,
            "melimi_gap":mapped_gap,
            "clickable":clickable
        })
    return result

def strict_violations(text):
    inv=lexical_inventory()
    violations=[]
    for word in tokenize(text):
        if word in inv["standard_to_melimi"]:
            violations.append({"standard":word,"melimi":inv["standard_to_melimi"][word]})
        elif word in inv["unresolved_loan"]:
            violations.append({"loan":word,"melimi":""})
    return violations

def analyze_word(word):
    inv=lexical_inventory()
    return {
        "word":word,
        "registered":word in inv["registered"],
        "native":word in inv["native"],
        "loan":word in inv["loan"],
        "unresolved_loan":word in inv["unresolved_loan"],
        "melimi_equivalent":inv["standard_to_melimi"].get(word,""),
        "root_candidate":word,
    }
