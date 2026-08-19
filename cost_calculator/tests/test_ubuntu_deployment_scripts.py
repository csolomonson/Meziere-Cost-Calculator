import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
CONFIGURATOR = (PROJECT_ROOT / "deployment" / "ubuntu" / "configure.sh").read_text(
    encoding="utf-8"
)
STARTER = (PROJECT_ROOT / "deployment" / "ubuntu" / "start.sh").read_text(
    encoding="utf-8"
)
INSTALLER = (PROJECT_ROOT / "deployment" / "ubuntu" / "install.sh").read_text(
    encoding="utf-8"
)
UPDATER = (PROJECT_ROOT / "deployment" / "ubuntu" / "update.sh").read_text(
    encoding="utf-8"
)
VERIFIER = (PROJECT_ROOT / "deployment" / "ubuntu" / "verify.sh").read_text(
    encoding="utf-8"
)
ROLLBACK = (PROJECT_ROOT / "deployment" / "ubuntu" / "rollback.sh").read_text(
    encoding="utf-8"
)
COMPOSE = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
CADDY = (PROJECT_ROOT / "deployment" / "Caddyfile").read_text(encoding="utf-8")
ENV_EXAMPLE = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
DOCKERIGNORE = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")
DOCKERFILE = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
CONTAINER_CONFIG = (PROJECT_ROOT / "deployment" / "configure-container.sh").read_text(
    encoding="utf-8"
)
CONTAINER_START = (PROJECT_ROOT / "deployment" / "start-app.sh").read_text(
    encoding="utf-8"
)
WORKFLOW = (
    REPOSITORY_ROOT / ".github" / "workflows" / "publish-container-release.yml"
).read_text(encoding="utf-8")


class UbuntuDeploymentScriptTests(unittest.TestCase):
    def test_release_workflow_publishes_multi_platform_image_and_attestation(self):
        self.assertIn('tags:\n      - "v*"', WORKFLOW)
        self.assertIn("linux/amd64,linux/arm64", WORKFLOW)
        self.assertIn("docker/build-push-action@v7", WORKFLOW)
        self.assertIn("push: true", WORKFLOW)
        self.assertIn("actions/attest@v4", WORKFLOW)
        self.assertIn("subject-digest: ${{ steps.image.outputs.digest }}", WORKFLOW)

    def test_release_workflow_creates_source_free_bundle_with_digest_metadata(self):
        self.assertIn("cost-calculator-$RELEASE_TAG", WORKFLOW)
        self.assertIn("deployment/release.env", WORKFLOW)
        self.assertIn("APP_IMAGE_DIGEST", WORKFLOW)
        self.assertIn("compose.yaml", WORKFLOW)
        self.assertIn("database/reset_schema.sql", WORKFLOW)
        self.assertIn("gh release create", WORKFLOW)
        self.assertNotIn('install -D -m 0644 "$app_dir/api.py"', WORKFLOW)

    def test_compose_uses_only_a_published_immutable_image(self):
        self.assertNotIn("build:", COMPOSE)
        self.assertIn("COST_APP_IMAGE must be set by deployment/release.env", COMPOSE)
        self.assertIn("name: cost-calculator", COMPOSE)
        self.assertIn("docker compose pull app proxy", CONFIGURATOR)
        self.assertNotIn("docker compose build", CONFIGURATOR + STARTER)

    def test_startup_runs_configuration_before_starting_without_building(self):
        configure_index = STARTER.index('bash "$script_dir/configure.sh"')
        up_index = STARTER.index("docker compose up")
        self.assertLess(configure_index, up_index)
        self.assertIn("--no-build", STARTER)
        self.assertIn("--skip-configure", STARTER)
        self.assertIn('exec bash "$script_dir/start.sh"', INSTALLER)

    def test_container_startup_configures_persistent_state_before_uvicorn(self):
        configure_index = CONTAINER_START.index("configure-container.sh")
        uvicorn_index = CONTAINER_START.index("exec uvicorn")
        self.assertLess(configure_index, uvicorn_index)
        self.assertIn("COST_DB_PASSWORD_FILE", CONTAINER_CONFIG)
        self.assertIn("COST_APP_USERS_SEED_FILE", CONTAINER_CONFIG)
        self.assertIn("missing or unreadable", CONTAINER_CONFIG)

    def test_release_identity_is_synchronized_and_digest_pinned(self):
        self.assertIn("sync_release_settings()", CONFIGURATOR)
        self.assertIn("deployment/release.env", CONFIGURATOR)
        self.assertIn("ghcr\\.io/", CONFIGURATOR)
        self.assertIn("@sha256:", CONFIGURATOR)
        self.assertIn("APP_VERSION=v1.0.0", ENV_EXAMPLE)
        self.assertIn("@sha256:", ENV_EXAMPLE)

    def test_configuration_preserves_installer_storage_and_preflight_behavior(self):
        self.assertIn("separate database or schema in ERP database", CONFIGURATOR)
        self.assertIn('storage_mode="database"', CONFIGURATOR)
        self.assertIn('storage_mode="erp_schema"', CONFIGURATOR)
        self.assertIn("reset-selected-storage.sql", CONFIGURATOR)
        self.assertIn('print "IF DB_ID', CONFIGURATOR)
        self.assertIn('print "IF SCHEMA_ID', CONFIGURATOR)
        self.assertIn("GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA", CONFIGURATOR)
        self.assertIn("python -m tools.deployment_preflight", CONFIGURATOR)

    def test_python_helpers_run_as_modules_from_the_application_root(self):
        scripts = CONFIGURATOR + VERIFIER
        self.assertNotIn("python tools/", scripts)
        self.assertIn("python -m tools.create_user_seed", CONFIGURATOR)
        self.assertIn("python -m tools.deployment_preflight", scripts)

    def test_file_backed_secrets_are_limited_to_the_container_user(self):
        self.assertIn("grant_secret_access_to_app()", CONFIGURATOR)
        self.assertIn('chown "$app_uid:$app_gid"', CONFIGURATOR)
        self.assertIn(
            'chmod 0400 "$secrets_dir/db_password.txt" "$secrets_dir/app_users.json"',
            CONFIGURATOR,
        )
        runtime_body = CONFIGURATOR.split("configure_runtime() {", 1)[1].split(
            "\n}", 1
        )[0]
        self.assertLess(
            runtime_body.index("grant_secret_access_to_app"),
            runtime_body.index("create_initial_admin_if_needed"),
        )
        self.assertLess(
            runtime_body.index("create_initial_admin_if_needed"),
            runtime_body.index("python -m tools.deployment_preflight"),
        )
        self.assertIn("--gid 10001 costapp", DOCKERFILE)
        self.assertIn("--uid 10001 --ingroup costapp", DOCKERFILE)

    def test_private_sql_ca_is_injected_at_runtime_not_baked_into_image(self):
        self.assertIn("prepare_ca_bundle()", CONFIGURATOR)
        self.assertIn("deployment/sql-ca/*.crt", DOCKERIGNORE)
        self.assertIn(
            "./deployment/runtime/ca-certificates.crt:/etc/ssl/certs/ca-certificates.crt:ro",
            COMPOSE,
        )

    def test_build_context_excludes_runtime_configuration_and_secrets(self):
        for ignored_path in (
            ".env",
            "secrets",
            "deployment/runtime",
            "deployment/release.env",
            "deployment/sql-ca/*.crt",
        ):
            self.assertIn(ignored_path, DOCKERIGNORE)

    def test_caddy_serves_hostname_and_vm_ipv4_address(self):
        self.assertIn("{$APP_HOSTNAME}:443, {$APP_IP_ADDRESS}:443", CADDY)
        self.assertIn("default_sni {$APP_IP_ADDRESS}", CADDY)
        self.assertIn("APP_IP_ADDRESS: ${APP_IP_ADDRESS:-127.0.0.1}", COMPOSE)
        self.assertIn("APP_IP_ADDRESS=192.0.2.10", ENV_EXAMPLE)
        self.assertIn('"https://$app_ip_address/api/ready"', STARTER)
        self.assertIn('"https://$app_ip_address/api/health"', VERIFIER)

    def test_update_uses_extracted_release_instead_of_git_checkout(self):
        self.assertNotIn("git ", UPDATER)
        self.assertIn("deployment/release.env", UPDATER)
        self.assertIn('exec bash "$script_dir/start.sh"', UPDATER)

    def test_rollback_accepts_only_digest_pinned_ghcr_images(self):
        self.assertIn("ghcr\\.io/", ROLLBACK)
        self.assertIn("@sha256:", ROLLBACK)
        self.assertIn('APP_VERSION="$previous_version"', ROLLBACK)
        self.assertIn("--pull never", ROLLBACK)


if __name__ == "__main__":
    unittest.main()
