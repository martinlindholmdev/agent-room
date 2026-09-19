"""Versioned renderer boundary; legacy bridge/protocol consumers stay unchanged.
Only codes cross the diagnostic boundary, never arbitrary exception text.
"""
def failure(code, acceptance='uncertain'):
    return {'ok': False, 'error': {'code': code, 'acceptance': acceptance}}


def result_envelope(action, result):
    # Cold/unconfigured snapshots have no hub cache yet. Supply the renderer's
    # collection contract without inventing configuration or online status.
    if action == 'snapshot' and isinstance(result, dict):
        result = dict(result)
        for key in ('rooms', 'events', 'sessions', 'bindings', 'receipts', 'objects', 'outbox', 'devices', 'pairing'):
            result.setdefault(key, [])
    # snapshot.error is operational health, NOT an action rejection.
    if action != 'snapshot' and isinstance(result, dict) and result.get('error'):
        return failure('rejected' if result.get('acceptance') == 'rejected' else 'unavailable',
                       'rejected' if result.get('acceptance') == 'rejected' else 'uncertain')
    return {'ok': True, 'result': result}
