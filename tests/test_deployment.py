"""Check the deploy settings locally. Walang private keys o live services dito."""
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DeploymentTests(unittest.TestCase):
    def test_vercel_dependencies_match_requirements(self):
        # Both installers need the same tools. Para walang missing module sa Vercel.
        project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
        requirements = {
            line.strip() for line in (ROOT / 'requirements.txt').read_text(encoding='utf-8').splitlines()
            if line.strip() and not line.lstrip().startswith('#')
        }
        self.assertEqual(set(project['project']['dependencies']), requirements)
        self.assertEqual(project['tool']['vercel']['entrypoint'], 'app:app')