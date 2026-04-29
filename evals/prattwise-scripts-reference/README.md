# Prattwise Scripts Reference

Screenshot-derived reference files from the separate `prattwise-scripts` repo used by another NGAIP-362 implementation.

These files are not intended to be copied into Pratt-Backend verbatim. They capture the useful patterns visible in the screenshots:

- RAGAS is used directly for golden testset candidate generation.
- `langchain_openai.OpenAI` / `OpenAIEmbeddings` are used against OpenAI-compatible endpoints.
- ModelHub mints a bearer token with `client_credentials`; the OpenAI call then includes both the ModelHub bearer token and the APIM subscription key.
- PDF input is reduced to extracted text before creating LangChain `Document` objects.
- Candidate rows stay in a reviewable shape before promotion into the official gold dataset.

The NGAIP transfer scripts should use these ideas in a Pratt-Backend shape, not clone this standalone script layout.
