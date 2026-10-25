(defn accept-delivery [state event]
  (cond
    (not= (:generation state) (:generation event))
    (assoc state :last-event-result :old-generation)

    (= :delivered (:type event))
    (assoc state :carrier-state :delivered)

    (= :customer-dispute (:type event))
    (assoc state :disputed? true :active? false)

    :else state))
;; Carrier delivery does not clear :disputed? or set :active?.