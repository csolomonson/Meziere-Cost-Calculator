import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
DEPLOYMENT = PROJECT_ROOT / "deployment"

DOCKERFILE = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
COMPOSE = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
DOCKERIGNORE = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")
CADDY = (DEPLOYMENT / "Caddyfile").read_text(encoding="utf-8")
ENTRYPOINT = (DEPLOYMENT / "container-entrypoint.sh").read_text(encoding="utf-8")
CONFIGURE = (DEPLOYMENT / "configure-image.sh").read_text(encoding="utf-8")
VALIDATOR = (DEPLOYMENT / "configure-container.sh").read_text(encoding="utf-8")
STARTER = (DEPLOYMENT / "start-app.sh").read_text(encoding="utf-8")
WORKFLOW = (
    REPOSITORY_ROOT / ".github" / "workflows" / "publish-container-release.yml"
).read_text(encoding="utf-8")


class ContainerDeploymentContractTests(unittest.TestCase):
    def test_release_workflow_publishes_multi_platform_image_and_attestation(self):
        self.assertIn('tags:\n      - "v*"', WORKFLOW)
        self.assertIn("linux/amd64,linux/arm64", WORKFLOW)
        self.assertIn("docker/build-push-action@v7", WORKFLOW)
        self.assertIn("push: true", WORKFLOW)
        self.assertIn("actions/attest@v4", WORKFLOW)
        self.assertIn("subject-digest: ${{ steps.image.outputs.digest }}", WORKFLOW)

    def test_release_contains_an_immutable_image_reference_not_a_source_bundle(self):
        self.assertIn("cost-calculator-%s-image.txt", WORKFLOW)
        self.assertIn("'%s:%s@%s\\n'", WORKFLOW)
        self.assertIn("gh release create", WORKFLOW)
        self.assertNotIn("tar ", WORKFLOW)
        self.assertNotIn("compose.yaml", WORKFLOW)
        self.assertNotIn("deployment/release.env", WORKFLOW)

    def test_image_bundles_caddy_and_uses_one_unprivileged_runtime(self):
        self.assertIn("FROM caddy:2.11.4-alpine AS caddy", DOCKERFILE)
        self.assertIn("COPY --from=caddy /usr/bin/caddy /usr/bin/caddy", DOCKERFILE)
        self.assertIn("--uid 10001 --ingroup costapp", DOCKERFILE)
        self.assertIn("USER costapp", DOCKERFILE)
        self.assertIn("EXPOSE 8443", DOCKERFILE)
        self.assertIn(
            "ln -s /var/lib/cost-calculator/ca/ca-certificates.crt "
            "/etc/ssl/certs/ca-certificates.crt",
            DOCKERFILE,
        )
        self.assertIn('["/app/deployment/container-entrypoint.sh"]', DOCKERFILE)
        self.assertIn('["serve"]', DOCKERFILE)

    def test_compose_is_an_optional_one_image_wrapper(self):
        self.assertNotIn("build:", COMPOSE)
        self.assertIn("COST_APP_IMAGE", COMPOSE)
        self.assertIn('"443:8443"', COMPOSE)
        self.assertIn("app_state:/var/lib/cost-calculator", COMPOSE)
        self.assertIn("name: cost-calculator-data", COMPOSE)
        self.assertNotIn("proxy:", COMPOSE)
        self.assertNotIn("secrets:", COMPOSE)

    def test_caddy_and_uvicorn_communicate_only_over_container_loopback(self):
        self.assertIn("https://{$APP_HOSTNAME},", CADDY)
        self.assertIn("https://{$APP_IP_ADDRESS}", CADDY)
        self.assertIn("servers :8443", CADDY)
        self.assertIn("protocols h1 h2", CADDY)
        self.assertIn("reverse_proxy 127.0.0.1:8000", CADDY)
        self.assertIn("--host 127.0.0.1", STARTER)
        self.assertIn('--forwarded-allow-ips="127.0.0.1"', STARTER)

    def test_startup_preflights_before_starting_both_processes(self):
        validation_index = STARTER.index("configure-container.sh")
        preflight_index = STARTER.index("python -m tools.deployment_preflight")
        uvicorn_index = STARTER.index("uvicorn api:app")
        caddy_index = STARTER.index("caddy run")
        self.assertLess(validation_index, preflight_index)
        self.assertLess(preflight_index, uvicorn_index)
        self.assertLess(preflight_index, caddy_index)
        self.assertIn("trap handle_signal TERM INT", STARTER)

    def test_entrypoint_exposes_configuration_and_operational_commands(self):
        for command in (
            "configure)",
            "install-ca)",
            "serve)",
            "preflight)",
            "database-setup)",
            "export-ca)",
        ):
            self.assertIn(command, ENTRYPOINT)
        self.assertIn("/var/lib/cost-calculator", ENTRYPOINT)
        self.assertNotIn("eval ", ENTRYPOINT)

    def test_configuration_is_written_only_to_persistent_state(self):
        self.assertIn(
            'state_root="${COST_APP_STATE_ROOT:-/var/lib/cost-calculator}"',
            CONFIGURE,
        )
        self.assertIn('config_file="$state_root/config/runtime.env"', CONFIGURE)
        self.assertIn('password_file="$state_root/secrets/db_password.txt"', CONFIGURE)
        self.assertIn('users_file="$state_root/users/app_users.json"', CONFIGURE)
        self.assertIn(
            'database_setup_file="$state_root/database/reset-selected-storage.sql"',
            CONFIGURE,
        )
        self.assertIn("python -m tools.create_user_seed", CONFIGURE)
        self.assertIn("container-entrypoint.sh preflight", CONFIGURE)
        self.assertIn("python -m tools.deployment_preflight", ENTRYPOINT)
        self.assertNotIn("docker.sock", CONFIGURE + STARTER + COMPOSE)

    def test_runtime_validator_requires_configuration_secrets_users_and_ca(self):
        for relative_path in (
            "config/runtime.env",
            "users/app_users.json",
            "secrets/db_password.txt",
            "ca/ca-certificates.crt",
        ):
            self.assertIn(relative_path, VALIDATOR)
        self.assertIn("missing or unreadable", VALIDATOR)
        self.assertIn("/usr/local/share/cost-calculator/ca-certificates.crt", VALIDATOR)

    def test_configuration_preserves_database_or_erp_schema_storage_modes(self):
        self.assertIn("Costing storage (database/schema)", CONFIGURE)
        self.assertIn('storage_mode="database"', CONFIGURE)
        self.assertIn('storage_mode="erp_schema"', CONFIGURE)
        self.assertIn("reset-selected-storage.sql", CONFIGURE)
        self.assertIn('print "IF DB_ID', CONFIGURE)
        self.assertIn('print "IF SCHEMA_ID', CONFIGURE)
        self.assertIn("GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA", CONFIGURE)

    def test_runtime_data_and_private_ca_are_excluded_from_build_context(self):
        for ignored_path in (
            ".env",
            "secrets",
            "deployment/runtime",
            "deployment/sql-ca/*.crt",
        ):
            self.assertIn(ignored_path, DOCKERIGNORE)

    def test_obsolete_host_deployment_scripts_are_gone(self):
        ubuntu_dir = DEPLOYMENT / "ubuntu"
        self.assertFalse(any(ubuntu_dir.glob("*.sh")))


if __name__ == "__main__":
    unittest.main()
