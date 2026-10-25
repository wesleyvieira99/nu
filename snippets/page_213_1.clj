(defn explain-statement [entries]
  (let [sum-kind (fn [kind]
                   (reduce + (map :cents
                     (filter #(= kind (:kind %)) entries))))
        purchases (sum-kind :purchase)
        refunds (sum-kind :refund)
        payments (sum-kind :payment)
        signed (- purchases refunds payments)]
    {:purchases purchases
     :refunds refunds
     :payments payments
     :amount-due (max 0 signed)
     :credit-balance (max 0 (- signed))}))