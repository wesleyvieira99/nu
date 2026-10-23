"""Caso 13: governança sintética; não cria nem apaga bancos de dados."""
from dataclasses import dataclass, replace
import threading
import unittest


@dataclass(frozen=True)
class Resource:
    owner: str
    revision: int = 1
    hold: bool = False
    archived: bool = False


class Registry:
    def __init__(self):
        self.resource = Resource('team-a')
        self.lock = threading.Lock()

    def transfer(self, expected, destination, accepting_team):
        with self.lock:
            current = self.resource
            if current.revision != expected:
                raise ValueError('revisão obsoleta')
            if not destination or accepting_team != destination:
                raise PermissionError('aceite do destino obrigatório')
            if current.archived:
                raise ValueError('recurso arquivado')
            self.resource = replace(current, owner=destination,
                                    revision=current.revision + 1)
            return self.resource

    def set_hold(self):
        with self.lock:
            self.resource = replace(self.resource, hold=True,
                                    revision=self.resource.revision + 1)

    def archive(self, expected, *, inactive, retention_elapsed,
                no_dependencies, restore_verified):
        evidence = (inactive, retention_elapsed,
                    no_dependencies, restore_verified)
        if any(type(value) is not bool for value in evidence):
            raise ValueError('evidências devem ser booleanas neste modelo')
        with self.lock:
            current = self.resource
            if expected != current.revision:
                raise ValueError('evidência de revisão antiga')
            if current.hold or not all((inactive, retention_elapsed,
                                       no_dependencies, restore_verified)):
                raise PermissionError('barreiras não satisfeitas')
            if current.archived:
                return current
            self.resource = replace(current, archived=True,
                                    revision=current.revision + 1)
            return self.resource


class Tests(unittest.TestCase):
    def setUp(self):
        self.registry = Registry()
        self.evidence = dict(inactive=True, retention_elapsed=True,
                             no_dependencies=True, restore_verified=True)

    def test_destination_must_accept(self):
        with self.assertRaises(PermissionError):
            self.registry.transfer(1, 'team-b', 'team-a')
        self.assertEqual(self.registry.resource.owner, 'team-a')

    def test_stale_transfer_cannot_override(self):
        self.registry.transfer(1, 'team-b', 'team-b')
        with self.assertRaises(ValueError):
            self.registry.transfer(1, 'team-c', 'team-c')
        self.assertEqual(self.registry.resource.owner, 'team-b')

    def test_hold_blocks_archive(self):
        self.registry.set_hold()
        with self.assertRaises(PermissionError):
            self.registry.archive(2, **self.evidence)

    def test_each_missing_barrier_blocks(self):
        for key in self.evidence:
            args = dict(self.evidence, **{key: False})
            with self.subTest(key=key), self.assertRaises(PermissionError):
                self.registry.archive(1, **args)

    def test_old_evidence_blocks_after_transfer(self):
        self.registry.transfer(1, 'team-b', 'team-b')
        with self.assertRaises(ValueError):
            self.registry.archive(1, **self.evidence)

    def test_safe_archive_keeps_resource_record(self):
        value = self.registry.archive(1, **self.evidence)
        self.assertTrue(value.archived)
        self.assertEqual(value.owner, 'team-a')
        self.assertEqual(value.revision, 2)

    def test_archived_resource_cannot_transfer(self):
        self.registry.archive(1, **self.evidence)
        with self.assertRaises(ValueError):
            self.registry.transfer(2, 'team-b', 'team-b')

    def test_untyped_evidence_rejected(self):
        args = dict(self.evidence, inactive='false')
        with self.assertRaises(ValueError):
            self.registry.archive(1, **args)


if __name__ == '__main__':
    unittest.main(verbosity=2)
