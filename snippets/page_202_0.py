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