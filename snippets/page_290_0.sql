CREATE TABLE refund_receipt (
  merchant_id TEXT NOT NULL,
  payment_id TEXT NOT NULL,
  authorization_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  amount_cents BIGINT NOT NULL CHECK (amount_cents > 0),
  ledger_receipt_id TEXT NOT NULL,
  PRIMARY KEY (merchant_id, payment_id),
  UNIQUE (merchant_id, idempotency_key)
);

-- Insert must share the financial transaction or a verified ledger command.
-- A uniqueness constraint alone does not make an external credit atomic.