# Melimi Telugu Corpus Ruleset

TeluAI treats the supplied **మేలిమి తెలుగు బలుకులు (బంగారు నాణేలు)** corpus as a `MASTER_RULESET` for documented Melimi word formation.

## Runtime hierarchy

```text
MASTER lexical mapping
        +
MASTER corpus formation rules
        +
root-first morphology
        ↓
Melimi generation
```

The ruleset does not authorize vocabulary invention. An unknown root, affix use, or derivation remains unknown unless the Language Space/master data supports it.

## Lemma mapping

`/word SOURCE = TARGET` is a lemma-level mapping. Surface forms are parsed first and the same grammatical operation is regenerated from the target.

Examples:

- `విషయం → ఎడాటం`; `విషయాలు → ఎడాటాలు`
- `పదం → పలుకు`; `పదాలు → పలుకులు`
- `భాష → నుడి`; `భాషా → నుడి`
- `వ్యాకరణం → జక్కం`; `వ్యాకరణ → జక్క`; `వ్యాకరణపు → జక్కపు`
- `స్థాపితం → నెలగొల్పిదం`; `స్థాపితమైన → నెలగొల్పిదమైన`

## Corpus families

The runtime registry contains the supplied:

- మునుజేర్పులు
- కొత్త మునుజేర్పులు
- పదగ్రములు
- పదాంచలములు
- ఆద్యక్షర శేషత formations
- ఆమ్రేడిత formations
- పోలిక/analogy formations
- వెనుజేర్పులు
- adjective-forming suffixes

Important documented suffix families include `కాను/కాన్`, `వాను/వాన్`, `మారి`, `అలవి/అల్వి`, `అరిది/అర్ది`, `పాదు/పఱ`, `ద/ఇద`, `అ`, `అంగి`, `మాలు`, `కము/ఇకము`, `గము`, `ఓరు`, `ఆది`, `ఓలి`, and `ఓజ`.

## Authority rule

The LLM may reason over these rules, but deterministic runtime morphology has priority for transformations. A model-generated Melimi form must not silently become authoritative language data.

## Shared workspaces

Main Chat and Melimi Telugu Lab use the same persistent Melimi Language Space and root dictionary. The Lab provides explicit language commands; Main Chat can consume the resulting MASTER data through normal Melimi processing, while workspace boundaries prevent Lab-only commands from being executed as ordinary Main Chat commands.
