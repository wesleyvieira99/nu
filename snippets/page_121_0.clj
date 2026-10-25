(defn recovery-event [current event]
  ;; Proposed local rule, not a DICT payload specification.
  (let [amount (:cents event)
        remaining (- (:claimed current) (:recovered current))]
    (cond
      (not (true? (:verified event))) {:error :untrusted}
      (not (integer? amount)) {:error :invalid-money}
      (not (<= 1 amount remaining)) {:error :amount-out-of-range}
      (not= (:sequence event) (inc (:sequence current)))
      {:error :sequence-gap}
      :else {:next-recovered (+ (:recovered current) amount)
             :next-sequence (:sequence event)})))