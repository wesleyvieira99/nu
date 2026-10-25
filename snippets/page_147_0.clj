(defn allocation-valid? [{:keys [received allocations unapplied]}]
  (and (pos-int? received)
       (every? pos-int? (vals allocations))
       (<= 0 unapplied)
       (= received (+ unapplied (reduce + (vals allocations))))))

(defn allocation-event [payment-id revision plan]
  {:event-type :payment-applied
   :payment-id payment-id
   :revision revision
   :allocations plan})