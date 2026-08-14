"""Small, explicit Melimi leakage guard.

This file is deliberately conservative: it only marks words that have been
explicitly identified as unwanted Standard/loan leakage or that have an
authoritative Melimi replacement. It does not treat every unregistered Telugu
word as a loan.
"""

# User-confirmed leakage/replacement forms. Keep this list small and sourced;
# expand it only when an authoritative Melimi equivalent is established.
LEAKAGE_REPLACEMENTS = {
    "విశిష్ట": "వేఱైన",
    "ఆసక్తికరం": "హాళికాను",
    "ఆసక్తికరమైన": "హాళికాను",
    "ఆసక్తికరంగా": "హాళికానుగా",
}

LEAKAGE_ONLY = {
    # No authoritative replacement is claimed here. These are flagged so the
    # generator/validator knows they need review instead of silently accepting
    # them as Melimi.
    "భాషా పరిమాణం": "",
}


def leakage_replacements():
    return dict(LEAKAGE_REPLACEMENTS)


def leakage_only():
    return dict(LEAKAGE_ONLY)
