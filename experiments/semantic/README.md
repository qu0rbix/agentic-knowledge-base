# Semantic search benchmark

Reproduce: copy `template/` to a scratch folder, `uv run python experiments/semantic/build.py <folder>` (writes notes, history and queries.txt), set the KB_EMBED_* variables, then in the folder run `uv run tools/kb.py embed`, `uv run tools/kb.py search-eval <path>/queries.txt --calibrate` and `uv run python <path>/sim_eval.py <path>/extra.json`. Results: `result.txt` and docs/project/experiments.md.
