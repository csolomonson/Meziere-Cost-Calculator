import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
DEPLOYMENT = PROJECT_ROOT / "deployment"
UBUNTU = DEPLOYMENT / "ubuntu"

INSTALL = (UBUNTU / "install.sh").read_text(encoding="utf-8")
CONFIGURE = (UBUNTU / "configure.sh").read_text(encoding="utf-8")
VERIFY = (UBUNTU / "verify.sh").read_text(encoding="utf-8")
ROLLBACK = (UBUNTU / "rollback.sh").read_text(encoding="utf-8")
UPDATE = (UBUNTU / "update.sh").read_text(encoding="utf-8")
SERVICE = (UBUNTU / "cost-calculator.service").read_text(encoding="utf-8")
CADDY_OVERRIDE = (UBUNTU / "caddy-override.conf").read_text(encoding="utf-8")
CADDY = (DEPLOYMENT / "Caddyfile").read_text(encoding="utf-8")
WORKFLOW = (
    REPOSITORY_ROOT / ".github" / "workflows" / "publish-vm-release.yml"
).read_text(encoding="utf-8")


class NativeVmDeploymentContractTests(unittest.TestCase):
    def test_container_deployment_assets_are_removed(self):
        for relative_path in (
            "Dockerfile",
            "compose.yaml",
            ".dockerignore",
            "deployment/container-entrypoint.sh",
            "deployment/configure-container.sh",
            "deployment/configure-image.sh",
            "deployment/start-app.sh",
        ):
            self.assertFalse((PROJECT_ROOT / relative_path).exists(), relative_path)
        self.assertFalse(
            (REPOSITORY_ROOT / ".github/workflows/publish-container-release.yml").exists()
        )

    def test_release_workflow_publishes_an_attested_vm_archive(self):
        self.assertIn('tags:\n      - "v*"', WORKFLOW)
        self.assertIn("ubuntu-vm.tar.gz", WORKFLOW)
        self.assertIn("static/dist", WORKFLOW)
        self.assertIn("actions/attest@v4", WORKFLOW)
        self.assertIn("subject-path:", WORKFLOW)
        self.assertIn("gh release create", WORKFLOW)
        self.assertNotIn("docker/", WORKFLOW)
        self.assertNotIn("ghcr.io", WORKFLOW)

    def test_installer_targets_supported_ubuntu_lts_releases(self):
        self.assertIn('22.04|24.04', INSTALL)
        self.assertIn('ubuntu/$ubuntu_version/packages-microsoft-prod.deb', INSTALL)
        self.assertIn('ppa:deadsnakes/ppa', INSTALL)
        self.assertIn('python3.11-venv', INSTALL)
        self.assertIn('python_command="python3.11"', INSTALL)

    def test_installer_installs_host_dependencies(self):
        self.assertIn("python3-venv", INSTALL)
        self.assertIn("https://deb.nodesource.com/node_22.x", INSTALL)
        self.assertIn("Node.js 22 is required", INSTALL)
        self.assertIn("msodbcsql18", INSTALL)
        self.assertIn("apt-get install -y caddy", INSTALL)
        self.assertIn("pnpm run build", INSTALL)
        self.assertIn('"$python_command" -m venv "$staging_dir/.venv"', INSTALL)

    def test_installer_preflights_before_atomically_switching_release(self):
        self.assertLess(INSTALL.index("preflight_release\n"), INSTALL.index("activate_release\n"))
        self.assertIn('releases/$app_version', INSTALL)
        self.assertIn('mv -Tf -- "$temporary_link" "$install_root/current"', INSTALL)
        self.assertIn("previous-release", INSTALL)

    def test_configuration_persists_outside_releases(self):
        self.assertIn("/etc/cost-calculator", CONFIGURE)
        self.assertIn("/var/lib/cost-calculator", CONFIGURE)
        self.assertIn("users/app_users.json", CONFIGURE)
        self.assertIn("secrets/db_password.txt", CONFIGURE)
        self.assertIn("reset-selected-storage.sql", CONFIGURE)
        self.assertIn("tools.create_user_seed", CONFIGURE)
        self.assertIn("GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA", CONFIGURE)
        self.assertIn(']] || return 0', CONFIGURE)
        self.assertNotIn(']] || return\n', CONFIGURE)

    def test_routine_install_preserves_caddy_identity_and_checks_for_drift(self):
        self.assertIn('[[ ! -s "$caddy_config_file" || "$reconfigure" == "true" ]]', CONFIGURE)
        self.assertIn("Keeping the existing Caddy hostname and certificate identity", CONFIGURE)
        self.assertIn("verify_caddy_config_matches_runtime", CONFIGURE)
        self.assertIn("Refusing to change TLS during a routine install", CONFIGURE)

    def test_update_checks_tls_identity_before_fetching(self):
        safety_check = UPDATE.index("TLS safety check failed")
        fetch = UPDATE.index("run_git fetch")
        self.assertLess(safety_check, fetch)
        self.assertIn("No files or services were changed", UPDATE)

    def test_systemd_runs_uvicorn_as_a_restricted_service_account(self):
        self.assertIn("User=cost-calculator", SERVICE)
        self.assertIn("EnvironmentFile=/etc/cost-calculator/runtime.env", SERVICE)
        self.assertIn("--host 127.0.0.1 --port 8000", SERVICE)
        self.assertIn("ExecStartPre=", SERVICE)
        self.assertIn("tools.deployment_preflight", SERVICE)
        self.assertIn("NoNewPrivileges=true", SERVICE)
        self.assertIn("ProtectSystem=strict", SERVICE)
        self.assertIn("CapabilityBoundingSet=", SERVICE)

    def test_caddy_is_a_separate_host_service_on_https(self):
        self.assertIn("servers :443", CADDY)
        self.assertIn("reverse_proxy 127.0.0.1:8000", CADDY)
        self.assertIn("# BEGIN shopify-order-listener managed route", CADDY)
        self.assertIn("handle /sales-orders*", CADDY)
        self.assertIn("reverse_proxy 127.0.0.1:8010", CADDY)
        self.assertLess(
            CADDY.index("handle /sales-orders*"),
            CADDY.index("reverse_proxy 127.0.0.1:8000"),
        )
        self.assertIn("tls internal", CADDY)
        self.assertIn("EnvironmentFile=/etc/cost-calculator/caddy.env", CADDY_OVERRIDE)
        self.assertIn("XDG_DATA_HOME=/var/lib/caddy/data", CADDY_OVERRIDE)

    def test_verifier_checks_services_preflight_and_both_addresses(self):
        self.assertIn("systemctl is-active --quiet cost-calculator.service", VERIFY)
        self.assertIn("systemctl is-active --quiet caddy.service", VERIFY)
        self.assertIn("tools.deployment_preflight", VERIFY)
        self.assertIn('https://$APP_HOSTNAME/api/ready', VERIFY)
        self.assertIn('https://$APP_IP_ADDRESS/api/ready', VERIFY)
        self.assertIn("caddy-root.crt", VERIFY)

    def test_update_and_rollback_preserve_release_boundaries(self):
        self.assertIn('branch="${1:-no_docker}"', UPDATE)
        self.assertIn("merge --ff-only", UPDATE)
        self.assertIn("status --porcelain", UPDATE)
        self.assertIn("native Ubuntu deployment", UPDATE)
        self.assertIn('"$install_root"/releases/*', ROLLBACK)
        self.assertIn('mv -Tf -- "$temporary_link" "$install_root/current"', ROLLBACK)
        self.assertIn("previous-release", ROLLBACK)


if __name__ == "__main__":
    unittest.main()
