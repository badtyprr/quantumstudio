"""Authored checks after the four descriptor-bound original source cells."""
if __name__ == '__main__':
    _qb013_capture.check_after(
        (13, 15, 19, 22)[len(_qb013_capture.controller.postcells)],
        _qb013_reference, _qb013_audit)
