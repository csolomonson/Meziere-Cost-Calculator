import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = (PROJECT_ROOT / "deployment" / "ubuntu" / "install.sh").read_text(
    encoding="utf-8"
)
VERIFIER = (PROJECT_ROOT / "deployment" / "ubuntu" / "verify.sh").read_text(
    encoding="utf-8"
)


class UbuntuDeploymentScriptTests(unittest.TestCase):
    def test_python_helpers_run_as_modules_from_the_application_root(self):
        scripts = INSTALLER + VERIFIER

        self.assertNotIn("python tools/", scripts)
        self.assertIn("python -m tools.create_user_seed", INSTALLER)
        self.assertIn("python -m tools.deployment_preflight", INSTALLER)
        self.assertIn("python -m tools.deployment_preflight", VERIFIER)

    def test_first_deployment_without_a_previous_container_is_successful(self):
        self.assertIn('[[ -n "$container_id" ]] || return 0', INSTALLER)

    def test_versioned_application_image_does_not_depend_on_compose_output_order(self):
        self.assertNotIn("docker compose config --images", INSTALLER)
        self.assertGreaterEqual(INSTALLER.count("env_value COST_APP_IMAGE"), 2)

    def test_file_backed_secrets_are_limited_to_the_container_user(self):
        self.assertIn("grant_secret_access_to_app()", INSTALLER)
        self.assertIn('chown "$app_uid:$app_gid"', INSTALLER)
        self.assertIn(
            'chmod 0400 "$secrets_dir/db_password.txt" "$secrets_dir/app_users.json"',
            INSTALLER,
        )

        deploy_body = INSTALLER.split("deploy() {", 1)[1].split("\n}", 1)[0]
        self.assertLess(
            deploy_body.index("grant_secret_access_to_app"),
            deploy_body.index("create_initial_admin_if_needed"),
        )
        self.assertLess(
            deploy_body.index("create_initial_admin_if_needed"),
            deploy_body.index("python -m tools.deployment_preflight"),
        )


if __name__ == "__main__":
    unittest.main()
