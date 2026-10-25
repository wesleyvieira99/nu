# Dentro da pasta labs do pacote extraído:
python3 case_01.py
python3 case_17.py

# Todos os casos em uma única execução:
python3 -m unittest discover -p "case_*.py" -v

# Núcleo Clojure, com Clojure 1.12.0 instalado:
clojure -M decision_core.clj