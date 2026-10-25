# Confiança em escala · Trust at scale

Wesley Vieira · Engineering Manager / Staff Software Engineer

[Ler em português](https://wesleyvieira99.github.io/nu/) · [Read in English](https://wesleyvieira99.github.io/nu/en.html) · [PDF PT](docs/pdf/Nubank_Confianca_em_Escala_PT.pdf) · [PDF EN](docs/pdf/Nubank_Trust_at_Scale_EN.pdf)

![Reader preview](docs/preview.png)

408 páginas por idioma, 20 novos estudos de problemas públicos, 24 arquiteturas + 20 diagramas de sequência com marcas oficiais, 98 blocos de código, 20 simuladores, tags de padrões e 11 linguagens/formatos. Menu de capítulos no computador e celular; PDF com marcadores e cinco controles de navegação em cada página.

Os vinte casos anteriores foram substituídos. Esta edição parte de 18 reclamações no Reclame AQUI e 2 reportagens, com capturas reais, resposta da empresa e desfecho disponível. Cada estudo propõe uma solução específica, implementação, indicadores, cenários financeiros e roadmap com responsáveis e critérios de saída. Vídeos de reportagem e tutorial oficial são identificados como fontes com finalidades diferentes.

The twenty previous cases have been replaced by specific, evidence-led studies. All cases include source provenance, company replies, available outcomes, distinct engineering proposals, executable labs, metrics, financial scenarios and staged roadmaps. The publication is independent application material, without Nubank endorsement or access to its internal systems.

## Cases / Casos

| # | Português | English | Implementation |
| --- | --- | --- | --- |
| 01 | [Pix de R$ 300 falha; estorno e estado precisam ficar claros](cases/pt/case_01.md) | [A BRL 300 Pix fails: make the refund and state visible](cases/en/case_01.md) | [Python](labs/case_01.py) |
| 02 | [Pix recebido sem atualização do saldo: incidente de 8 de julho](cases/pt/case_02.md) | [Incoming Pix missing from the displayed balance: July 8 incident](cases/en/case_02.md) | [Python](labs/case_02.py) |
| 03 | [Mais de R$ 2 milhões retidos: revisão e saída de conta com evidência](cases/pt/case_03.md) | [More than BRL 2 million held: evidence-based review and account exit](cases/en/case_03.md) | [Python](labs/case_03.py) |
| 04 | [Câmera quebrada impede autorização facial: recuperação assistida](cases/pt/case_04.md) | [Broken camera blocks facial authorization: assisted recovery](cases/en/case_04.md) | [Python](labs/case_04.py) |
| 05 | [Telefone novo, e-mail antigo: código que não chega](cases/pt/case_05.md) | [New phone, old email: an authorization code that never arrives](cases/en/case_05.md) | [Python](labs/case_05.py) |
| 06 | [Contestação Airbnb em análise não permite anexar nova evidência](cases/pt/case_06.md) | [Airbnb dispute under review blocks additional evidence](cases/en/case_06.md) | [Python](labs/case_06.py) |
| 07 | [Três Pix somam R$ 478,55; cliente pede clareza sobre o MED](cases/pt/case_07.md) | [Three Pix transfers totaling BRL 478.55: make MED progress explicit](cases/en/case_07.md) | [Python](labs/case_07.py) |
| 08 | [Empréstimo contestado: evidência de acesso e decisão revisável](cases/pt/case_08.md) | [Disputed loan: access evidence and a reviewable decision](cases/en/case_08.md) | [Python](labs/case_08.py) |
| 09 | [Fatura paga, limite incerto: rastrear a alocação do pagamento](cases/pt/case_09.md) | [Paid statement, uncertain credit: trace payment allocation](cases/en/case_09.md) | [Python](labs/case_09.py) |
| 10 | [NuPay após erro exibido: repetição, duplicidade e juros](cases/pt/case_10.md) | [NuPay after an error message: retry, duplication and interest](cases/en/case_10.md) | [Python](labs/case_10.py) |
| 11 | [Estorno em três lançamentos: tornar a fatura explicável](cases/pt/case_11.md) | [A refund in three entries: make the statement explain itself](cases/en/case_11.md) | [Python](labs/case_11.py) |
| 12 | [Entregue no rastreio, ausente na mão: comprovar posse do cartão](cases/pt/case_12.md) | [Delivered in tracking, missing in hand: establish card possession](cases/en/case_12.md) | [Python](labs/case_12.py) |
| 13 | [Teto do cartão virtual não é crédito disponível](cases/pt/case_13.md) | [A virtual card cap is not available credit](cases/en/case_13.md) | [Python](labs/case_13.py) |
| 14 | [Antecipação paga fora da data: cotação, execução e desconto](cases/pt/case_14.md) | [An early repayment applied late: quote, execution and discount](cases/en/case_14.md) | [Python](labs/case_14.py) |
| 15 | [Caixinhas: resgate indisponível e estado de serviço invisível](cases/pt/case_15.md) | [Money Boxes: unavailable withdrawals and an invisible service state](cases/en/case_15.md) | [Python](labs/case_15.py) |
| 16 | [Portabilidade de investimentos: elegibilidade contraditória no cashback](cases/pt/case_16.md) | [Investment transfers: conflicting cashback eligibility answers](cases/en/case_16.md) | [Python](labs/case_16.py) |
| 17 | [Ultravioleta: um saldo, duas unidades, uma escolha irreversível](cases/pt/case_17.md) | [Ultravioleta: one balance, two units, one irreversible choice](cases/en/case_17.md) | [Python](labs/case_17.py) |
| 18 | [NuCel: portabilidade sem conclusão entre duas operadoras](cases/pt/case_18.md) | [NuCel: number portability stalled between two carriers](cases/en/case_18.md) | [Python](labs/case_18.py) |
| 19 | [Conta Global: validar o objetivo antes de converter](cases/pt/case_19.md) | [Global Account: validate the goal before exchanging currency](cases/en/case_19.md) | [Python](labs/case_19.py) |
| 20 | [NuPay: pagamento aprovado, pedido sem confirmação](cases/pt/case_20.md) | [NuPay: payment approved, order unconfirmed](cases/en/case_20.md) | [Python](labs/case_20.py) |

## Run / Executar

```bash
cd labs
python3 -m unittest discover -p "case_*.py" -v
clojure -M decision_core.clj
```

Local validation: **241 Python tests** and **11 Clojure tests / 22 assertions** passed. Labs use synthetic data and never access bank accounts. Integration snippets are not all executable applications; the book labels unexecuted examples and production gaps. Clojure is pinned in `deps.edn`; dependency resolution needs internet.

[GitHub Actions workflow](https://github.com/wesleyvieira99/nu/actions/workflows/labs.yml). Remote Actions validation has not completed; local validation records are in `validation/`. Pages publication is verified separately.

## Reproduce a financial scenario / Reproduzir um cenário

From the repository root / Da raiz do repositório:

```bash
python3 models/simulate.py 04 --scenario 1 --realization 50
```

`--scenario` selects 0 (conservative), 1 (base), or 2 (ambitious). `--realization` accepts 0–100 percent. The standard-library Decimal CLI reads `models/normalized-scenarios.json`, retains scenario costs and reproduces the reader's monthly, annual or six-month-cohort horizon. Capacity equivalent is not cash saved; all proposal returns remain hypothetical. Invalid, negative or non-finite inputs are rejected.

## Evidence and value / Evidência e valor

Public complaints establish reported experiences, not incidence, technical cause or a current generalized defect. Resolved outcomes and conflicting accounts are preserved. Screenshots are real cropped source captures. Official product photos and tutorials are context, not proof of an incident.

Financial outputs are **conditional scenarios**, with assumptions and sensitivity, not realized Nubank returns. Customer principal is not bank revenue; released capacity is not automatically cash savings. Do not sum overlapping cases. Public financial context, model inputs and calculation checks are in `models/` and `validation/`.

`labs/` executable models · `snippets/` literal book code · `cases/` full chapters · `manuscripts/` editable bilingual content · `evidence/` captures, logos and diagrams with provenance · `models/` financial assumptions · `sources.json` references · `checksums.json` file hashes.

Case research: 23 October 2026. LinkedIn, official media and method references checked on 25 October 2026. Brands and photographs belong to their respective owners. Official font sources and OFL licenses are in `fonts/`.

## Autor · Author

[Portfólio · Portfolio](https://wesleyvieira99.github.io/WVPortfolio/) · [LinkedIn](https://www.linkedin.com/in/techvieira/) · [GitHub](https://github.com/wesleyvieira99)
