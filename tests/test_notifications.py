"""Tests for Telegram delivery: several recipients, and honest success reporting."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import config, notifications  # noqa: E402

OK = json.dumps({"ok": True, "result": {}})
BLOCKED = json.dumps({"ok": False, "error_code": 403, "description": "Forbidden: bot was blocked by the user"})


def _run(chat_ids, replies):
    """Send one message; `replies` maps chat id -> (returncode, stdout)."""
    sent_to = []

    def fake_run(cmd, **kwargs):
        chat = next(a.split("=", 1)[1] for a in cmd if a.startswith("chat_id="))
        sent_to.append(chat)
        code, out = replies[chat]
        return SimpleNamespace(returncode=code, stdout=out, stderr="")

    with patch.object(config, "TELEGRAM_BOT_TOKEN", "123:abc"), \
         patch.object(config, "TELEGRAM_CHAT_ID", chat_ids), \
         patch("lib.notifications.subprocess.run", side_effect=fake_run):
        return notifications.send_telegram_notification("hello"), sent_to


def test_single_chat_id_still_works():
    result, sent_to = _run("111", {"111": (0, OK)})
    assert result is True and sent_to == ["111"]


def test_every_listed_chat_gets_the_message():
    result, sent_to = _run("111, 222 ,333", {c: (0, OK) for c in ("111", "222", "333")})
    assert result is True
    assert sent_to == ["111", "222", "333"]


def test_one_blocked_recipient_does_not_stop_the_others():
    result, sent_to = _run("111,222", {"111": (0, BLOCKED), "222": (0, OK)})
    assert sent_to == ["111", "222"]
    assert result is True            # at least one person was told


def test_telegram_refusal_is_not_reported_as_sent():
    """curl exits 0 on an HTTP 403, so the reply body must decide."""
    result, _ = _run("111", {"111": (0, BLOCKED)})
    assert result is False


def test_curl_failure_or_garbage_reply_is_not_sent():
    assert _run("111", {"111": (6, "")})[0] is False
    assert _run("111", {"111": (0, "<html>oops</html>")})[0] is False


def test_nothing_is_sent_without_credentials():
    with patch.object(config, "TELEGRAM_BOT_TOKEN", ""), \
         patch("lib.notifications.subprocess.run") as run:
        assert notifications.send_telegram_notification("hello") is False
    run.assert_not_called()
