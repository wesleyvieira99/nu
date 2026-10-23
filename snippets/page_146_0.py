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