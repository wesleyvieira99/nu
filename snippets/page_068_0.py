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