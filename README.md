# TeluAI

**సహజమైన తెలుగు సంభాషణ కోసం రూపొందించిన AI.**

TeluAI యొక్క ప్రస్తుత ఉద్దేశ్యం ఒకటే: వినియోగదారుతో సాధారణంగా తెలుగులో మాట్లాడటం. వినియోగదారు మేలిమి తెలుగు పదం, పద వినియోగం లేదా వ్యాకరణంపై స్పష్టమైన సూచన ఇస్తే, ఆ సూచనను ఆ వినియోగదారుడి వ్యక్తిగత భాషా జ్ఞాపకంగా భద్రపరుస్తుంది. కొత్త సంభాషణల్లో సంబంధిత సందర్భం వచ్చినప్పుడు ఆ జ్ఞాపకాన్ని తిరిగి ఉపయోగిస్తుంది.

## ప్రస్తుత ఉత్పత్తి

```text
వినియోగదారు
   ↓
TeluAI తెలుగు సంభాషణ
   ├─ సహజమైన తెలుగు సమాధానాలు
   ├─ సంభాషణ చరిత్ర
   ├─ వినియోగదారు-వ్యక్తిగత భాషా జ్ఞాపకం
   └─ స్పష్టమైన మేలిమి పద/వ్యాకరణ సూచనల నేర్చుకోవడం
             ↓
        Groq AI
             ↓
        PostgreSQL / SQLite
```

### ముఖ్య నియమాలు

- సాధారణ సంభాషణలో సమాధానం తెలుగులోనే ఉంటుంది.
- ఇంగ్లీష్, రోమన్ తెలుగు లేదా మిశ్రమంగా అడిగినా భావాన్ని అర్థం చేసుకుని తెలుగులో స్పందిస్తుంది.
- సాధారణ మాటలను భాషా పాఠంగా లేదా నిఘంటువు వివరణగా మార్చదు.
- వినియోగదారు స్పష్టంగా ఇచ్చిన భాషా సూచనలను మాత్రమే నేర్చుకుంటుంది.
- ఒక వినియోగదారుడి నేర్చుకున్న సూచనలు మరొక వినియోగదారుడికి కలవవు.
- నేర్చుకున్న వ్యక్తిగత సూచనలు కొత్త సంభాషణల్లో కూడా అందుబాటులో ఉంటాయి.
- AI స్వయంగా ఊహించిన పదాన్ని అధికారిక భాషా జ్ఞానంగా సేవ్ చేయదు.
- మేలిమి తెలుగు పరిశోధన/ల్యాబ్ ఇంటర్‌ఫేస్ ప్రస్తుతం ఉత్పత్తిలో భాగం కాదు; అది తరువాతి దశకు వదిలివేయబడింది.

## Quality evaluation

The quality-evaluation layer uses a stable Pydantic contract in `quality_evaluation/schema.py`. Each evaluation reports four normalized metrics on a `0..1` scale:

- **Relevance** — how directly the response addresses the request.
- **Coherence** — clarity, consistency, and logical flow.
- **Factual accuracy** — correctness of claims when factual assessment is applicable.
- **Toxicity** — harmful, abusive, or unsafe language signals; higher scores represent better quality after the metric is normalized.

The API contract also carries an overall normalized score and an evaluator version. Unknown fields are rejected so schema drift is caught early by tests and CI.

## Runtime

`app.server:app` మాత్రమే ప్రస్తుత canonical production entrypoint.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.server:app --reload
```

Render/Docker కూడా ఇదే entrypoint ఉపయోగిస్తాయి.

## Configuration

`.env.example` ఆధారంగా అవసరమైన విలువలను అమర్చండి.

```text
GROQ_API_KEY
GROQ_MODEL
GROQ_FALLBACK_MODEL
DATABASE_URL
SESSION_DAYS
COOKIE_SECURE
CORS_ORIGINS
```

Provider keys లేదా ఇతర secrets ను browserలో ఎప్పుడూ పంపకూడదు.

## Database learning model

భాషా సూచనల కోసం `user_memory` ఆధారంగా వ్యక్తిగత జ్ఞాపకం ఉపయోగించబడుతుంది:

```text
స్పష్టమైన వినియోగదారు సూచన
        ↓
తెలుగు పదం / వ్యాకరణ సూచన గుర్తింపు
        ↓
ఆ వినియోగదారుడి వ్యక్తిగత జ్ఞాపకంలో భద్రపరచడం
        ↓
కొత్త సంభాషణలో సంబంధిత సందర్భానికి తిరిగి ఇవ్వడం
```

సాధారణ సంభాషణ, ఊహ, లేదా TeluAI స్వంత సమాధానం స్వయంగా నేర్చుకునే డేటాగా మారదు.

## Health

```text
GET /health
GET /health/ready
```

`/health/ready` database connectivityని తనిఖీ చేస్తుంది.

## Scope

ప్రస్తుత దశను ఉద్దేశపూర్వకంగా చిన్నదిగా ఉంచాం: **తెలుగు AI chat + వ్యక్తిగత మేలిమి భాషా learning memory**. అదనపు భాషా పరిశోధన సాధనాలు తరువాత ప్రత్యేక దశలో చేర్చవచ్చు.
