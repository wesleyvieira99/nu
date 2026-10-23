# Entrada monetária: inteiro em centavos.
# Saída externa: decimal com ponto e duas casas.
# O parser rejeita formatos fora deste contrato sintético.
# Não existe etapa de arredondamento neste percurso.
def format_cents(cents):
    if type(cents) is not int:
        raise ValueError("integer_cents_required")
    sign = "-" if cents < 0 else ""
    units, remainder = divmod(abs(cents), 100)
    return f"{sign}{units}.{remainder:02d}"

def parse_cents(text):
    if not re.fullmatch(r"-?(?:0|[1-9][0-9]*)\.[0-9]{2}", text):
        raise ValueError("invalid_decimal_format")
    negative = text.startswith("-")
    units, fraction = text.lstrip("-").split(".")
    result = int(units) * 100 + int(fraction)
    return -result if negative else result