"""Caso 11: leitura materializada sintética; não autoriza pagamentos."""
import unittest


class Projection:
    def __init__(self):
        self.parts = {}
        self.fallbacks = 0

    def apply(self, component, version, cents, observed_at, now):
        if component not in {'balance', 'limit'}:
            raise ValueError('componente desconhecido')
        if type(cents) is not int or cents < 0:
            raise ValueError('centavos inválidos')
        if type(version) is not int or version < 1:
            raise ValueError('versão inválida')
        if observed_at > now:
            raise ValueError('timestamp futuro')
        candidate = (version, cents, observed_at)
        previous = self.parts.get(component)
        if previous and version < previous[0]:
            return False
        if previous and version == previous[0]:
            if previous != candidate:
                raise ValueError('versão conflitante')
            return False
        self.parts[component] = candidate
        return True

    def read(self, now, max_age, canonical_reader, unavailable=False):
        complete = {'balance', 'limit'} <= self.parts.keys()
        fresh = complete and all(
            0 <= now - row[2] <= max_age for row in self.parts.values())
        if unavailable or not fresh:
            self.fallbacks += 1
            return {'source': 'canonical', 'data': canonical_reader()}
        return {'source': 'projection', 'data': {
            key: {'version': value[0], 'cents': value[1]}
            for key, value in self.parts.items()}}


class Tests(unittest.TestCase):
    def setUp(self):
        self.view = Projection()
        self.view.apply('balance', 1, 1000, 100, 100)
        self.view.apply('limit', 1, 2000, 100, 100)
        self.origin = lambda: {'validated': True}

    def test_fresh_projection_used(self):
        result = self.view.read(105, 10, self.origin)
        self.assertEqual(result['source'], 'projection')

    def test_old_component_forces_fallback(self):
        self.view.apply('balance', 2, 900, 119, 119)
        result = self.view.read(120, 10, self.origin)
        self.assertEqual(result['source'], 'canonical')
        self.assertEqual(self.view.fallbacks, 1)

    def test_old_version_does_not_replace(self):
        self.view.apply('balance', 2, 900, 101, 101)
        self.assertFalse(self.view.apply('balance', 1, 1000, 100, 101))
        self.assertEqual(self.view.parts['balance'][0], 2)

    def test_conflicting_version_rejected(self):
        with self.assertRaises(ValueError):
            self.view.apply('limit', 1, 3000, 100, 100)

    def test_future_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            self.view.apply('limit', 2, 3000, 200, 100)

    def test_missing_component_forces_fallback(self):
        self.view.parts.pop('limit')
        self.assertEqual(self.view.read(105, 10, self.origin)['source'],
                         'canonical')

    def test_unavailable_projection_forces_fallback(self):
        result = self.view.read(105, 10, self.origin, unavailable=True)
        self.assertEqual(result['source'], 'canonical')


if __name__ == '__main__':
    unittest.main(verbosity=2)
