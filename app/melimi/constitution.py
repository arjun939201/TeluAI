"""Compact always-on Melimi Telugu language contract."""

MELIMI_CONSTITUTION = r'''
MELIMI TELUGU — CORE LANGUAGE CONSTITUTION

IDENTITY
Melimi Telugu is a native Telugu-based language system with its own authoritative vocabulary, word formation, semantic distinctions and usage patterns. It is NOT Standard Telugu with MT words substituted. The supplied MT language source is authoritative.

LANGUAGE BOUNDARY
- Use native Telugu grammatical foundations unless the MT source explicitly establishes a different rule.
- Use only established/native MT vocabulary and MT word-formation rules supported by the project source.
- Do not import a Standard Telugu synonym, suffix, derivation, or semantic assumption merely because it is familiar to the model.
- If an MT form is not sufficiently supported, keep it unresolved rather than inventing a form or silently translating it through Standard Telugu.

CORE TELUGU GRAMMAR
Basic pronouns, pronoun inflection, SOV word order, case behavior, agreement, tense, aspect, mood, negation, questions, imperatives, participles/non-finite forms, clauses, comparison, possession, existential constructions, demonstratives, conjunctions and ordinary sentence syntax follow the Telugu foundation unless explicitly overridden by the MT source.

MT WORD FORMATION
Treat lexical formation as first-class language knowledge. A formation is a word derived from an existing root/word through an authoritative MT mechanism. Preserve the root, formation element, formation mechanism, meaning, examples, provenance and authority state.

FORMATION PRIORITY
1. Established MASTER MT word/form.
2. Explicitly documented MT formation rule.
3. Supported productive formation using native/MT vocabulary.
4. Where several permitted forms are possible, use established usage and general Telugu వినసొంపు (sound suitability).
5. If the evidence is unclear, do not generate.

PREFIXES
A prefix may have multiple meanings/functions. Do not collapse one prefix to one gloss. For example:
- అలన్ can mean గతము or మరల మరల according to documented usage.
- ఎస can participate in the documented ఎక్కువ/తక్కువ sense.
Store each documented sense with its examples and context.
Preserve documented surface variants such as అలన్, ఎడ/ఎడన్, మరు/మారు, మున్/మును, వెన్/వెను/వెనుక, etc. Do not invent distribution rules for variants that are not established.

SUFFIXES / AGENT FORMS
- కాను is the preferred productive agent/doer suffix and means చేయునట్టి; it may yield agent, doer or characterized-by meanings according to established lexical usage: ముప్పుకాను, పాటకాను, నడకాను, త్రోవకాను, పెంపుకాను, పాటుకాను, విలుకాను, రుత్తుకాను, పాలికాను, జరిమికాను, క్రచ్చుకాను, మసటుకాను, అడంకాను.
- కాన్ is recognized, but do not newly generate it until its usage is established.
- అరి remains active.
- కాఁడు, గాఁడు, కత్తె are legacy alternatives and must not be selected for new productive formations; existing vocabulary may be recognized.
- When choosing among permitted forms, use established usage and వినసొంపు; do not force one suffix merely by English meaning.
- వాను/వాన్ expresses కలిగిన/సంబంధించిన where supported: నెనరువాను, మైవాను, నిలువాను, ఏలువాను.
- -ఇత is a productive explicit feminine formation for suitable person/agent words: ఏలువాను → ఏలువానిత. The unmarked agent form is the default/neutral/male-compatible form; do not invent a masculine suffix.

OTHER DOCUMENTED FORMATION FAMILIES
Use only where the base, meaning and formation are sufficiently clear from the MT source:
- అలవి/అల్వి = చేయుటకు శక్యము, సాధ్యము, యోగ్యము, అర్హము.
- అరిది/అర్ది = అలవి యొక్క వ్యతిరేకార్థము.
- పాదు = suitable/capable-of for supported nominal bases.
- పఱ = పాదు యొక్క వ్యతిరేకార్థము; తగనిది.
- మాలు = రహితము.
- కము/ఇకము = documented abstract/state formation.
- గము = మొత్తం/గుంపు.
- ఓరు = సంస్థ/వ్యవస్థ.
- ఆది = మొత్తం/సమాహారం/సమూహం.
- ఓలి = వరుస.
- ఓజ = క్రమము/విధము/విధానము/శైలి.
- ద/ఇద, అ, అంగి and documented adjective-forming families are available only within their established source limits.

ADJECTIVES
Some words directly function as noun and adjective. Others require an established derivation. Do not assume every noun needs an adjective suffix. Do not turn కాను into a generic adjective suffix; it is a doer/agent formation with documented semantic behavior. Example: హాళి = interest; హాళికాను = interesting is an established lexical formation.

PLURAL AND CASE
Plural and case forms are formed from the existing MT word/form using the normal MT/Telugu grammatical foundation, while preserving established MT forms and alternations. Never blindly copy a source suffix onto a target word.

PERSON AND NUMBER
Person/agent words use the normal MT plural formation. Example: ఏలువాను → ఏలువానులు. Do not create a special people-only plural system.

REDUPLICATION / ANALOGY
Reduplication and analogy are genuine MT word-formation mechanisms. Recognize documented transformations such as మఱు+మఱు→మమ్మఱు, సలుపు+సలుపు→సంసల్పు, వంచి+వంచి→వావంచి, and analogy formations such as క్రొత్త→క్రోచి as structured language evidence. Do not mechanically concatenate repeated strings or force analogy into a suffix rule.

UNKNOWN / UNCERTAIN
Unknown evidence is not permission to guess. Never silently reinterpret an MT form as a similar Standard Telugu word. Never invent a root, suffix meaning, derivation, or MT equivalent. If the source does not establish the formation clearly, preserve uncertainty.

GENERATION
meaning → context → authoritative MT root/lexeme → documented word formation → Telugu grammatical operation → surface form → validation.
The LLM is the generation engine, not the linguistic authority. The deterministic MT knowledge layer constrains generation.
'''.strip()

def language_constitution() -> str:
    return MELIMI_CONSTITUTION
