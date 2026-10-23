"""Caso 09: projeção de fatura sintética; nenhuma API Nubank."""
from dataclasses import dataclass, replace
import unittest


@dataclass(frozen=True)
class Invoice:
    period: str
    revision: int
    total_cents: int
    due_date: str
    entries: tuple

    def validate(self):
        if type(self.entries) is not tuple:
            raise ValueError('lançamentos devem ser tupla imutável')
        values = [self.total_cents, *self.entries]
        if any(type(value) is not int for value in values):
            raise ValueError('centavos inteiros obrigatórios')
        if sum(self.entries) != self.total_cents:
            raise ValueError('snapshot inconsistente')
        if self.revision < 1 or not self.due_date:
            raise ValueError('metadados ausentes')
        return self


class Screen:
    def __init__(self, invoice):
        self.invoice = invoice.validate()
        self.show_chart = True

    def apply(self, invoice):
        invoice.validate()
        if invoice.period != self.invoice.period:
            raise ValueError('seleção explícita de período necessária')
        if invoice.revision < self.invoice.revision:
            return False
        if invoice.revision == self.invoice.revision:
            if invoice != self.invoice:
                raise ValueError('mesma revisão com conteúdo diferente')
            return False
        self.invoice = invoice
        return True

    def select_period(self, invoice):
        self.invoice = invoice.validate()

    def view(self):
        return dict(period=self.invoice.period,
                    total_cents=self.invoice.total_cents,
                    due_date=self.invoice.due_date,
                    chart=self.invoice.entries if self.show_chart else None)


class Tests(unittest.TestCase):
    def setUp(self):
        self.invoice = Invoice('2026-10', 1, 900, '2026-11-10', (1000, -100))
        self.screen = Screen(self.invoice)

    def test_hide_chart_keeps_financial_information(self):
        before = self.screen.view()
        self.screen.show_chart = False
        after = self.screen.view()
        for key in ('period', 'total_cents', 'due_date'):
            self.assertEqual(before[key], after[key])
        self.assertIsNone(after['chart'])

    def test_empty_period(self):
        self.screen.select_period(Invoice('2026-11', 1, 0, '2026-12-10', ()))
        self.assertEqual(self.screen.view()['total_cents'], 0)

    def test_refund_is_signed(self):
        self.assertEqual(self.screen.view()['total_cents'], 900)

    def test_stale_revision_ignored(self):
        self.screen.apply(replace(self.invoice, revision=2))
        self.assertFalse(self.screen.apply(self.invoice))
        self.assertEqual(self.screen.invoice.revision, 2)

    def test_conflicting_revision_rejected(self):
        with self.assertRaises(ValueError):
            self.screen.apply(replace(self.invoice, due_date='2026-11-15'))

    def test_partial_snapshot_rejected(self):
        with self.assertRaises(ValueError):
            Screen(replace(self.invoice, total_cents=1000))

    def test_wrong_period_not_silently_applied(self):
        with self.assertRaises(ValueError):
            self.screen.apply(replace(self.invoice, period='2026-11'))

    def test_mutable_entries_rejected(self):
        entries = [1000, -100]
        with self.assertRaises(ValueError):
            Screen(replace(self.invoice, entries=entries))
        self.assertEqual(self.screen.view()['total_cents'], 900)


if __name__ == '__main__':
    unittest.main(verbosity=2)
