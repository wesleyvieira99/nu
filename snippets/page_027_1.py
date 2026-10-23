# Fragmento de instrumentação; tracer fornecido pelo runtime.
def confirm(command, repository, tracer):
    with tracer.start_as_current_span("journey.confirm") as span:
        span.set_attribute("journey.kind", "payment")
        span.set_attribute("contract.version", 1)
        try:
            result = repository.confirm(command)
            span.set_attribute("journey.outcome", result.kind)
            return result
        except TimeoutError:
            span.set_attribute("journey.outcome", "unknown")
            raise

# Não registrar CPF, token, saldo ou payload integral.
# Propagar contexto entre produtores e consumidores.
# Para processamento assíncrono, modelar links/parentesco
# de acordo com a semântica real do trabalho.