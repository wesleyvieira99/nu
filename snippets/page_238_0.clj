(ns independent.support-policy)

(defn choose-route
  [{:keys [urgent? available candidates min-support]}]
  (let [ordered (sort-by (juxt (comp - :weight) :intent)
                         candidates)
        total (reduce + (map :weight ordered))
        best (first ordered)
        share (if (pos? total)
                (/ (:weight best 0) total)
                0)]
    (cond
      urgent?
      {:queue :human-urgent :reason :declared-urgency}

      (< total min-support)
      {:queue :human-general :reason :insufficient}

      (or (< share 3/4)
          (not (contains? available (:intent best))))
      {:queue :human-general :reason :abstention}

      :else
      {:queue (:intent best)
       :reason :ranked
       :share share})))

;; O adaptador persiste e encaminha fora desta função.
;; Contrato proposto: candidate weights >= 0.
;; Empates recebem ordem determinística, não mais confiança.