"""Caso 14: contratos BDC sintéticos e coorte; não acessa BDC/NuDS reais."""
from dataclasses import dataclass
import hashlib
import unittest


@dataclass(frozen=True)
class Manifest:
    revision: str
    protocol: int
    components: tuple
    action: str
    accessible_name: str


def validate(manifest):
    if type(manifest.components) is not tuple:
        raise ValueError('componentes devem ser tupla imutável')
    if any(type(item) is not str or not item for item in manifest.components):
        raise ValueError('componentes devem ser identificadores imutáveis')
    if not manifest.revision or manifest.protocol != 1:
        raise ValueError('protocolo ou revisão inválidos')
    if not manifest.components or not manifest.accessible_name.strip():
        raise ValueError('composição ou semântica ausente')
    if manifest.action not in {'view-invoice', 'open-support'}:
        raise ValueError('ação fora do catálogo proposto')
    return manifest


class Publisher:
    def __init__(self):
        self.revisions = {}
        self.active = None

    def publish(self, manifest):
        validate(manifest)
        previous = self.revisions.get(manifest.revision)
        if previous is not None and previous != manifest:
            raise ValueError('revisão é imutável')
        self.revisions[manifest.revision] = manifest

    def activate(self, revision):
        if revision not in self.revisions:
            raise ValueError('revisão não publicada')
        self.active = revision

    def select(self, capabilities, protocol, fallback):
        if self.revisions.get(fallback.revision) != fallback:
            raise ValueError('fallback não publicado')
        current = self.revisions.get(self.active)
        compatible = current and current.protocol == protocol
        compatible = compatible and set(current.components) <= capabilities
        if compatible:
            return current
        if (fallback.protocol == protocol
                and set(fallback.components) <= capabilities):
            return fallback
        raise ValueError('nenhuma composição compatível')


def in_cohort(subject, percent, salt='synthetic-rollout-v1'):
    if type(percent) is not int or not 0 <= percent <= 100:
        raise ValueError('percentual inválido')
    value = hashlib.sha256(f'{salt}:{subject}'.encode()).digest()
    return int.from_bytes(value[:8], 'big') % 10000 < percent * 100


class Tests(unittest.TestCase):
    def setUp(self):
        self.publisher = Publisher()
        self.old = Manifest('r1', 1, ('text',), 'view-invoice', 'Ver fatura')
        self.new = Manifest('r2', 1, ('text', 'chart'), 'view-invoice', 'Fatura')
        self.publisher.publish(self.old)
        self.publisher.publish(self.new)
        self.publisher.activate('r2')

    def test_old_client_gets_fallback(self):
        self.assertEqual(self.publisher.select({'text'}, 1, self.old), self.old)

    def test_capable_client_gets_active_revision(self):
        self.assertEqual(self.publisher.select({'text', 'chart'}, 1, self.old),
                         self.new)

    def test_revision_cannot_change(self):
        changed = Manifest('r1', 1, ('chart',), 'view-invoice', 'Fatura')
        with self.assertRaises(ValueError):
            self.publisher.publish(changed)

    def test_missing_accessibility_rejected(self):
        with self.assertRaises(ValueError):
            validate(Manifest('r3', 1, ('text',), 'view-invoice', ''))

    def test_rollback_selects_old_revision(self):
        self.publisher.activate('r1')
        self.assertEqual(self.publisher.select({'text', 'chart'}, 1, self.old),
                         self.old)

    def test_cohort_is_stable_and_monotonic(self):
        for person in map(str, range(500)):
            self.assertEqual(in_cohort(person, 5), in_cohort(person, 5))
            if in_cohort(person, 5):
                self.assertTrue(in_cohort(person, 20))

    def test_cohort_boundaries(self):
        self.assertFalse(in_cohort('demo', 0))
        self.assertTrue(in_cohort('demo', 100))

    def test_arbitrary_action_rejected(self):
        with self.assertRaises(ValueError):
            validate(Manifest('r4', 1, ('text',), 'execute-money', 'Pagar'))

    def test_incompatible_fallback_is_not_returned(self):
        with self.assertRaises(ValueError):
            self.publisher.select(set(), 2, self.old)

    def test_unpublished_fallback_rejected(self):
        unknown = Manifest('r99', 1, ('text',), 'view-invoice', 'Fatura')
        with self.assertRaises(ValueError):
            self.publisher.select({'text'}, 1, unknown)

    def test_mutable_components_rejected(self):
        for components in (['text'], (['text'],), ('',)):
            with self.subTest(components=components):
                with self.assertRaises(ValueError):
                    self.publisher.publish(Manifest('r3', 1, components,
                                                    'view-invoice', 'Fatura'))
                self.assertNotIn('r3', self.publisher.revisions)


if __name__ == '__main__':
    unittest.main(verbosity=2)
