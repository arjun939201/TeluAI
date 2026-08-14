# File-content authority rule

Melimi Telugu mode is governed by the actual `melimi_telugu/` subject files.

For every explicit Standard/source -> Melimi mapping in the vocabulary subject:

- the Standard/source form is forbidden in Melimi output;
- the registered Melimi form is the required lexical choice;
- the model is given the mapping before generation;
- the response is checked after generation;
- a failed response is regenerated;
- a deterministic file-derived lexical barrier runs as the final safety net.

This means the language files are not merely retrieval context. They are an
enforceable lexical specification.

Important distinction:

- unknown word != loanword
- ordinary Telugu != automatically Melimi
- file mapping = authoritative
- unsupported invention = prohibited
