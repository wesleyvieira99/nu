"""Modelo local de conteúdo, privacidade tardia e deduplicação. Sem push real."""
import json
import unittest


class Notifications:
    def __init__(self):
        self.events, self.preferences, self.sent = {}, {}, {}

    def configure(self, user, show_values=False, enabled=True):
        if type(show_values) is not bool or type(enabled) is not bool:
            raise ValueError("boolean_preferences_required")
        old = self.preferences.get(user, {"version": 0})
        self.preferences[user] = dict(show_values=show_values, enabled=enabled,
                                      version=old["version"] + 1)

    def enqueue(self, event):
        if set(event) != {"id", "user", "version", "kind", "amount_cents"}:
            raise ValueError("schema")
        if (type(event["version"]) is not int or event["version"] != 1
                or event["kind"] not in ("cashback", "income")):
            raise ValueError("unsupported")
        cents = event["amount_cents"]
        if type(cents) is not int or cents < 0:
            raise ValueError("money")
        payload = json.dumps(event, sort_keys=True)
        old = self.events.get(event["id"])
        if old is not None and old != payload:
            raise ValueError("id_conflict")
        self.events[event["id"]] = payload

    def deliver(self, event_id):
        if event_id in self.sent:
            return self.sent[event_id]
        event = json.loads(self.events[event_id])
        pref = self.preferences.get(event["user"],
                                    dict(show_values=False, enabled=True, version=0))
        if not pref["enabled"]:
            return {"status": "suppressed"}
        # A política é aplicada agora, não no instante de enfileirar.
        message = {"title": "Atualização financeira",
                   "body": "Consulte os detalhes no aplicativo.",
                   "preference_version": pref["version"]}
        if pref["show_values"]:
            whole, cents = divmod(event["amount_cents"], 100)
            message["body"] = f"Crédito disponível: R$ {whole},{cents:02d}."
        # Aceitação local pelo provedor simulado, sem garantia de leitura.
        self.sent[event_id] = {"status": "accepted", "message": message}
        return self.sent[event_id]


class Tests(unittest.TestCase):
    def setUp(self):
        self.n = Notifications()
        self.event = dict(id="e1", user="u", version=1, kind="income",
                          amount_cents=12345)

    def test_default_hides_values(self):
        self.n.enqueue(self.event)
        result = self.n.deliver("e1")
        self.assertNotIn("123", str(result))
        self.assertNotIn("amount_cents", str(result))

    def test_explicit_opt_in_formats_integer_cents(self):
        self.n.configure("u", show_values=True)
        self.n.enqueue(self.event)
        self.assertIn("123,45", self.n.deliver("e1")["message"]["body"])

    def test_privacy_changed_while_queued_is_respected(self):
        self.n.configure("u", show_values=True)
        self.n.enqueue(self.event)
        self.n.configure("u", show_values=False)
        self.assertNotIn("123", str(self.n.deliver("e1")))

    def test_opt_out_suppresses_delivery(self):
        self.n.enqueue(self.event)
        self.n.configure("u", enabled=False)
        self.assertEqual(self.n.deliver("e1"), {"status": "suppressed"})
        self.assertEqual(len(self.n.sent), 0)

    def test_replay_is_identical(self):
        self.n.enqueue(self.event)
        first = self.n.deliver("e1")
        self.n.enqueue(self.event)
        self.assertEqual(self.n.deliver("e1"), first)
        self.assertEqual(len(self.n.sent), 1)

    def test_payload_conflict_is_rejected(self):
        self.n.enqueue(self.event)
        with self.assertRaises(ValueError):
            self.n.enqueue(dict(self.event, amount_cents=999))

    def test_unsupported_schema_and_float_are_rejected(self):
        for change in ({"version": 2}, {"amount_cents": 12.3}, {"kind": "other"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.n.enqueue(dict(self.event, **change))

    def test_preferences_and_version_have_strict_types(self):
        for change in ({"show_values": "false"}, {"show_values": 1},
                       {"enabled": "false"}, {"enabled": None}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.n.configure("u", **change)
        self.assertNotIn("u", self.n.preferences)
        for version in (True, 1.0):
            with self.subTest(version=version), self.assertRaises(ValueError):
                self.n.enqueue(dict(self.event, version=version))


if __name__ == "__main__":
    print("LAB SINTÉTICO 03: fila e provedor em memória; não envia mensagens.")
    unittest.main(verbosity=2)
