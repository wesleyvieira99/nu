#!/usr/bin/env python3
"""Laboratório SINTÉTICO de confiança transacional — somente Python stdlib.

Não implementa, reproduz nem descreve sistemas do Nubank. Não movimenta dinheiro.
Execute: python3 lab_confianca.py

Modelo: um pagamento debita uma conta local e grava recibo + lançamento na mesma
transação SQLite. O favorecido é um rótulo; não existe liquidação externa.
Os testes usam bancos temporários e incluem encerramento abrupto de subprocessos.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
import uuid


MAX_CENTS = 2**63 - 1


class PaymentError(Exception):
    """Base para erros de domínio deste exemplo."""


class IdempotencyConflict(PaymentError):
    pass


class InsufficientFunds(PaymentError):
    pass


class StaleSession(PaymentError):
    pass


class UnknownAccount(PaymentError):
    pass


class AmbiguousPaymentResult(TimeoutError):
    """O commit ocorreu, mas a resposta simulada não chegou ao cliente."""


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_cents(value: int, *, allow_zero: bool = False) -> None:
    minimum = 0 if allow_zero else 1
    if type(value) is not int or not minimum <= value <= MAX_CENTS:
        raise ValueError("Valor deve ser um inteiro em centavos dentro do intervalo suportado")


class SyntheticPayments:
    """Armazenamento local; account_id/epoch são entradas de teste, não autenticação."""

    def __init__(self, database: str | Path):
        self.database = str(database)
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    initial_cents INTEGER NOT NULL
                        CHECK(typeof(initial_cents) = 'integer' AND initial_cents >= 0),
                    balance_cents INTEGER NOT NULL
                        CHECK(typeof(balance_cents) = 'integer' AND balance_cents >= 0),
                    recovery_epoch INTEGER NOT NULL DEFAULT 0
                        CHECK(typeof(recovery_epoch) = 'integer' AND recovery_epoch >= 0)
                );
                CREATE TABLE IF NOT EXISTS payments (
                    operation_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL REFERENCES accounts(account_id),
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL
                        CHECK(typeof(amount_cents) = 'integer' AND amount_cents > 0),
                    receipt_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ledger (
                    entry_id INTEGER PRIMARY KEY,
                    operation_id TEXT NOT NULL UNIQUE REFERENCES payments(operation_id),
                    account_id TEXT NOT NULL REFERENCES accounts(account_id),
                    debit_cents INTEGER NOT NULL
                        CHECK(typeof(debit_cents) = 'integer' AND debit_cents > 0)
                );
            """)

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self.database, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("PRAGMA synchronous=FULL")
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _write(self):
        # BEGIN IMMEDIATE serializa a decisão de saldo/epoch com os demais writes.
        # É uma escolha didática local; não é uma estratégia distribuída de escala.
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except BaseException:
                if connection.in_transaction:
                    connection.rollback()
                raise

    def create_account(self, account_id: str, initial_cents: int) -> None:
        validate_cents(initial_cents, allow_zero=True)
        if not isinstance(account_id, str) or not account_id.strip():
            raise ValueError("Conta de teste deve ter identificador")
        with self._write() as connection:
            connection.execute(
                "INSERT INTO accounts(account_id, initial_cents, balance_cents) VALUES (?, ?, ?)",
                (account_id, initial_cents, initial_cents),
            )

    def recover_session(self, account_id: str) -> int:
        """Incrementa a barreira de sessão; não desfaz pagamentos já confirmados."""
        with self._write() as connection:
            row = connection.execute(
                "SELECT recovery_epoch FROM accounts WHERE account_id=?", (account_id,)
            ).fetchone()
            if row is None:
                raise UnknownAccount(account_id)
            new_epoch = row["recovery_epoch"] + 1
            connection.execute(
                "UPDATE accounts SET recovery_epoch=? WHERE account_id=?", (new_epoch, account_id)
            )
            return new_epoch

    def pay(
        self, *, account_id: str, operation_id: str, amount_cents: int,
        payee: str, recovery_epoch: int, fault: str | None = None,
    ) -> dict:
        validate_cents(amount_cents)
        if not isinstance(operation_id, str) or not 1 <= len(operation_id) <= 128:
            raise ValueError("operation_id deve ter entre 1 e 128 caracteres")
        if not isinstance(payee, str) or not payee.strip() or len(payee) > 200:
            raise ValueError("Favorecido de teste inválido")
        if type(recovery_epoch) is not int or recovery_epoch < 0:
            raise ValueError("recovery_epoch deve ser inteiro não negativo")
        if fault not in (None, "timeout_after_commit", "crash_before_commit", "crash_after_commit"):
            raise ValueError("Injeção de falha desconhecida")
        payload = canonical_json({
            "account_id": account_id, "amount_cents": amount_cents, "payee": payee,
        })
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        with self._write() as connection:
            account = connection.execute(
                "SELECT balance_cents, recovery_epoch FROM accounts WHERE account_id=?", (account_id,)
            ).fetchone()
            if account is None:
                raise UnknownAccount(account_id)
            # A sessão é validada antes inclusive de retornar um recibo já existente.
            if recovery_epoch != account["recovery_epoch"]:
                raise StaleSession("Comando de sessão anterior à recuperação")
            previous = connection.execute(
                "SELECT payload_json, payload_hash, receipt_json FROM payments WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
            if previous is not None:
                # Compara também o conteúdo canônico, sem depender apenas do hash.
                if previous["payload_hash"] != digest or previous["payload_json"] != payload:
                    raise IdempotencyConflict("operation_id reutilizado com outro payload")
                return json.loads(previous["receipt_json"])
            if account["balance_cents"] < amount_cents:
                raise InsufficientFunds("Saldo insuficiente no cenário sintético")

            remaining = account["balance_cents"] - amount_cents
            receipt = {
                "receipt_id": str(uuid.uuid4()), "operation_id": operation_id,
                "account_id": account_id, "payee": payee, "amount_cents": amount_cents,
                "balance_after_cents": remaining, "status": "committed",
                "environment": "synthetic-local-lab",
            }
            connection.execute(
                "UPDATE accounts SET balance_cents=? WHERE account_id=?", (remaining, account_id)
            )
            connection.execute(
                "INSERT INTO payments VALUES (?, ?, ?, ?, ?, ?)",
                (operation_id, account_id, payload, digest, amount_cents, canonical_json(receipt)),
            )
            connection.execute(
                "INSERT INTO ledger(operation_id, account_id, debit_cents) VALUES (?, ?, ?)",
                (operation_id, account_id, amount_cents),
            )
            if fault == "crash_before_commit":
                os._exit(72)  # Somente subprocesso descartável dos testes.

        if fault == "timeout_after_commit":
            raise AmbiguousPaymentResult("Resposta perdida após commit persistido")
        if fault == "crash_after_commit":
            os._exit(73)
        return receipt

    def inspect(self, account_id: str) -> dict:
        """Inspeção didática de um snapshot consistente, usada pelos testes."""
        with self._connection() as connection:
            connection.execute("BEGIN")
            account = connection.execute(
                "SELECT * FROM accounts WHERE account_id=?", (account_id,)
            ).fetchone()
            if account is None:
                raise UnknownAccount(account_id)
            payments = [dict(row) for row in connection.execute(
                "SELECT * FROM payments WHERE account_id=? ORDER BY operation_id", (account_id,)
            )]
            ledger = [dict(row) for row in connection.execute(
                "SELECT * FROM ledger WHERE account_id=? ORDER BY operation_id", (account_id,)
            )]
            result = dict(account)
            result.update(payments=payments, ledger=ledger)
            connection.commit()
            return result


class TrustInvariantTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-payment-lab-")
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "ledger.sqlite"
        self.bank = SyntheticPayments(self.database)
        self.bank.create_account("alice", 1000)

    def command(self, **changes):
        result = dict(account_id="alice", operation_id="op-1", amount_cents=700,
                      payee="loja-demo", recovery_epoch=0)
        result.update(changes)
        return result

    def assert_invariants(self, balance: int, payments: int):
        state = self.bank.inspect("alice")
        self.assertEqual(state["balance_cents"], balance)
        self.assertGreaterEqual(state["balance_cents"], 0)
        self.assertEqual(len(state["payments"]), payments)
        self.assertEqual(len(state["ledger"]), payments)
        self.assertEqual(
            state["initial_cents"], state["balance_cents"] + sum(row["debit_cents"] for row in state["ledger"])
        )
        payment_by_id = {row["operation_id"]: row for row in state["payments"]}
        self.assertEqual(len(payment_by_id), payments)
        for entry in state["ledger"]:
            payment = payment_by_id[entry["operation_id"]]
            receipt = json.loads(payment["receipt_json"])
            self.assertEqual(entry["debit_cents"], payment["amount_cents"])
            self.assertEqual(entry["debit_cents"], receipt["amount_cents"])
            self.assertEqual(entry["account_id"], receipt["account_id"])
            self.assertEqual(entry["operation_id"], receipt["operation_id"])

    def test_same_id_same_payload_returns_identical_persisted_receipt(self):
        first = self.bank.pay(**self.command())
        reopened = SyntheticPayments(self.database)
        for _ in range(8):
            self.assertEqual(reopened.pay(**self.command()), first)
        self.assert_invariants(balance=300, payments=1)

    def test_same_id_different_payload_conflicts_without_mutation(self):
        self.bank.pay(**self.command())
        original = self.bank.inspect("alice")
        for change in ({"amount_cents": 100}, {"payee": "outra-loja"}):
            with self.subTest(change=change), self.assertRaises(IdempotencyConflict):
                self.bank.pay(**self.command(**change))
        self.assertEqual(self.bank.inspect("alice"), original)
        self.assert_invariants(balance=300, payments=1)

    def test_timeout_after_commit_retry_does_not_debit_twice(self):
        with self.assertRaises(AmbiguousPaymentResult):
            self.bank.pay(**self.command(fault="timeout_after_commit"))
        stored = json.loads(self.bank.inspect("alice")["payments"][0]["receipt_json"])
        self.assertEqual(self.bank.pay(**self.command()), stored)
        self.assert_invariants(balance=300, payments=1)

    def test_insufficient_funds_has_no_partial_side_effects(self):
        with self.assertRaises(InsufficientFunds):
            self.bank.pay(**self.command(amount_cents=1001))
        self.assert_invariants(balance=1000, payments=0)

    def test_concurrent_distinct_payments_cannot_overdraw(self):
        barrier = threading.Barrier(2)
        def attempt(operation_id):
            barrier.wait(timeout=10)
            try:
                return self.bank.pay(**self.command(operation_id=operation_id))
            except InsufficientFunds:
                return "insufficient"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, ("parallel-a", "parallel-b")))
        self.assertEqual(sum(isinstance(value, dict) for value in results), 1)
        self.assertEqual(results.count("insufficient"), 1)
        self.assert_invariants(balance=300, payments=1)

    def test_concurrent_same_operation_has_one_receipt_and_one_debit(self):
        barrier = threading.Barrier(8)
        def retry(_):
            barrier.wait(timeout=10)
            return self.bank.pay(**self.command())
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(retry, range(8)))
        self.assertTrue(all(receipt == results[0] for receipt in results))
        self.assert_invariants(balance=300, payments=1)

    def test_recovery_epoch_rejects_old_commands_and_accepts_new_session(self):
        self.assertEqual(self.bank.recover_session("alice"), 1)
        reopened = SyntheticPayments(self.database)
        with self.assertRaises(StaleSession):
            reopened.pay(**self.command())
        self.assert_invariants(balance=1000, payments=0)
        receipt = reopened.pay(**self.command(recovery_epoch=1))
        with self.assertRaises(StaleSession):
            reopened.pay(**self.command())
        self.assertEqual(reopened.pay(**self.command(recovery_epoch=1)), receipt)
        self.assert_invariants(balance=300, payments=1)

    def test_recovery_does_not_reexecute_a_previously_committed_operation(self):
        first = self.bank.pay(**self.command())
        epoch = self.bank.recover_session("alice")
        self.assertEqual(self.bank.pay(**self.command(recovery_epoch=epoch)), first)
        self.assert_invariants(balance=300, payments=1)

    def test_integer_cents_rejects_float_bool_zero_negative_and_overflow(self):
        for invalid in (0.01, 700.0, True, 0, -1, MAX_CENTS + 1, "700"):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                self.bank.pay(**self.command(amount_cents=invalid))
        self.assert_invariants(balance=1000, payments=0)

    def run_crash_worker(self, fault: str, expected_exit: int):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--crash-worker", str(self.database), fault],
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, expected_exit, result.stderr)
        self.bank = SyntheticPayments(self.database)

    def test_process_crash_before_commit_rolls_back_and_resume_executes_once(self):
        self.run_crash_worker("crash_before_commit", 72)
        self.assert_invariants(balance=1000, payments=0)
        receipt = self.bank.pay(**self.command())
        self.assertEqual(self.bank.pay(**self.command()), receipt)
        self.assert_invariants(balance=300, payments=1)

    def test_process_crash_after_commit_preserves_receipt_and_resume_replays(self):
        self.run_crash_worker("crash_after_commit", 73)
        self.assert_invariants(balance=300, payments=1)
        stored = json.loads(self.bank.inspect("alice")["payments"][0]["receipt_json"])
        self.assertEqual(self.bank.pay(**self.command()), stored)
        self.assert_invariants(balance=300, payments=1)

    def test_unknown_account_has_no_effect(self):
        with self.assertRaises(UnknownAccount):
            self.bank.pay(**self.command(account_id="missing"))
        self.assert_invariants(balance=1000, payments=0)


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--crash-worker":
        parser = argparse.ArgumentParser()
        parser.add_argument("--crash-worker", dest="database", required=True)
        parser.add_argument("fault", choices=("crash_before_commit", "crash_after_commit"))
        args = parser.parse_args()
        SyntheticPayments(args.database).pay(
            account_id="alice", operation_id="op-1", amount_cents=700,
            payee="loja-demo", recovery_epoch=0, fault=args.fault,
        )
        return 1  # O worker deve terminar no ponto de falha solicitado.
    print("LABORATÓRIO SINTÉTICO LOCAL — NÃO É CÓDIGO NEM ARQUITETURA DO NUBANK", flush=True)
    print("Python stdlib + SQLite; bancos temporários; valores inteiros em centavos.", flush=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TrustInvariantTests)
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
