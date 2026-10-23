(defn restore-tx [case-id expected-version now decision]
  ;; Esboço proposto de dados transacionais.
  ;; O chamador autenticado precisa validar a autorização.
  (when-not (= :verified (:state decision))
    (throw (ex-info "case-not-verified" {})))
  (when (>= now (:expires-at decision))
    (throw (ex-info "decision-expired" {})))
  (let [new-version (inc expected-version)
        identity-id (:identity-id decision)
        old-epoch (:recovery-epoch decision)]
    [[:db/cas case-id
      :recovery/version expected-version new-version]
     [:db/cas case-id
      :recovery/state :verified :restored]
     [:db/cas identity-id
      :identity/recovery-epoch old-epoch (inc old-epoch)]
     {:db/id "audit-event"
      :audit/kind :recovery-restored
      :audit/case case-id
      :audit/decision-id (:decision-id decision)
      :audit/actor-id (:actor-id decision)
      :audit/at now}]))