(ns portfolio.delivery)

(def allowed-status
  #{:transit :exception :delivered})

(defn normalize-event [raw]
  (let [{:keys [event-id shipment-id sequence
                status next-step]} raw]
    (when-not (and (string? event-id)
                   (string? shipment-id)
                   (integer? sequence)
                   (pos? sequence)
                   (contains? allowed-status status)
                   (string? next-step))
      (throw (ex-info "Invalid partner contract"
                      {:kind :invalid-event})))
    {:event-id event-id
     :shipment-id shipment-id
     :sequence sequence
     :status status
     :next-step next-step}))

;; Autenticação ocorre antes desta função pura.
;; Persistência e confirmação ocorrem depois dela.