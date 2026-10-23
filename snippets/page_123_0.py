# Fragmento didático: BANKTRANLIST não é um documento OFX completo.
# FITID preserva a identidade entre reemissões.
# O gerador XML cuida de escapar o texto da descrição.
# A ordem recebida é preservada neste fragmento.
# Identidades repetidas são recusadas antes da publicação.
# O consumidor de teste reconcilia o resultado do lote.
def export_transactions(transactions):
    root = ET.Element("BANKTRANLIST")
    seen = set()
    for tx in transactions:
        if tx["id"] in seen:
            raise ValueError("duplicate_transaction")
        seen.add(tx["id"])
        row = ET.SubElement(root, "STMTTRN")
        ET.SubElement(row, "FITID").text = tx["id"]
        ET.SubElement(row, "TRNAMT").text = format_cents(tx["cents"])
        ET.SubElement(row, "MEMO").text = tx["memo"]
    return ET.tostring(root, encoding="unicode")