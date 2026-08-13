#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/../.." && pwd)"
branch="${1:-master}"

log() {
    printf '\n==> %s\n' "$*"
}

fail() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

usage() {
    printf 'Usage: sudo bash deployment/ubuntu/update.sh [branch]\n'
    printf 'Fetch and deploy origin/master, or the optional origin branch.\n'
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    usage
    exit 0
fi
[[ "$#" -le 1 ]] || {
    usage >&2
    exit 2
}
[[ "${EUID:-$(id -u)}" -eq 0 ]] || fail "Run with sudo: sudo bash deployment/ubuntu/update.sh [branch]"
command -v git >/dev/null 2>&1 || fail "Git is required to update the deployment."
git check-ref-format --branch "$branch" >/dev/null 2>&1 || fail "Invalid Git branch name: $branch"
[[ -f "$project_root/.env" ]] || fail ".env is missing. Complete the initial installation before using update.sh."

# Git operations must use the account that owns the checkout. This preserves its
# SSH keys/credential configuration and avoids Git's root ownership protection.
git_user="${SUDO_USER:-}"
if [[ -z "$git_user" || "$git_user" == "root" ]]; then
    git_user="$(stat -c '%U' "$project_root")"
fi
[[ -n "$git_user" && "$git_user" != "UNKNOWN" ]] || fail "Could not determine the deployment checkout owner."

run_git() {
    if [[ "$git_user" == "root" ]]; then
        git -C "$project_root" "$@"
    else
        sudo -H -u "$git_user" -- git -C "$project_root" "$@"
    fi
}

run_git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "$project_root is not inside a Git checkout."
working_tree_status="$(run_git status --porcelain --untracked-files=normal)"
if [[ -n "$working_tree_status" ]]; then
    printf '%s\n' "$working_tree_status" >&2
    fail "The Git checkout has uncommitted or untracked files. Commit, remove, or ignore them before updating."
fi

log "Fetching origin/$branch as $git_user"
run_git fetch --prune origin "+refs/heads/$branch:refs/remotes/origin/$branch"
run_git show-ref --verify --quiet "refs/remotes/origin/$branch" || fail "origin/$branch was not found."

# Refuse an old or unrelated branch before changing the worktree. This is
# especially important during a migration while master may not contain the
# Ubuntu deployment yet.
project_prefix="$(run_git rev-parse --show-prefix)"
for required_path in \
    compose.yaml \
    deployment/ubuntu/install.sh \
    deployment/ubuntu/update.sh \
    deployment/ubuntu/verify.sh; do
    run_git cat-file -e "refs/remotes/origin/$branch:${project_prefix}${required_path}" 2>/dev/null || \
        fail "origin/$branch does not contain the current Ubuntu deployment. Has its deployment PR been merged?"
done

if run_git show-ref --verify --quiet "refs/heads/$branch"; then
    run_git switch "$branch"
    run_git merge --ff-only "refs/remotes/origin/$branch"
else
    # A --single-branch clone has no tracking refspec for other branches. Avoid
    # --track here because Git can update the worktree before tracking setup
    # fails, leaving a partially switched checkout.
    run_git switch --no-track -c "$branch" "refs/remotes/origin/$branch"
fi

commit_sha="$(run_git rev-parse HEAD)"
remote_sha="$(run_git rev-parse "refs/remotes/origin/$branch")"
[[ "$commit_sha" == "$remote_sha" ]] || fail "Local $branch contains commits not present on origin/$branch; refusing to deploy it."

short_sha="${commit_sha:0:12}"
app_version="git-$short_sha"
image_tag="cost-calculator:$app_version"
env_file="$project_root/.env"
temporary_env="$(mktemp "$project_root/.env.update.XXXXXX")"
cleanup() {
    [[ -z "${temporary_env:-}" ]] || rm -f -- "$temporary_env"
}
trap cleanup EXIT

# Store the generated release identity so Compose, verify.sh, rollback.sh, and
# later administrative commands all agree about the selected application image.
awk -v app_version="$app_version" -v image_tag="$image_tag" '
    substr($0, 1, 12) == "APP_VERSION=" {
        if (!version_written) print "APP_VERSION=" app_version
        version_written = 1
        next
    }
    substr($0, 1, 15) == "COST_APP_IMAGE=" {
        if (!image_written) print "COST_APP_IMAGE=" image_tag
        image_written = 1
        next
    }
    { print }
    END {
        if (!version_written) print "APP_VERSION=" app_version
        if (!image_written) print "COST_APP_IMAGE=" image_tag
    }
' "$env_file" > "$temporary_env"
chown --reference="$env_file" "$temporary_env"
chmod --reference="$env_file" "$temporary_env"
mv -f -- "$temporary_env" "$env_file"
temporary_env=""

log "Deploying origin/$branch at $commit_sha as $image_tag"
bash "$project_root/deployment/ubuntu/install.sh"
bash "$project_root/deployment/ubuntu/verify.sh"

log "Update completed"
printf 'Branch: %s\nCommit: %s\nApplication image: %s\n' "$branch" "$commit_sha" "$image_tag"
