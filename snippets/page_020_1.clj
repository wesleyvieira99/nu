;; Schema proposto para um exercício de domínio.
[{:db/ident :operation/id
  :db/valueType :db.type/uuid
  :db/cardinality :db.cardinality/one
  :db/unique :db.unique/identity}
 {:db/ident :operation/status
  :db/valueType :db.type/keyword
  :db/cardinality :db.cardinality/one}
 {:db/ident :operation/version
  :db/valueType :db.type/long
  :db/cardinality :db.cardinality/one}]

;; Uma transação propõe a mudança de versão e status.
;; entity-id e expected-version são obtidos pelo adapter.
[[:db/cas entity-id :operation/version
  expected-version (inc expected-version)]
 [:db/add entity-id :operation/status :operation/pending]]