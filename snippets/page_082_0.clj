(defn usable? [now max-age resource]
  (and (= :complete (:status resource))
       (integer? (:cents resource))
       (<= 0 (- now (:observed-at resource)) max-age)))

(defn aggregate [expected resources now max-age]
  ;; Contrato proposto: total conhecido sempre vem com cobertura.
  (reduce
    (fn [acc key]
      (let [resource (get resources key)]
        (if (usable? now max-age resource)
          (update acc :known-cents + (:cents resource))
          (assoc-in acc [:gaps key]
            (cond
              (nil? resource) :missing
              (not= :complete (:status resource))
              (:status resource)
              :else :stale-or-future)))))
    {:known-cents 0 :gaps {}}
    expected))

(defn presentation [result]
  (assoc result :label
    (if (empty? (:gaps result))
      :covered-total :known-subtotal)))