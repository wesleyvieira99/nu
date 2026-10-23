-- Esquema proposto; não executado pelo laboratório.
CREATE TABLE purchase_records (
  document_id TEXT PRIMARY KEY,
  purchase_id TEXT NOT NULL,
  purchase_revision BIGINT NOT NULL,
  template_revision INTEGER NOT NULL,
  document_kind TEXT NOT NULL,
  state_at_issue TEXT NOT NULL,
  payload_digest TEXT NOT NULL,
  storage_reference TEXT NOT NULL,
  issued_at TIMESTAMP NOT NULL,
  owner_reference TEXT NOT NULL,
  UNIQUE (purchase_id, purchase_revision,
          template_revision, document_kind),
  CHECK (purchase_revision > 0),
  CHECK (template_revision > 0)
);

CREATE INDEX records_by_purchase
  ON purchase_records (purchase_id, purchase_revision);

-- Acesso ao blob ainda exige autorização.
-- Digest não torna o arquivo anônimo ou público.