(def transitions
  {:received #{:pending :rejected}
   :pending #{:settled :rejected}
   :settled #{}
   :rejected #{}})

(defn advance [db key expected-version next-status]
  (let [{:keys [status version] :as current} (get db key)]
    (when-not current
      (throw (ex-info "unknown operation" {:reason :not-found})))
    (when-not (= expected-version version)
      (throw (ex-info "stale writer" {:reason :version-conflict})))
    (when-not (contains? (get transitions status #{}) next-status)
      (throw (ex-info "illegal transition"
                      {:reason :illegal-transition})))
    (assoc db key (assoc current :status next-status
                         :version (inc version)))))