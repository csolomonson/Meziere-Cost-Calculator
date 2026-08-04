import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = (PROJECT_ROOT / "deployment" / "ubuntu" / "install.sh").read_text(
    encoding="utf-8"
)
VERIFIER = (PROJECT_ROOT / "deployment" / "ubuntu" / "verify.sh").read_text(
    encoding="utf-8"
)
UPDATER = (PROJECT_ROOT / "deployment" / "ubuntu" / "update.sh").read_text(
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

    def test_updater_defaults_to_master_and_accepts_one_branch(self):
        self.assertIn('branch="${1:-master}"', UPDATER)
        self.assertIn('[[ "$#" -le 1 ]]', UPDATER)
        self.assertIn('git check-ref-format --branch "$branch"', UPDATER)

    def test_updater_uses_the_checkout_owner_and_requires_a_clean_fast_forward(self):
        self.assertIn('git_user="${SUDO_USER:-}"', UPDATER)
        self.assertIn('sudo -H -u "$git_user" -- git', UPDATER)
        self.assertIn("status --porcelain --untracked-files=normal", UPDATER)
        self.assertIn('merge --ff-only "refs/remotes/origin/$branch"', UPDATER)
        self.assertIn('[[ "$commit_sha" == "$remote_sha" ]]', UPDATER)

    def test_updater_generates_an_immutable_image_from_the_git_commit(self):
        self.assertIn('short_sha="${commit_sha:0:12}"', UPDATER)
        self.assertIn('app_version="git-$short_sha"', UPDATER)
        self.assertIn('image_tag="cost-calculator:$app_version"', UPDATER)
        self.assertIn('print "APP_VERSION=" app_version', UPDATER)
        self.assertIn('print "COST_APP_IMAGE=" image_tag', UPDATER)

    def test_updater_installs_and_verifies_the_selected_commit(self):
        install_index = UPDATER.index('deployment/ubuntu/install.sh')
        verify_index = UPDATER.index('deployment/ubuntu/verify.sh')
        self.assertLess(install_index, verify_index)


if __name__ == "__main__":
    unittest.main()
