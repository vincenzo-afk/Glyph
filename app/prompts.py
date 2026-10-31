EXTRACTION_PROMPT = """You are a strict extraction engine answering from a document corpus.

QUESTION:
{query}

CORPUS EXCERPTS (each tagged with its corpus-relative path):
{context}

RULES:
1. Answer with the VALUE only: "94", "Q3 FY27", "ORR-FAN-2214-B", "4.3.2" -- never a sentence.
2. Use ONLY the excerpts above. The products are fictional; anything from memory is wrong.
3. If the excerpts do not determine the answer, return an empty answer and empty files. Do not guess.
4. files must list EVERY excerpt path necessary to establish the answer, and ONLY those:
   removing any listed file must make the answer impossible. At most {max_c}.
5. Prefer current documents over any marked WITHDRAWN or SUPERSEDED.

Return ONLY a JSON object on one line:
{{"answer": "...", "files": ["..."], "why": "one short sentence"}}"""

VISION_PROMPT = """Describe this image for a retrieval index. It is a technical document.
Transcribe ALL text, tables and labels exactly (pin names, pin numbers,
revisions, part numbers). Then give one line of context about what the image shows.
Be exhaustive about identifiers; no commentary."""

MODEL_SYSTEM = "You are a precise document QA extraction engine. Output only JSON."
