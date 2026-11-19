# Troubleshooting

The messages you may see, what they mean, and what to do. In most cases the agent handles them itself; this page is
for when you want to understand what happened.

## "BLOCKED ... may not write ..."

The guard stopped a change to something protected: an existing source, your saved messages, or an owner file
(charter, settings, the KB's own tools) through the shell. Sources are replaced by freezing a new one; owner files
change only through an edit you approve. Nothing to do unless you asked for that change.

## "changed by role ... which may not write it" in `kb.py check`

A script or command changed a protected file. The agent runs `uv run tools/kb.py restore`, which undoes exactly the
flagged changes and nothing else, then makes the intended change properly. If **you** changed it by hand on purpose,
say so; `uv run python tools/hooks/guard.py clear`, run in your own terminal, accepts the current state.

## "claim changed or removed since last commit without a history/ entry"

A claim was edited or deleted without keeping the old version. Usually a hand edit. The agent restores the note and
files the change as a correction (old value to `history/`).

## `kb.py commit` refuses

`kb.py check` is not clean - the message lists the problems; the agent fixes them first. With `[review] mode =
"always"` in `kb.toml`, the change also needs an approved review of exactly this change: the agent runs the reviewer.

## "number(s) ... not in any cited source" / "date(s) ... not in any cited source"

A claim states a number or date that none of its cited sources contains. Either the claim cites the wrong source
(the agent cites the one that states the number) or the claim is wrong. This check catches misread figures; it never needs disabling.

## The first reply lists messages of yours that were not filed

`owner_messages_not_filed_7d` in the session-start report: your recent messages that no claim cites. Most are tasks
and chat; the agent mentions only those that look durable. Say "file that one" or ignore it.

## The first reply mentions "unfinished filing" or "commits outside kb.py commit"

- *Unfinished filing*: a previous session stopped before its change was committed (for example you ran out of
  usage). Say "finish that".
- *Commits outside kb.py commit*: someone (usually you, in your own terminal) committed notes without review. Ask the
  agent to check that commit; correct anything it finds through `fix`.

## Permission prompts

The KB pre-approves its own tools (`uv run tools/kb.py`, `uv run tools/fetch.py`, read-only git, and scripts in
`work/`). Other commands prompt as usual in Claude Code. Edits to `charter.md`, `CLAUDE.md`, `CONVENTIONS.md`,
`kb.toml`, `.claude/` and the scaffold tools always prompt: approve them only when you asked for that change.

If **every** `kb.py` call prompts, a global hook may be rewriting commands (for example a command-compression hook
that prefixes `rtk`). Exclude the KB folder from it, or add the rewritten form to `.claude/settings.local.json`.

## "guard heartbeat missing or stale"

`kb.py check` found that the hooks have not run recently in this session: Claude Code did not load
`.claude/settings.json` (start `claude` in the KB folder; accept the folder trust prompt) or `uv` is not on the
PATH. Until fixed, writes are unguarded.

## Search does not find a note you know exists

Say so ("search missed X, it's in note Y"). The agent adds aliases or fixes the title. Repeated misses also show up
in `kb.py stats`. With semantic search configured, meaning-only matches help, but keyword search stays the source of
truth.

## Two sessions at once

Do not. The guard cannot tell which session changed what, and a `restore` in one session can undo the other's work.
Work in one session per KB.
