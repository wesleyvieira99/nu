(ns portfolio.conditions)

(def required-components #{:balance :limit})

(defn fresh? [now max-age parts]
  (and
    (every? #(contains? parts %) required-components)
    (every?
      (fn [{:keys [observed-at]}]
        (<= 0 (- now observed-at) max-age))
      (vals parts))))

(defn read-conditions
  [projection now max-age canonical-reader]
  (if (fresh? now max-age projection)
    {:source :projection
     :purpose :display-conditions
     :data projection}
    {:source :canonical
     :purpose :display-conditions
     :data (canonical-reader)}))

;; canonical-reader é contrato proposto, não API do Nu.
;; Autorizar pagamento pertence a outra fronteira.