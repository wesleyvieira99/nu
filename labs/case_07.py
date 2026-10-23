"""Fragmento XML inspirado em OFX: não é exportador OFX completo/certificado."""
import re
import unittest
from xml.etree import ElementTree as ET


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


class Importer:
    def __init__(self):
        self.entries = {}

    def load(self, document):
        # XML de fixtures confiáveis; não é parser de entrada hostil.
        pending = dict(self.entries)
        for row in ET.fromstring(document).findall("STMTTRN"):
            key = row.findtext("FITID")
            value = (parse_cents(row.findtext("TRNAMT")), row.findtext("MEMO"))
            if not key:
                raise ValueError("missing_identity")
            if key in pending and pending[key] != value:
                raise ValueError("identity_conflict")
            pending[key] = value
        self.entries = pending  # Só publica após validar o lote todo.
        return sum(value[0] for value in self.entries.values())


class Tests(unittest.TestCase):
    def test_negative_cent_and_integers(self):
        self.assertEqual(format_cents(-1), "-0.01")
        self.assertEqual(format_cents(-1000), "-10.00")
        self.assertEqual(format_cents(0), "0.00")

    def test_roundtrip_range_of_integer_cents(self):
        for cents in range(-10000, 10001):
            self.assertEqual(parse_cents(format_cents(cents)), cents)

    def test_invalid_formats_and_float_are_rejected(self):
        for text in (".-1", "1,00", "1.0", "1e2", " 1.00", "01.00"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_cents(text)
        for cents in (0.1, True):
            with self.assertRaises(ValueError):
                format_cents(cents)

    def test_xml_escapes_memo_and_preserves_identity(self):
        data = [dict(id="tx1", cents=-1, memo="A & B <teste>")]
        document = export_transactions(data)
        self.assertIn("&amp;", document)
        consumer = Importer()
        self.assertEqual(consumer.load(document), -1)
        self.assertEqual(consumer.entries["tx1"][1], "A & B <teste>")

    def test_reissue_does_not_duplicate_import(self):
        document = export_transactions([dict(id="tx1", cents=-123, memo="x")])
        consumer = Importer()
        self.assertEqual(consumer.load(document), -123)
        self.assertEqual(consumer.load(document), -123)
        self.assertEqual(len(consumer.entries), 1)

    def test_conflicting_reissue_is_atomic(self):
        consumer = Importer()
        consumer.load(export_transactions([dict(id="tx1", cents=-123, memo="x")]))
        changed = [dict(id="tx2", cents=100, memo="new"),
                   dict(id="tx1", cents=-124, memo="x")]
        with self.assertRaises(ValueError):
            consumer.load(export_transactions(changed))
        self.assertEqual(consumer.entries, {"tx1": (-123, "x")})

    def test_duplicate_source_identity_fails(self):
        row = dict(id="tx", cents=100, memo="x")
        with self.assertRaises(ValueError):
            export_transactions([row, row])


if __name__ == "__main__":
    print("LAB SINTÉTICO 07: fragmento XML, não arquivo OFX interoperável completo.")
    unittest.main(verbosity=2)
