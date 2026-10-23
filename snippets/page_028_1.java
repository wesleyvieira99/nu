// Fragmento autoral: todas as durações são ilustrativas.
record Budget(long deadlineNanos) {
    static Budget start(java.time.Duration timeout) {
        return new Budget(System.nanoTime() + timeout.toNanos());
    }
    long remainingNanos() {
        return Math.max(0L, deadlineNanos - System.nanoTime());
    }
    boolean exhausted() {
        return remainingNanos() == 0L;
    }
}

// O adapter repassa apenas o orçamento restante.
// O relógio monotônico mede intervalo dentro do processo.
// Não serializar deadlineNanos para outro host.
var budget = Budget.start(java.time.Duration.ofMillis(800));
if (budget.exhausted()) {
    throw new java.util.concurrent.TimeoutException();
}