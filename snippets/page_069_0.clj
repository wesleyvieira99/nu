(def templates
  {:income {:title "Atualização financeira"
            :private-body "Consulte os detalhes no aplicativo."}
   :cashback {:title "Cashback disponível"
              :private-body "Veja a atualização no aplicativo."}})

(defn cents-label [cents]
  (str "R$ " (quot cents 100) ","
       (format "%02d" (mod cents 100))))

(defn render-message [event preference]
  ;; Catálogo e contrato propostos; sem envio neste exemplo.
  (when-not (= 1 (:schema-version event))
    (throw (ex-info "unsupported-schema" {})))
  (when-not (true? (:enabled? preference))
    (throw (ex-info "communication-suppressed" {})))
  (let [template (get templates (:kind event))
        amount (:amount-cents event)]
    (when-not (and template (integer? amount) (<= 0 amount))
      (throw (ex-info "invalid-event" {})))
    {:title (:title template)
     :body (if (true? (:show-values? preference))
             (str "Crédito disponível: " (cents-label amount))
             (:private-body template))
     :policy-version (:version preference)}))