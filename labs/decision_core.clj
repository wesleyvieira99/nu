(ns decision-core
  (:require [clojure.test :refer [deftest is testing run-tests]]))

;; Synthetic, in-memory state machine. No network or banking integration.
(def terminal #{:settled :rejected})
(def transitions
  {:received #{:pending :rejected}
   :pending #{:settled :rejected}
   :settled #{}
   :rejected #{}})

(defn valid-command? [{:keys [key amount currency]}]
  (and (string? key) (not (empty? key))
       (integer? amount) (pos? amount)
       (= :BRL currency)))

(defn register [db {:keys [key amount currency] :as cmd}]
  (when-not (valid-command? cmd)
    (throw (ex-info "invalid command" {:reason :invalid-command})))
  (let [fingerprint [amount currency]
        existing (get db key)]
    (cond
      (nil? existing)
      (assoc db key {:fingerprint fingerprint
                     :status :received :version 0})
      (= fingerprint (:fingerprint existing)) db
      :else (throw (ex-info "key reused with different payload"
                            {:reason :key-conflict})))))

(defn advance [db key expected-version next-status]
  (let [{:keys [status version] :as current} (get db key)]
    (when-not current
      (throw (ex-info "unknown operation" {:reason :not-found})))
    (when-not (= expected-version version)
      (throw (ex-info "stale writer" {:reason :version-conflict})))
    (when-not (contains? (get transitions status #{}) next-status)
      (throw (ex-info "illegal transition" {:reason :illegal-transition})))
    (assoc db key (assoc current :status next-status
                         :version (inc version)))))

(defn visible-state [{:keys [status]}]
  (case status
    :settled {:label "Concluido" :retry? false}
    :rejected {:label "Nao concluido" :retry? false}
    :pending {:label "Em confirmacao" :retry? false}
    :received {:label "Recebido" :retry? false}
    {:label "Consulte o historico" :retry? false}))

(def command {:key "synthetic-001" :amount 1250 :currency :BRL})
(defn reason [f]
  (try (f) nil
       (catch clojure.lang.ExceptionInfo e (:reason (ex-data e)))))

(deftest registration
  (is (= :received (get-in (register {} command)
                          ["synthetic-001" :status])))
  (is (= 0 (get-in (register {} command)
                   ["synthetic-001" :version]))))
(deftest retry-does-not-create-another-operation
  (let [db (register {} command)]
    (is (= db (register db command)))
    (is (= 1 (count (register db command))))))
(deftest changed-payload-is-rejected
  (let [db (register {} command)]
    (is (= :key-conflict
           (reason #(register db (assoc command :amount 1300)))))))
(deftest malformed-money-is-rejected
  (doseq [amount [0 -1 1.2 nil]]
    (is (= :invalid-command
           (reason #(register {} (assoc command :amount amount)))))))
(deftest wrong-currency-is-rejected
  (is (= :invalid-command
         (reason #(register {} (assoc command :currency :USD))))))
(deftest legal-state-path
  (let [db (-> {} (register command)
               (advance "synthetic-001" 0 :pending)
               (advance "synthetic-001" 1 :settled))]
    (is (= :settled (get-in db ["synthetic-001" :status])))
    (is (= 2 (get-in db ["synthetic-001" :version])))))
(deftest stale-writer-cannot-revert
  (let [db (-> {} (register command)
               (advance "synthetic-001" 0 :pending))]
    (is (= :version-conflict
           (reason #(advance db "synthetic-001" 0 :rejected))))))
(deftest terminal-state-is-immutable
  (let [db (-> {} (register command)
               (advance "synthetic-001" 0 :pending)
               (advance "synthetic-001" 1 :settled))]
    (doseq [s [:received :pending :rejected]]
      (is (= :illegal-transition
             (reason #(advance db "synthetic-001" 2 s)))))))
(deftest unknown-operation-is-rejected
  (is (= :not-found (reason #(advance {} "missing" 0 :pending)))))
(deftest concurrent-identical-registration
  (let [db (atom {})
        workers (doall (repeatedly 80 #(future (swap! db register command))))]
    (doseq [worker workers] @worker)
    (is (= 1 (count @db)))
    (is (= 0 (get-in @db ["synthetic-001" :version])))))
(deftest unknown-status-never-encourages-retry
  (is (false? (:retry? (visible-state {:status :unknown}))))
  (is (false? (:retry? (visible-state {:status :pending}))))
  (is (= "Concluido" (:label (visible-state {:status :settled})))) )

(let [{:keys [fail error]} (run-tests 'decision-core)]
  (shutdown-agents)
  (System/exit (if (zero? (+ fail error)) 0 1)))
