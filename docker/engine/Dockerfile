# Maya engine for the practice-pack items: the app image plus document and audio tools.
# pypdf (BSD-3) instead of PyMuPDF (AGPL-3.0), see docs/research/05_docs_and_code.md.
FROM maya-app

RUN pip install --no-cache-dir pypdf rank_bm25 soundfile

WORKDIR /app
