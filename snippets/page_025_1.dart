sealed class ReceiptState {
  const ReceiptState();
}
final class AwaitingConfirmation extends ReceiptState {
  const AwaitingConfirmation(this.operationId);
  final String operationId;
}
final class Confirmed extends ReceiptState {
  const Confirmed(this.operationId, this.receiptId);
  final String operationId;
  final String receiptId;
}
final class Unavailable extends ReceiptState {
  const Unavailable(this.operationId);
  final String operationId;
}

String actionLabel(ReceiptState state) => switch (state) {
  AwaitingConfirmation() => 'Consultar andamento',
  Confirmed() => 'Abrir comprovante',
  Unavailable() => 'Tentar consultar novamente',
};