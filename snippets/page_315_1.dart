class RedemptionPreview {
  final int pointsConsumedMinor;
  final int cashReceivedCents;
  final int pointsRemainingMinor;
  final String quoteId;
  final DateTime expiresAt;
  const RedemptionPreview(this.pointsConsumedMinor,
      this.cashReceivedCents, this.pointsRemainingMinor,
      this.quoteId, this.expiresAt);
}

String consequenceLabel(RedemptionPreview preview) =>
    "This choice consumes the same benefit balance. "
    "Review the amount and remaining points before confirming.";