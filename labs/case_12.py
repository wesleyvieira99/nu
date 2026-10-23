"""Caso 12: reserva sintética de capacidade; não provisiona cloud."""
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest


class Capacity:
    def __init__(self, limits, used, reserve):
        if not limits or set(limits) != set(used) or set(limits) != set(reserve):
            raise ValueError('dimensões inconsistentes')
        for key in limits:
            values = (limits[key], used[key], reserve[key])
            if any(type(v) is not int or v < 0 for v in values):
                raise ValueError('configuração inválida')
            if used[key] + reserve[key] > limits[key]:
                raise ValueError('baseline excede limite seguro')
        self.limits = dict(limits)
        self.used, self.reserve_floor = dict(used), dict(reserve)
        self.allocations = {}
        # Retido após release: uma tentativa atrasada não recria a reserva.
        self.requests = {}
        self.lock = threading.Lock()

    def allocate(self, token, demand):
        with self.lock:
            if token in self.requests:
                if self.requests[token] != demand:
                    raise ValueError('token conflitante')
                return False
            if not demand or set(demand) - set(self.limits):
                raise ValueError('recurso desconhecido ou demanda vazia')
            if any(type(v) is not int or v <= 0 for v in demand.values()):
                raise ValueError('demanda inteira positiva obrigatória')
            available = {}
            for resource, limit in self.limits.items():
                pending = sum(x.get(resource, 0)
                              for x in self.allocations.values())
                available[resource] = (limit - self.used[resource]
                    - self.reserve_floor[resource] - pending)
            if any(amount > available[key] for key, amount in demand.items()):
                raise RuntimeError('capacidade insuficiente')
            self.allocations[token] = dict(demand)
            self.requests[token] = dict(demand)
            return True

    def release(self, token):
        with self.lock:
            return self.allocations.pop(token, None) is not None


def days_to_threshold(used, limit, reserve, daily_growth):
    remaining = limit - reserve - used
    if remaining <= 0:
        return 0.0
    return float('inf') if daily_growth <= 0 else remaining / daily_growth


class Tests(unittest.TestCase):
    def setUp(self):
        self.capacity = Capacity({'cpu': 10, 'ip': 10},
                                 {'cpu': 4, 'ip': 4}, {'cpu': 1, 'ip': 1})

    def test_multidimensional_reservation_is_atomic(self):
        with self.assertRaises(RuntimeError):
            self.capacity.allocate('a', {'cpu': 2, 'ip': 6})
        self.assertEqual(self.capacity.allocations, {})

    def test_same_token_not_reserved_twice(self):
        self.assertTrue(self.capacity.allocate('a', {'cpu': 3}))
        self.assertFalse(self.capacity.allocate('a', {'cpu': 3}))
        self.assertEqual(len(self.capacity.allocations), 1)

    def test_conflicting_token(self):
        self.capacity.allocate('a', {'cpu': 3})
        with self.assertRaises(ValueError):
            self.capacity.allocate('a', {'cpu': 4})

    def test_concurrent_demands_cannot_overbook(self):
        barrier = threading.Barrier(2)
        def attempt(token):
            barrier.wait()
            try:
                self.capacity.allocate(token, {'cpu': 3})
                return 'accepted'
            except RuntimeError:
                return 'rejected'
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(attempt, ['a', 'b']))
        self.assertEqual(sorted(results), ['accepted', 'rejected'])

    def test_release_is_idempotent(self):
        self.capacity.allocate('a', {'cpu': 5})
        self.assertTrue(self.capacity.release('a'))
        self.assertFalse(self.capacity.release('a'))

    def test_unknown_resource_rejected(self):
        with self.assertRaises(ValueError):
            self.capacity.allocate('a', {'gpu': 1})

    def test_forecast(self):
        self.assertEqual(days_to_threshold(70, 100, 10, 5), 4)
        self.assertEqual(days_to_threshold(95, 100, 10, 5), 0)
        self.assertEqual(days_to_threshold(70, 100, 10, 0), float('inf'))

    def test_replay_after_release_cannot_resurrect_reservation(self):
        self.capacity.allocate('a', {'cpu': 3})
        self.capacity.release('a')
        self.assertFalse(self.capacity.allocate('a', {'cpu': 3}))
        self.assertEqual(self.capacity.allocations, {})

    def test_token_remains_bound_to_payload_after_release(self):
        self.capacity.allocate('a', {'cpu': 3})
        self.capacity.release('a')
        with self.assertRaises(ValueError):
            self.capacity.allocate('a', {'cpu': 4})
        self.assertEqual(self.capacity.allocations, {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
