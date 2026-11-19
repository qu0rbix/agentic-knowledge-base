# Fable review 6 - what to do after case E

Asked: should the scaffold switch to light Wikipedia-style citing (cite only dates, versions, numbers, decisions and
owner statements; no quotes), keep a deterministic number check without quotes, make the audit newest-source driven,
and re-check old claims when a new source arrives?

Verdict: agree with the direction, with three changes.

1. **The evidence pack must change, not only the prompt.** The case E audit prompt already asked whether a newer source
   superseded each claim, and quote-citing KBs still scored 0/12 on natural errors. So `kb.py verify` must stop showing
   the cited passage first and instead list the sources on the claim's subject, newest first, with the cited one
   marked. The reviewer prompt follows: read the newest source first; a citation is where a claim came from, not proof
   it is still true; "stale" means a newer source in `sources/`, cited or not, says otherwise.
2. **Keep a citation on every bullet; drop only the quotes.** The length saving in case E came from quotes (36% of the
   text), not from ids. "Decision / policy / contested" cannot be detected by code, so "cite only what matters" is half
   enforceable and would drift. Keeping `[src: id §locator]` on every bullet leaves the uncited-prose rule, history,
   staleness, `uncited_sources` and forget unchanged. Owner citations keep their quote (the commit and stats logic
   depends on it, and the owner's words are the source).
3. **Number and date check against the cited source file** instead of the quote. Weaker (a mangled number passes if it
   occurs anywhere in the file) but still catches invented and mangled figures.

Also: re-check what a new source changes at filing time (search the notes for its subjects and supersede now) and in
the audit (notes about sources frozen since the last audit), without a new command; re-key `coverage` on numbers and
names, since it matched quotes. Leave the `CIT` regex unchanged so old quoted notes stay valid.

Risks named: the combination is untested (run one case E replicate on the changed scaffold before real use); the
file-level number check is weaker; owner quotes still anchor; old quoted notes keep anchoring until touched;
search-first depends on keyword recall over sources, including other languages.

Applied in the commit "Light citations and newest-source review"; the validation replicate is recorded in
`../experiments.md` (case E, KB-new).
