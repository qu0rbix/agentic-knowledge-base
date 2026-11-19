# agentic-knowledge-base

A template for a personal work knowledge base that [Claude Code](https://claude.com/claude-code) maintains for you.

You hand it documents, ask it to research, and simply work with it. It keeps what is worth knowing as short, cited
notes in plain markdown - and keeps them correct: every claim cites its source, every change keeps the old value, and
a reviewer agent checks the filings against their sources whenever you ask for an audit.

```
you:    ingest work/2024-03-12-ops-review.md
agent:  Froze the source. Filed 4 claims (2 new, 1 merged, 1 supersedes the old
        on-call rotation - old value kept in history/). Skipped 6 (task status,
        chit-chat). Checks clean. Committed: kb: ingest 2024-03-12-ops-review

you:    btw Jonas took over the Fivewire contract last week
agent:  Noted - filed under vendors/fivewire, citing your message.

you:    who owns the Fivewire contract?
agent:  Jonas, since 2024-03-05 [notes/fivewire, your message of 2024-03-12].
```

## Why

Notes an LLM writes for itself drift: claims lose their source, old values are silently overwritten, session chatter
piles up, and a confident wrong answer looks the same as a right one. This template treats your knowledge base like
code with tests:

- **Evidence by code.** Sources are frozen byte for byte; your own messages are saved by a hook. A citation to a source
  that does not exist, or a number or date that is not in the cited source, fails the check.
- **Checks on every commit, review when it pays.** Citations, numbers and history are checked by code on every commit.
  A reviewer agent reads claims cold next to their sources in a weekly audit - or on every filing, if you want that.
- **History, not overwrites.** A changed fact moves the old one to `history/` with the date and the reason.
- **An admission test.** Task status, today's error and small talk stay out. A typical document yields 0-8 claims.
- **Any language, no trigger words.** Talk normally; the agent decides what is durable.
- **No database, no schedule.** Markdown in git and a few small Python tools run with `uv`. Optional semantic search
  with your own embedding provider or a local model.

## Quick start

Requirements: Claude Code, [uv](https://docs.astral.sh/uv/) and git.

```bash
uv run https://raw.githubusercontent.com/qu0rbix/agentic-knowledge-base/main/scripts/create_kb.py my-kb
cd my-kb
claude
```

Then say **"set up this KB"**. A short interview turns your goals into a charter, and you are ready to ingest your
first documents. The new KB is your own repository, with no link back to this one.

Full walkthrough: [Getting started](docs/getting-started.md).

## Daily use

| You want to | You say | Guide |
|---|---|---|
| Add a document or web page | "ingest work/report.pdf" | [Ingest](docs/workflows.md#ingest-a-source) |
| Fill a gap in the KB | "research X's API limits" | [Research](docs/workflows.md#research-to-grow-the-kb) |
| Just work | anything - durable facts are captured as you go | [Co-work](docs/workflows.md#co-work-learning-while-you-work) |
| Know something | ask | [Ask](docs/workflows.md#ask-a-question) |
| Fix or remove a fact | "that's outdated: ..." / "forget ..." | [Correct or forget](docs/workflows.md#correct-something-or-forget-it) |
| Document a database table | "ingest this describe output" | [Data and SQL](docs/workflows.md#data-and-sql) |
| Check the KB (weekly) | "audit the KB" | [Audit](docs/workflows.md#audit-the-kb) |
| Reorganise | "group the vendor notes" | [Refactor](docs/workflows.md#refactor-the-kb) |

Five rules are yours; the agent handles everything else:

1. Start `claude` in the KB folder, one session per KB at a time.
2. Hand over files rather than pastes - or say what a paste is.
3. Never edit notes or commit yourself; tell the agent what is wrong.
4. Approve edits to `charter.md`, `CLAUDE.md`, `kb.toml` or `.claude/` only when you asked for them.
5. Read the first reply of a session: it lists anything that needs you.

## Documentation

- [Getting started](docs/getting-started.md) - create a KB, the setup interview, first ingest
- [Concepts](docs/concepts.md) - notes, claims, sources, the agents, what is enforced
- [Workflows](docs/workflows.md) - daily use, step by step
- [Configuration](docs/configuration.md) - `kb.toml`, models, semantic search, upgrading
- [Troubleshooting](docs/troubleshooting.md) - the messages you may see
- [Backlog](docs/backlog.md) - known gaps and promising ideas
- [Project history](docs/project/) - design notes, experiments and reviews

## Status

Ready for supervised personal use: one owner, one KB, one session at a time. Every version was reviewed and tested
with Claude Haiku agents (a deliberately weak model) on synthetic and real public documents, including live headless
runs of Claude Code. The decisive test on real documents compared this design with and without a reviewer on every
filing, and with a plain LLM wiki - see [experiments](docs/project/experiments.md); the default follows from it. Not
yet verified: the setup interview in a live session, stronger models than Haiku, Linux and macOS. See the
[backlog](docs/backlog.md).

## Development

```bash
cd tests && uv run python -m unittest discover -s .
```

The tests replay the hooks and tools without a model. `template/` is what users get; `experiments/` holds the case
study harnesses.

## License

MIT - see [LICENSE](LICENSE).
