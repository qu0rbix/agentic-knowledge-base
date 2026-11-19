# Getting started

This guide takes you from nothing to a working knowledge base (KB) with its first notes. It takes about 30 minutes,
most of it answering the setup interview.

## Requirements

- [Claude Code](https://claude.com/claude-code) (the CLI), signed in.
- [uv](https://docs.astral.sh/uv/) - runs the Python tools; no other Python setup is needed.
- git.
- Windows, macOS or Linux. The test suite and all live case studies ran on Windows; Linux and macOS are expected to work but have not been exercised end to end.

## 1. Create your KB

Your KB is your own repository. It does not track this template repository, so you receive no surprise changes and
your notes never point back here.

```bash
uv run https://raw.githubusercontent.com/qu0rbix/agentic-knowledge-base/main/scripts/create_kb.py my-kb
cd my-kb
```

This downloads only the `template/` folder, runs `git init` and makes a first commit. Alternatives: click **Use this
template** on GitHub, or copy the folder from a clone with `scripts/new-kb.sh ~/my-kb` (`scripts\new-kb.ps1` on
Windows).

If you want a backup, add your own private remote: `git remote add origin <your-repo-url>`.

## 2. Run the setup interview

```bash
claude
```

Then say:

> set up this KB

The `init-kb` skill interviews you, one topic at a time:

1. **Purpose** - who uses the KB and for which decisions.
2. **Must-answer questions** - 10 to 30 real questions. They become `eval/golden.md`, the KB's regression tests.
3. **Scope** - what is in, and explicitly what is out.
4. **Sources** - where knowledge comes from, and how much you trust each kind (tiers 1-4).
5. **Volatility** - what changes often and needs dates.
6. **Recurring work** - reports, analyses, data systems.
7. **Languages** - which languages you work in, and the one language notes are written in.
8. **Approval** - what the agent may change without asking.
9. **Semantic search** - optional; you can skip it and add it later ([configuration](configuration.md)).

It then shows you `charter.md`, `eval/golden.md` and the project block of `CLAUDE.md` before saving them. Claude
Code asks you to approve these edits: approve them, because you asked for them.

Keep the first interview short. You can refine the charter any time by saying "update the charter: ...".

## 3. Add your first sources

Put two or three core documents in a folder inside the KB (for example `work/`) and say:

> ingest the files in work/

Watch what happens the first time - see [Ingest a source](workflows.md#ingest-a-source). The agent freezes each file,
files the facts that pass the charter's admission test with a citation of the source, runs the checks and commits. A
few documents take a few minutes.

When it is done, open `notes/` and read what was filed. Every claim ends with a short citation: the source id and where in it.

## 4. Ask something

> what is the support window for X?

The agent answers from the notes and tells you which note and source it used, or says the KB does not know.

## The five rules

Everything else is handled by the agent. These five are yours:

1. **Start `claude` in the KB folder**, and work in **one session per KB** at a time.
2. **Hand over files, not pastes.** Save a document or a query result to a file and say "ingest this". If you do paste, say what it is ("this is the output of `describe orders`") - otherwise it may be filed as your own statement.
3. **Never edit `notes/` or commit yourself.** Say what is wrong instead ("that's outdated: ..."); the agent files the correction with history. If you did edit or commit by hand, the next session reports it.
4. **Approve edits to `charter.md`, `CLAUDE.md`, `kb.toml` or `.claude/` only when you asked for them.**
5. **Read the first reply of each session.** It lists anything that needs you: an unfinished filing, a commit made by hand, a message of yours that looks worth filing.

Once a week, say **"audit the KB"**: a reviewer agent checks the week's filings against their sources.

Next: [Concepts](concepts.md) explains the moving parts; [Workflows](workflows.md) covers daily use.
