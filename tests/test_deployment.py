"""Check the deploy settings locally. Walang private keys o live services dito."""
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

import deploy_services


ROOT = Path(__file__).resolve().parents[1]


class DeploymentTests(unittest.TestCase):
    def test_vercel_does_not_inherit_another_project_token(self):
        # A different terminal must not switch our deployment account. Dito lang ang login.
        with patch.dict('os.environ', {'VERCEL_TOKEN': 'other-account-token', 'VERCEL_ORG_ID': 'other-team', 'VERCEL_PROJECT_ID': 'other-project', 'PATH': 'keep-this-path'}):
            environment = deploy_services.cli_environment()
        for name in ('VERCEL_TOKEN', 'VERCEL_ORG_ID', 'VERCEL_PROJECT_ID'):
            self.assertNotIn(name, environment)
        self.assertEqual(environment['PATH'], 'keep-this-path')

    def test_deployment_stops_before_writes_for_another_team(self):
        # Stop before reading domains or uploading secrets. Huwag galawin ang ibang team.
        responses = [{'user': {'email': 'joshricaballes2007@gmail.com'}}, {'accountId': 'other-team'}]
        with patch.object(deploy_services, 'api', side_effect=responses) as api, patch.object(deploy_services, 'dotenv_values', return_value={}):
            with self.assertRaisesRegex(RuntimeError, 'Wrong Vercel team'):
                deploy_services.main()
        self.assertEqual(api.call_count, 2)

    def test_vercel_dependencies_match_requirements(self):
        # Both installers need the same tools. Para walang missing module sa Vercel.
        project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
        requirements = {
            line.strip() for line in (ROOT / 'requirements.txt').read_text(encoding='utf-8').splitlines()
            if line.strip() and not line.lstrip().startswith('#')
        }
        self.assertEqual(set(project['project']['dependencies']), requirements)
        self.assertEqual(project['tool']['vercel']['entrypoint'], 'app:app')
