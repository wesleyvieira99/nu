(defn explain-installment [{:keys [eligible due paid today]}]
  (cond
    paid {:state :paid :next-action :view-receipt}
    (not eligible) {:state :review :next-action :view-reasons}
    (.isBefore today due)
    {:state :scheduled :next-action :view-calendar :due due}
    :else {:state :due :next-action :track-payment}))

;; Inputs come from authorized, versioned domain services.
;; This function explains; it never posts a financial credit.