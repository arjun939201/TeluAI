
import re
from functools import lru_cache
from app.melimi.index import build_index

TOKEN_RE=re.compile(r"[\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*")
FUNCTION_WORDS={"నేను","నాకు","నా","నువ్వు","నీ","నీకు","మీరు","మీకు","అతను","ఆమె","వారు",
"ఇది","అది","ఇవి","అవి","ఏమి","ఏం","ఏంటి","ఎలా","ఎందుకు","ఎక్కడ","ఎప్పుడు","ఎవరు",
"ఎంత","ఎన్ని","ఒక","మరియు","లేదా","కానీ","అయితే","కూడా","మాత్రం","ఇంకా","ఇప్పుడు",
"అప్పుడు","ఇక్కడ","అక్కడ","లో","కు","కి","తో","నుండి","నుంచి","పై","కింద","కోసం",
"వల్ల","గురించి","మధ్య","లా","గా","అని","అంటే","లేదు","లేను","లేవు","కాదు","వద్దు",
"ఉంది","ఉన్న","ఉన్నారు","ఉన్నాను","ఉన్నావు","చెప్పు","చెప్పండి","రా","రండి","వెళ్లు",
"వెళ్లి","చేయి","చేయండి","అవును","సరే","హా","హాయ్","టేంకణములు"}
def tokenize(t): return TOKEN_RE.findall(t or "")
@lru_cache(maxsize=1)
def registered_words():
    out=set(FUNCTION_WORDS)
    for d in build_index():
        if d.kind!="vocabulary": continue
        for e in d.entries:
            for k in ("melimi","word","headword","forms","variants"):
                v=e.get(k)
                if isinstance(v,list): out.update(str(x).strip() for x in v if str(x).strip())
                elif isinstance(v,str) and v.strip(): out.add(v.strip())
    return frozenset(out)
def reload_registry(): registered_words.cache_clear()
def audit_response(text):
    known=registered_words()
    return [{"word":w,"registered":w in known,
             "clickable":w not in known and w not in FUNCTION_WORDS}
            for w in tokenize(text)]
def analyze_word(word):
    return {"word":word,"registered":word in registered_words(),
            "root_candidate":word,"meaning":"","part_of_speech":"","melimi_equivalent":""}
