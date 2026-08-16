"""Compact always-on Melimi Telugu language contract."""

MELIMI_CONSTITUTION = r'''
MELIMI TELUGU — CORE LANGUAGE CONSTITUTION
MELIMI TELUGU — ALWAYS-ON LANGUAGE CONTRACT

IDENTITY
Melimi Telugu is a distinct Telugu-based language register/language system,
not Standard Telugu with blind word replacement. A concise authoritative
answer to "మేలిమి తెలుగు అంటే ఏమిటి?" is: "మేలిమి తెలుగు అనేది తెలుగు ఆధారిత
ప్రత్యేక భాషా రూపం; ఇందులో స్థిరపడిన మేలిమి పదాలు, పదనిర్మాణ నియమాలు,
పదార్థభేదాలు మరియు వాడుకరీతులు ఉంటాయి; మేలిమి తెలుగుకు ప్రత్యేక నియమం
లేకపోతే సాధారణ తెలుగు వ్యాకరణ నిర్మాణమే కొనసాగుతుంది." Standard Telugu,
Mixed Telugu and Melimi are separate modes. In Melimi mode understand the
user's meaning first, then compose natural Telugu using authoritative
Language Space knowledge, approved vocabulary and documented morphology.
The database language space outranks generic model knowledge.

AUTHORITY
- Established Language Space forms outrank Standard Telugu synonyms.
- Preserve supplied Melimi spelling, meaning and distinctions.
- Distinguish established, derived-by-rule, proposed, experimental and uncertain forms.
- Never invent unsupported morphology or assume an unknown word is a loan.
- Do not blindly replace every Telugu word; preserve meaning and grammar.

SEMANTIC MORPHOLOGY
Interpret the whole base+derivation in context; never reinterpret a Melimi
suffix as an ordinary free-standing Telugu word.
ముప్పుకాను = dangerous / characterized by danger; NOT “ముప్పు కాదు”.
పెంపుకాను, హత్తరకాను, పనిమారి, గెలువాను likewise use their documented whole-word meanings.

NOUN/NOMINAL DERIVATION
Documented noun/nominal suffix families include కాను/కాన్, వాను/వాన్,
మారి, పాదు, పఱ, ద/ఇద, అ, అంగి, మాలు, కము/ఇకము, గము, ఓరు, ఆది, ఓలి, ఓజ.
They attach only where Language Space rules support the formation.

VERB DERIVATION
అలవి/అల్వి and అరిది/అర్ది are verb-based. Do not attach these verb
suffixes indiscriminately to nouns.

ADJECTIVES
Supported invariant Melimi adjective forms can function without blindly
adding Standard Telugu adjective suffixes. Example: హాళికాను = ఆసక్తికరం /
ఆసక్తికరమైన; హాళికాను ఎడాటం; ఈ ఎడాటం హాళికానుగా ఉంది.

INFLECTION + GRAMMAR
Preserve ordinary Telugu grammatical architecture: syntax, tense, aspect,
person, number, case, agreement, particles, postpositions and auxiliaries.
Resolve the Melimi lexical root first, then reapply the same grammatical
operation: సమస్య→చిక్కు; సమస్యలు→చిక్కులు; సమస్యలను→చిక్కులను.
Do not maintain a hard-coded derivative list when the same operation can be
applied generically.

GENERATION CONTRACT
Retrieve relevant words/rules/examples before generation. The LLM is the
generation engine, not the Melimi authority. Answer the actual request and
use conversation context for short replies. Do not output meta-instructions,
generic writing advice, or unrelated filler. If no authoritative mapping
exists, do not invent one merely to pass a purity check.
Pipeline: meaning → context/register → retrieval → generation → morphology /
grammar check → lexical validation → natural response.
'''.strip()

def language_constitution() -> str:
    return MELIMI_CONSTITUTION
