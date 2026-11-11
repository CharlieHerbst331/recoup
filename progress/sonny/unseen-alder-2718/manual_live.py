"""One manual live load, not an automated test. No evaluator expectations enter requests."""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/data/app')
OUT = ROOT / 'progress/sonny/unseen-alder-2718/live'
CASE = 'ALDER-2718'
BUNDLE = ROOT / 'cases/unseen/alder-2718/bundle.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(name, value):
    path = OUT / name
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    # Reuse the active server's environment in memory, never serialize secrets.
    pid = json.loads(Path('/data/server-state.json').read_text())['pid']
    server_env = dict(
        entry.split('=', 1)
        for entry in Path(f'/proc/{pid}/environ').read_text().split('\0')
        if '=' in entry
    )
    for key in ('RECOUP_LLM', 'RECOUP_MODEL', 'RECOUP_DB', 'OPENAI_BASE_URL', 'OPENAI_API_KEY', 'RECOUP_VISION'):
        if key in server_env:
            os.environ[key] = server_env[key]
    assert os.environ.get('RECOUP_LLM') == 'live'
    assert os.environ.get('RECOUP_MODEL') == 'claude-haiku-5-5'
    assert os.environ.get('OPENAI_API_KEY')
    for name in ('openai', 'httpx', 'httpcore', 'httpx2', 'httpcore2'):
        logger = logging.getLogger(name)
        logger.handlers = [logging.NullHandler()]
        logger.propagate = False

    from recoup.app import RecoupConfig, build
    from recoup.engine.rules import run_rules

    app = build(RecoupConfig.from_env())
    try:
        assert app.llm.mode == 'live' and app.llm.model_id == os.environ['RECOUP_MODEL']
        existing = [v.case_id for v in app.world.list_cases()]
        assert CASE not in existing
        assert not app.world.pending_events(), 'Existing pending events require separate handling'
        before = {
            c: digest(app.history(c).model_dump_json().encode()) for c in existing
        }
        recordings = ROOT / 'runs/recordings'
        old = {p.name: digest(p.read_bytes()) for p in recordings.glob('*.json')}
        source_paths = ['recoup/app.py', 'recoup/engine/harness.py', 'recoup/engine/rules.py', 'recoup/engine/tools.py', 'recoup/engine/llm/openai_compat.py', 'recoup/engine/llm/replay.py', 'recoup/engine/prompts/system_v1.md']
        save('manifest.json', {
            'case_id': CASE, 'llm_mode': app.llm.mode, 'configured_model': app.llm.model_id,
            'provider_base_url': app.config.base_url, 'database': app.config.db,
            'run_id': app.config.run_id, 'started_at_utc': datetime.now(timezone.utc).isoformat(),
            'bundle_sha256': digest(BUNDLE.read_bytes()),
            'source_sha256': {p: digest((ROOT / p).read_bytes()) for p in source_paths},
            'existing_history_sha256': before, 'recordings_before_sha256': old,
            'path': 'recoup.app.build(RecoupConfig.from_env()).load([new bundle directory])',
            'provenance': 'SYNTHETIC data; MOCK actions; LLM live',
        })
        error = None
        loaded = None
        try:
            loaded = [r.model_dump(mode='json') for r in app.load([str(BUNDLE.parent)])]
        except Exception as exc:
            # Provider internals may contain secrets. Actual sanitized harness stop is in history.
            error = type(exc).__name__
        finally:
            view = app.world.view(CASE)
            history = app.history(CASE)
            save('view.json', view.model_dump(mode='json'))
            save('history.json', history.model_dump(mode='json'))
            with (OUT / 'chronology.jsonl').open('x') as stream:
                for ordinal, trace in enumerate(history.traces, 1):
                    stream.write(json.dumps({'ordinal': ordinal, **trace.model_dump(mode='json')}) + '\n')
            save('rules-after-run.json', [f.model_dump(mode='json') for f in run_rules(view.lines, app.world.fact_set(CASE), app.world.ledger(CASE))])
            after = {c: digest(app.history(c).model_dump_json().encode()) for c in existing}
            new = {p.name: digest(p.read_bytes()) for p in recordings.glob('*.json') if p.name not in old}
            archive = OUT / 'recordings'
            archive.mkdir()
            for name in new:
                with (archive / name).open('xb') as stream:
                    stream.write((recordings / name).read_bytes())
            save('outcome.json', {
                'finished_at_utc': datetime.now(timezone.utc).isoformat(), 'load_result': loaded,
                'exception_type': error, 'status': view.status.value, 'status_reason': view.status_reason,
                'existing_histories_unchanged': before == after,
                'existing_history_sha256_after': after,
                'existing_recordings_unchanged': all((recordings / n).exists() and digest((recordings / n).read_bytes()) == h for n, h in old.items()),
                'new_recordings_sha256': new,
                'model_calls': sum(t.kind == 'model_call' for t in history.traces),
                'tool_calls': sum(t.kind == 'tool_call' for t in history.traces),
                'accepted_end_count': sum(t.tool == 'end' and bool((t.result or {}).get('result', {}).get('accepted')) for t in history.traces),
                'approvals': len(history.approvals), 'receipts': len(history.receipts),
                'pending_events': len(app.world.pending_events()),
            })
            with (OUT / 'drafts.md').open('x') as stream:
                stream.write('# Actual saved drafts — SYNTHETIC / MOCK / LLM live\n\n')
                for p in history.proposals_all:
                    stream.write(f'## {p.kind.value}: {p.proposal_id} v{p.version}\n\nStatus: {p.status.value}; recipient: {p.recipient}\n\n{p.draft_text}\n\n')
            secret = os.environ['OPENAI_API_KEY'].encode()
            assert all(secret not in p.read_bytes() for p in OUT.rglob('*') if p.is_file())
            print(json.dumps({'case_id': CASE, 'status': view.status.value, 'status_reason': view.status_reason, 'artifact_directory': str(OUT)}))
    finally:
        app.world.close()
        app.llm.client.close()


if __name__ == '__main__':
    main()
