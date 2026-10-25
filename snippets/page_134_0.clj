(defn reviewable? [{:keys [evidence decision policy]}]
  (and (seq evidence)
       (string? policy)
       (every? #(contains? % :source-ref) evidence)
       (not= :device-access-only decision)))

(defn appeal-command [case-id revision reviewer]
  {:case-id case-id
   :expected-revision revision
   :action :independent-review
   :reviewer reviewer})