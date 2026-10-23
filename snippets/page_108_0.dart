enum ContextReason {
  verified, permissionMissing, unavailable, expired,
}

class ContextMessage {
  final String title, body;
  final bool offerSettings;
  const ContextMessage(this.title, this.body, this.offerSettings);
}

ContextMessage explain(ContextReason reason) {
  // Texto proposto: não informa critérios internos de risco.
  switch (reason) {
    case ContextReason.verified:
      return const ContextMessage('Contexto confirmado',
          'Outras verificações de segurança continuam valendo.', false);
    case ContextReason.permissionMissing:
      return const ContextMessage('Proteção mantida',
          'Não foi possível confirmar o contexto sem a permissão.', true);
    case ContextReason.unavailable:
      return const ContextMessage('Proteção mantida',
          'O contexto não está disponível neste momento.', false);
    case ContextReason.expired:
      return const ContextMessage('Precisamos verificar novamente',
          'A confirmação anterior perdeu a validade.', false);
  }
}