# Feedback for Nebius x NVIDIA Global AI Hackathon

## What was confusing
- The model (Nemotron 3 Ultra) sometimes continues calling tools even when it has enough evidence, instead of producing the final Investigation JSON. It hit the 6-round / 10-tool-call limit without concluding.
- Tool schema validation rejects unknown arguments (e.g., `resource` is not a valid parameter for `query_events`), but the model tries to use it anyway.

## What was slow or failed
- Phase 3: Real model investigation hit `limit_reached` status after 6 rounds / 6 tool calls without producing final JSON. The model gathered evidence (queried events, baseline, context) but didn't transition to the final answer.
- API authentication initially failed due to using Nebius base URL with NVIDIA API key; fixed by using `https://integrate.api.nvidia.com/v1`.

## What worked well
- Phase 0: Nebius/NVIDIA API connection works with native tool calling.
- Phase 1: Deterministic synthetic data generation (seed=42) and baseline rules (R1-R4) all tested and working.
- Phase 2: Three read-only tools with strict validation, parameterized SQL, audit logging, and untrusted text truncation.
- Phase 3: Investigation loop infrastructure works perfectly with fake LLM (all 7 tests pass). Native tool calling and JSON fallback modes both implemented.

## Suggestions for Nebius and NVIDIA
- Consider adding a "stop" tool or clearer instruction in the system prompt to encourage the model to conclude when it has sufficient evidence.
- The Nemotron model seems to need stronger guidance to output the final structured JSON instead of continuing tool calls.
- Documentation on which base URL to use with NVIDIA API keys vs Nebius API keys would be helpful.