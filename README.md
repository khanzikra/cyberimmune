# CyberImmune

AI security investigator with deterministic claim verification. Built for the Nebius x NVIDIA Global AI Hackathon 2026.

## Setup

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy .env.example to .env and fill in your Nebius credentials
copy .env.example .env
# Edit .env with your NEBIUS_API_KEY, NEBIUS_BASE_URL, NEBIUS_MODEL
```

## How Nemotron and Nebius Token Factory are used

TODO: Document how the NVIDIA Nemotron model is called through Nebius Token Factory.

## Evaluation

TODO: Document the evaluation methodology (rules-only, plain LLM, CyberImmune with tools + verifier).

## Limitations

TODO: Document known limitations (synthetic data only, small N, author-designed patterns, etc.).