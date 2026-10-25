sealed class PaymentState {}
class Unknown extends PaymentState {
  final String intentId;
  Unknown(this.intentId);
}
class Confirmed extends PaymentState {
  final String receiptId;
  Confirmed(this.receiptId);
}

String nextAction(PaymentState state) => switch (state) {
  Unknown() => 'Check the existing payment',
  Confirmed() => 'Open receipt',
  _ => 'Continue',
};