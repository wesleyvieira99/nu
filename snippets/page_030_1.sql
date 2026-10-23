CREATE TABLE proposed_operation (
  operation_id UUID PRIMARY KEY,
  customer_scope TEXT NOT NULL,
  request_key TEXT NOT NULL,
  amount_minor BIGINT NOT NULL CHECK (amount_minor > 0),
  currency CHAR(3) NOT NULL CHECK (currency = 'BRL'),
  version BIGINT NOT NULL DEFAULT 0 CHECK (version >= 0),
  status TEXT NOT NULL CHECK (
    status IN ('received','pending','settled','rejected')
  ),
  UNIQUE (customer_scope, request_key)
);

UPDATE proposed_operation
SET status = 'pending', version = version + 1
WHERE operation_id = $1
  AND version = $2
  AND status = 'received'
RETURNING operation_id, version, status;