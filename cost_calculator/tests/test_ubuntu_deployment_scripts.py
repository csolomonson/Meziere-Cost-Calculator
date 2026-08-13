import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = (PROJECT_ROOT / "deployment" / "ubuntu" / "install.sh").read_text(
    encoding="utf-8"
)
VERIFIER = (PROJECT_ROOT / "deployment" / "ubuntu" / "verify.sh").read_text(
    encoding="utf-8"
)
COMPOSE = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
CADDY = (PROJECT_ROOT / "deployment" / "Caddyfile").read_text(encoding="utf-8")
ENV_EXAMPLE = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
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

    def test_updater_validates_the_target_before_switching(self):
        validation_index = UPDATER.index(
            'cat-file -e "refs/remotes/origin/$branch:${project_prefix}${required_path}"'
        )
        switch_index = UPDATER.index('run_git switch "$branch"')
        self.assertLess(validation_index, switch_index)
        self.assertIn("deployment/ubuntu/update.sh", UPDATER)

    def test_single_branch_clone_does_not_require_new_tracking_configuration(self):
        self.assertIn('switch --no-track -c "$branch"', UPDATER)
        self.assertNotIn('switch --track -c "$branch"', UPDATER)

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

    def test_installer_offers_both_costing_storage_layouts(self):
        self.assertIn("separate database or schema in ERP database", INSTALLER)
        self.assertIn('storage_mode="database"', INSTALLER)
        self.assertIn('storage_mode="erp_schema"', INSTALLER)
        self.assertIn("COST_APP_STORAGE_MODE=%s", INSTALLER)
        self.assertIn("COST_APP_SCHEMA=%s", INSTALLER)
        self.assertIn("--configure-storage", INSTALLER)
        self.assertIn("write_storage_settings", INSTALLER)

    def test_installer_generates_a_dba_storage_setup_script(self):
        self.assertIn("reset-selected-storage.sql", INSTALLER)
        self.assertIn('print "IF DB_ID', INSTALLER)
        self.assertIn('print "IF SCHEMA_ID', INSTALLER)
        self.assertIn('print "IF DB_NAME() <>', INSTALLER)
        self.assertIn('print "    SET NOEXEC ON;"', INSTALLER)
        self.assertIn("GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA", INSTALLER)
        self.assertIn("have a database administrator review and run", INSTALLER)

    def test_compose_passes_the_selected_schema_to_the_application(self):
        self.assertIn("COST_APP_SCHEMA: ${COST_APP_SCHEMA:-dbo}", COMPOSE)

    def test_caddy_serves_the_hostname_and_vm_ipv4_address(self):
        self.assertIn("{$APP_HOSTNAME}:443, {$APP_IP_ADDRESS}:443", CADDY)
        self.assertIn("default_sni {$APP_IP_ADDRESS}", CADDY)
        self.assertIn("APP_IP_ADDRESS: ${APP_IP_ADDRESS:-127.0.0.1}", COMPOSE)
        self.assertIn("APP_IP_ADDRESS=192.0.2.10", ENV_EXAMPLE)

    def test_installer_detects_backfills_and_verifies_the_vm_ipv4_address(self):
        self.assertIn("detect_primary_ipv4()", INSTALLER)
        self.assertIn("ensure_network_settings()", INSTALLER)
        self.assertIn("APP_IP_ADDRESS=%s", INSTALLER)
        self.assertIn('"https://$app_ip_address/api/ready"', INSTALLER)
        self.assertIn('"https://$app_ip_address/api/health"', VERIFIER)
        self.assertIn('"https://$app_ip_address/api/ready"', VERIFIER)
        self.assertIn('--cacert "$runtime_dir/caddy-root.crt"', INSTALLER)
        self.assertIn('--cacert "$ca_certificate"', VERIFIER)


if __name__ == "__main__":
    unittest.main()
