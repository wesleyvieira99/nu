(require '[clojure.string :as str])

(defn money-text [cents]
  ;; Valor inteiro e unidade definidos pelo contrato proposto.
  (when-not (integer? cents)
    (throw (ex-info "integer-cents-required" {})))
  (let [value (bigint cents)
        negative? (neg? value)
        magnitude (if negative? (- value) value)
        units (quot magnitude 100)
        fraction (long (rem magnitude 100))]
    (str (when negative? "-")
         units "." (format "%02d" fraction))))

(defn parse-money [text]
  (when-not (re-matches #"-?(0|[1-9][0-9]*)\.[0-9]{2}" text)
    (throw (ex-info "invalid-decimal-format" {})))
  (let [negative? (.startsWith text "-")
        unsigned (if negative? (subs text 1) text)
        [units fraction] (str/split unsigned #"\.")
        cents (+ (* (bigint units) 100) (bigint fraction))]
    (if negative? (- cents) cents)))

;; Propriedade pretendida, a verificar no runtime de destino:
;; (= x (parse-money (money-text x)))
;; Nenhuma etapa exige conversão para Double.