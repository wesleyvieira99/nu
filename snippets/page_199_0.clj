(ns portfolio.resource-transfer)

(defn transfer-tx
  [resource-eid expected-revision new-owner accepting-team]
  (when-not (= new-owner accepting-team)
    (throw (ex-info "Destination must accept"
                    {:kind :missing-acceptance})))
  (when-not (and (integer? expected-revision)
                (pos? expected-revision))
    (throw (ex-info "Invalid revision"
                    {:kind :invalid-revision})))
  [[:db/cas resource-eid :resource/revision
     expected-revision (inc expected-revision)]
   [:db/add resource-eid :resource/owner new-owner]])

;; Proposta: :resource/revision é cardinalidade one.
;; Os atributos devem existir em um schema revisado.
;; Submeter o vetor em UMA transação Datomic.
;; Aceite deve vir de identidade autenticada.
;; A checagem local não substitui autorização.
;; Restrições adicionais pertencem à mesma decisão.
;; O trecho constrói dados; não conecta a uma base.