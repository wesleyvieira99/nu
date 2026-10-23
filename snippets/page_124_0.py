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