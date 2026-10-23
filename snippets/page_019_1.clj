(defn register [db {:keys [key amount currency] :as cmd}]
  (when-not (valid-command? cmd)
    (throw (ex-info "invalid command"
                    {:reason :invalid-command})))
  (let [fingerprint [amount currency]
        existing (get db key)]
    (cond
      (nil? existing)
      (assoc db key {:fingerprint fingerprint
                     :status :received :version 0})
      (= fingerprint (:fingerprint existing)) db
      :else
      (throw (ex-info "key reused with different payload"
                      {:reason :key-conflict})))))

;; Em um único processo: atualização atômica do modelo.
;; Nunca adicionar efeitos externos à função de swap!.
(def state (atom {}))
(swap! state register
       {:key "synthetic-001" :amount 1250 :currency :BRL})