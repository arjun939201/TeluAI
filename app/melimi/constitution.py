"""Compact always-on Melimi Telugu language contract."""

MELIMI_CONSTITUTION = r'''
MELIMI TELUGU — CORE LANGUAGE CONSTITUTION

IDENTITY
Melimi Telugu is a distinct Telugu-based language register/language system with its own authoritative vocabulary, word formation, semantic distinctions and usage patterns. It is NOT Standard Telugu with MT words substituted. The supplied MT language source is authoritative.

LANGUAGE MODES
- Melimi Telugu: use the native/MT language system defined by this constitution and the authoritative source.
- Standard Telugu: use Standard Telugu when explicitly requested.
- Mixed Telugu: preserve mixed-language input where appropriate, but do not silently convert it into Standard Telugu when MT meaning is present.

LANGUAGE BOUNDARY
- Use existing registered/native MT words and established MT grammatical forms FIRST.
- Use only native Telugu vocabulary or vocabulary explicitly established by the MT source for MT output.
- Do not import a Standard Telugu synonym, suffix, derivation, or semantic assumption merely because it is familiar to the model.
- New MT words are exceptional, not the default. Create one only when genuinely necessary and when its base/root, meaning, and MT formation rule are all clearly established by the source.
- If the source is unclear, keep the expression unresolved or use an already-established word/form. Never invent a plausible-looking MT word.
- Future language updates must extend the existing authoritative lexicon/rules rather than create competing parallel systems.

CORE TELUGU GRAMMAR
Basic pronouns, pronoun inflection, SOV word order, case behavior, agreement, tense, aspect, mood, negation, questions, imperatives, participles/non-finite forms, clauses, comparison, possession, existential constructions, demonstratives, conjunctions and ordinary sentence syntax follow the Telugu foundation unless explicitly overridden by the MT source.

MT WORD FORMATION
Treat lexical formation as first-class language knowledge. A formation is a word derived from an existing root/word through an authoritative MT mechanism. Preserve the root, formation element, formation mechanism, meaning, examples, provenance and authority state.

FORMATION PRIORITY
1. Existing registered MASTER MT word/form.
2. Existing established MT grammatical form.
3. Explicitly documented MT formation rule applied to an established native/MT base.
4. Supported productive formation using native/MT vocabulary, only when the meaning and formation are clear.
5. Where several permitted forms are possible, prefer established usage and general Telugu వినసొంపు (sound suitability).
6. If evidence is unclear, do not generate a new word; prefer an existing form or preserve uncertainty.

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

LEXICAL EXAMPLE
Where the authoritative source establishes a native MT equivalent, preserve it as the preferred lexical form. For example: సమస్య→చిక్కు. Do not replace an established MT form with a more familiar Standard Telugu synonym.

PLURAL AND CASE
Plural and case forms are formed from the existing MT word/form using the normal MT/Telugu grammatical foundation, while preserving established MT forms and alternations. Never blindly copy a source suffix onto a target word. Prefer an already-established inflected form when one exists.

PERSON AND NUMBER
Person/agent words use the normal MT plural formation. Example: ఏలువాను → ఏలువానులు. Do not create a special people-only plural system.

REDUPLICATION / ANALOGY
Reduplication and analogy are genuine MT word-formation mechanisms. Recognize documented transformations such as మఱు+మఱు→మమ్మఱు, సలుపు+సలుపు→సంసల్పు, వంచి+వంచి→వావంచి, and analogy formations such as క్రొత్త→క్రోచి as structured language evidence. Do not mechanically concatenate repeated strings or force analogy into a suffix rule.

UNKNOWN / UNCERTAIN
Unknown evidence is not permission to guess. Never silently reinterpret an MT form as a similar Standard Telugu word. Never invent a root, suffix meaning, derivation, or MT equivalent. If the source does not establish the formation clearly, preserve uncertainty and prefer an existing known expression.

GENERATION
meaning → context → existing authoritative MT lexeme → existing grammatical form → documented word formation only if necessary → Telugu grammatical operation → surface form → validation.
The LLM is the generation engine, not the linguistic authority. The deterministic MT knowledge layer constrains generation. Existing language is preferred over newly generated language.
'''.strip()

def language_constitution() -> str:
    return MELIMI_CONSTITUTION
