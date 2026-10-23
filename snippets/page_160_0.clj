(ns portfolio.purchase-record)

(def labels
  {:pending "Autorização pendente"
   :confirmed "Registro de compra confirmada"
   :reversed "Compra estornada"})

(defn public-record [purchase subject]
  (when-not (= subject (:owner purchase))
    (throw (ex-info "Forbidden" {:kind :forbidden})))
  (let [status (:status purchase)
        label (get labels status)]
    (when-not label
      (throw (ex-info "Unsupported state"
                      {:kind :invalid-state})))
    (assoc
      (select-keys purchase
        [:purchase-id :revision :amount-cents
         :merchant :status])
      :label label
      :kind :purchase-record
      :notice "Não comprova quitação da fatura")))

;; Proposta pura: autenticação e assinatura são externas.