(defn payment-decision [account previous command]
  ;; Contrato proposto; não é código interno do Nubank.
  (let [{:keys [epoch balance-cents]} account
        {:keys [session-epoch payload]} command
        amount (:amount-cents payload)]
    (cond
      (not= epoch session-epoch)
      {:type :reject :reason :stale-session}

      (and previous (not= payload (:payload previous)))
      {:type :reject :reason :idempotency-conflict}

      previous
      {:type :replay :receipt (:receipt previous)}

      (or (not (integer? amount)) (not (pos? amount)))
      {:type :reject :reason :invalid-amount}

      (< balance-cents amount)
      {:type :reject :reason :insufficient-funds}

      :else
      {:type :commit
       :new-balance (- balance-cents amount)
       :payload payload})))