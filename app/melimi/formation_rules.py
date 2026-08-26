"""Authoritative, conservative Melimi word-formation rules.

This module deliberately contains only formations established by the project
language source. It is not a generic Telugu morphology generator. When a
formation is unclear, callers must leave it unresolved rather than guess.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class Formation:
    element: str
    function: str
    status: str = "MASTER"
    examples: Tuple[str, ...] = ()


# The corpus establishes multiple senses for some elements. Keep each sense
# separate instead of collapsing an element to one English gloss.
PREFIXES: Dict[str, Tuple[Formation, ...]] = {
    "అలన్": (
        Formation("అలన్", "గతము", examples=("అలనాడు",)),
        Formation("అలన్", "మరల మరల", examples=("అలవాటు", "అలవోక")),
    ),
    "ఎస": (
        Formation("ఎస", "ఎక్కువ, తక్కువ", examples=("ఎసకొను", "ఎసరేణు", "ఎసవెట్టు")),
    ),
    "మన్": (Formation("మన్", "మంచి, positive", examples=("మందావి", "మందనం", "మంద్రోవ")),),
    "సి": (Formation("సి/సీ", "చెడు", examples=("సీతావి", "సీతనం", "సీవాడుక")),),
    "ఔన్": (Formation("ఔన్", "మంచి, positive", examples=("ఔఁగాపు", "ఔఁజందం")),),
    "అక": (Formation("అక", "కానటువంటి", examples=("అకక్కఱ", "అకాఱియ", "అకపాటి")),),
    "తరు": (Formation("తరు", "తరువాత", examples=("తరుకౌట", "తరుకుందు", "తరుతేను")),),
    "మఱి": (Formation("మఱి/మఱీ", "అతిగా ఎక్కువగా", examples=("మఱీక్రాలిక", "మఱీదీమసము")),),
    "బై": (Formation("బై", "ప్రక్కన, దగ్గర, తోడుగా, సహాయముగా, ఉప", examples=("బైప్రెగడ", "బైవీటు", "బైదాఁటు")),),
    "సరి": (Formation("సరి", "ఒకే విధముగా, సరిగా, మంచిగా, చక్కగా", examples=("సరిచూచు", "సరిదిద్దు", "సరిచేయు")),),
    "పొలో": (Formation("పొలో", "సామూహికముగా, గుంపుగా", examples=("పొలోక్రమి", "పొలోచెఱపము", "పొలోమనువులు")),),
    "తిరి": (Formation("తిరి", "మరల", examples=("తిరికల్గం", "తిరివల్కు")),),
}

SUFFIXES: Dict[str, Tuple[Formation, ...]] = {
    "కాను": (Formation("కాను", "చేయునట్టి; agent/doer/characterized-by", examples=("ముప్పుకాను", "పాటకాను", "త్రోవకాను", "విలుకాను")),),
    "అరి": (Formation("అరి", "agent/doer", examples=("తెగువరి", "తలవరి", "జాలరి", "మేదరి")),),
    "వాను": (Formation("వాను", "కలిగిన, సంబంధించిన", examples=("నెనరువాను", "మైవాను", "నిలువాను", "ఏలువాను")),),
    "మారి": (Formation("మారి", "మంచి/తటస్థ స్వభావము", examples=("పనిమారి", "చదువుమారి", "తలపుమారి", "నెమ్మనమారి")),),
    "అలవి": (Formation("అలవి/అల్వి", "చేయుటకు శక్యము, సాధ్యము, యోగ్యము, అర్హము", examples=("చదువల్వి", "తినల్వి", "చేయల్వి", "చూడల్వి")),),
    "అరిది": (Formation("అరిది/అర్ది", "అలవి యొక్క వ్యతిరేకార్థము", examples=("చదువరిది", "వినర్ది", "తినర్ది", "చేయర్ది")),),
    "పాదు": (Formation("పాదు", "చేయదగిన/యోగ్యమైన", examples=("దీవనపాదు", "దండపాదు", "కంటుపాదు")),),
    "పఱ": (Formation("పఱ", "పాదు యొక్క వ్యతిరేకార్థము; తగనిది", examples=("ఈవిపఱ", "దీవనపఱ", "దండపఱ")),),
    "మాలు": (Formation("మాలు", "రహితము", examples=("పేరుమాలు", "అక్కఱమాలు", "నెరసుమాలు")),),
    "కము": (Formation("కము/ఇకము", "స్థితి/భావార్థకము", examples=("కవైణికము", "తోబుట్టుకము", "విచ్చుకము")),),
    "గము": (Formation("గము", "మొత్తము/గుంపు", examples=("పరిగము", "ఎన్నరిగము")),),
    "ఓరు": (Formation("ఓరు", "సంస్థ/వ్యవస్థ", examples=("పాటియోరు", "మణియోరు", "లెంకోరు")),),
    "ఆది": (Formation("ఆది", "మొత్తము/సమూహము", examples=("ఏడాది", "వేలాది", "ఉరువాది")),),
    "ఓలి": (Formation("ఓలి", "వరుస", examples=("మాటోలి", "కందోలి", "వ్రాయోలి")),),
    "ఓజ": (Formation("ఓజ", "క్రమము/విధము/విధానము/శైలి", examples=("బ్రదుకోజ", "తలఁపోజ", "ఏలోజ")),),
    "ఇత": (Formation("ఇత", "explicit feminine person/agent form", examples=("ఏలువానిత",)),),
}

# These are recognized as historical/source forms but are not preferred for
# newly generated agent words. New productive agent formations prefer కాను,
# subject to established lexical forms and sound suitability.
LEGACY_AGENT_SUFFIXES = frozenset({"కాఁడు", "గాఁడు", "కత్తె", "కత్తియ"})


def formation_for(element: str, *, suffix: bool = True) -> Optional[Tuple[Formation, ...]]:
    table = SUFFIXES if suffix else PREFIXES
    return table.get(element)


def preferred_agent_suffix() -> str:
    return "కాను"


def can_generate(element: str, *, suffix: bool = True) -> bool:
    """Return True only for explicitly documented productive elements."""
    return element in (SUFFIXES if suffix else PREFIXES)


def explain_element(element: str) -> dict:
    """Return structured evidence without inventing a meaning."""
    forms = SUFFIXES.get(element) or PREFIXES.get(element)
    if not forms:
        return {"element": element, "known": False, "formations": []}
    return {
        "element": element,
        "known": True,
        "formations": [
            {"function": f.function, "status": f.status, "examples": list(f.examples)}
            for f in forms
        ],
    }
