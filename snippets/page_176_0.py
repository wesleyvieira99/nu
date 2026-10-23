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