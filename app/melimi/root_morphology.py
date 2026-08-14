"""Generic root-first Melimi morphology.

The engine stores lexical mappings only at the root level. Surface forms are
reduced to a root plus a grammatical/derivational operation, the root is
looked up, and the same operation is reapplied. It intentionally does not
store per-word inflection/derivation tables.
"""
from __future__ import annotations
import json, os, re
from dataclasses import dataclass

TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]+")

@dataclass(frozen=True)
class MorphologicalForm:
    surface: str
    root: str
    suffixes: tuple[str, ...] = ()

# Shared grammatical endings. Longest first.
GRAMMATICAL_SUFFIXES = tuple(sorted([
    'లతో','లలో','లకు','లను','లని','లపై','లకై','నుంచి','నుండి','యొక్క','తోటి',
    'గురించి','కోసం','వల్ల','మధ్య','లోని','పైన','తో','లో','లు','ను','ని','కు',
    'కి','గా','పై','ల'
], key=len, reverse=True))

# Productive derivational markers defined by the supplied Melimi grammar.
# They are operations, not lexical entries.
DERIVATIONAL_SUFFIXES = tuple(sorted([
    'కాను','కాన్','మారి','వాను','వాన్','పాదు','పఱ','మాలు','కము','ఇకము',
    'గము','ఓరు','ఆది','ఓలి','ఓజ','అంగి','అలవి','అల్వి','అరిది','అర్ది',
    'ఆ','ఇ','తి','టి','అటి','ఇటి','ఇంటి','ఆటి','పాటి','పారు','బారు'
], key=len, reverse=True))


def _root_file():
    here=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(here,'melimi_telugu','vocabulary','root_dictionary.json')


def load_root_dictionary():
    with open(_root_file(),encoding='utf-8') as f:
        data=json.load(f)
    return {str(x['standard_root']).strip(): str(x['melimi_root']).strip() for x in data.get('entries',[]) if x.get('standard_root') and x.get('melimi_root')}


def _strip_one(word: str, suffixes):
    for suffix in suffixes:
        if word.endswith(suffix) and len(word) > len(suffix)+1:
            root=word[:-len(suffix)]
            return root, suffix
    return word, ''


def reduce_to_root(word: str) -> MorphologicalForm:
    """Reduce a surface word conservatively to a registered root candidate.

    Grammatical/derivational material is retained as operations. No word is
    declared a root unless the caller confirms it exists in the root lexicon.
    """
    surface=(word or '').strip()
    if not surface:
        return MorphologicalForm('', '')
    root, suffix=_strip_one(surface, GRAMMATICAL_SUFFIXES)
    if suffix:
        return MorphologicalForm(surface, root, (suffix,))
    root, suffix=_strip_one(surface, DERIVATIONAL_SUFFIXES)
    if suffix:
        return MorphologicalForm(surface, root, (suffix,))
    return MorphologicalForm(surface, surface, ())


def reapply_operations(melimi_root: str, operations: tuple[str,...]) -> str:
    result=melimi_root
    for suffix in operations:
        # Central morphophonemic rules, never per-word exceptions. A Telugu
        # attributive -ఆ surface can correspond to the Melimi root itself when
        # the target root is usable attributively; do not manufacture *నుడిఆ*.
        if suffix == 'ఆ':
            continue
        result += suffix
    return result


def convert_surface(word: str, roots=None):
    roots = roots or load_root_dictionary()
    if word in roots:
        return roots[word]
    form=reduce_to_root(word)
    if form.root not in roots:
        return word
    return reapply_operations(roots[form.root], form.suffixes)
