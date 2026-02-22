#!/usr/bin/env bash
# Usage: bash scripts/release.sh <tag>
# Example: bash scripts/release.sh 1.2.0
#
# Required env vars:
#   DOCKER_HUB_USER  – your Docker Hub username
#
# Optional env vars:
#   KUBE_NAMESPACE   – target namespace (default: kreaimggen-prod)
#   SKIP_PUSH        – set to 1 to build/tag without pushing (local test)
#   SKIP_DEPLOY      – set to 1 to push without deploying to k8s

set -euo pipefail

TAG=${1:?Usage: release.sh <tag>}
DOCKER_HUB_USER=${DOCKER_HUB_USER:?set DOCKER_HUB_USER env var}
KUBE_NAMESPACE=${KUBE_NAMESPACE:-kreaimggen-prod}
SKIP_PUSH=${SKIP_PUSH:-0}
SKIP_DEPLOY=${SKIP_DEPLOY:-0}

SERVICES=(backend worker frontend)

# ── 1. Build ─────────────────────────────────────────────────────────────────
echo ""
echo "==> [1/4] Building images (tag: $TAG)"
DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 docker compose build

# ── 2. Tag ───────────────────────────────────────────────────────────────────
echo ""
echo "==> [2/4] Re-tagging for Docker Hub ($DOCKER_HUB_USER)"
for svc in "${SERVICES[@]}"; do
  docker tag kreaimggen-$svc:latest $DOCKER_HUB_USER/kreaimggen-$svc:$TAG
  docker tag kreaimggen-$svc:latest $DOCKER_HUB_USER/kreaimggen-$svc:latest
  echo "    kreaimggen-$svc → $DOCKER_HUB_USER/kreaimggen-$svc:$TAG"
done

# ── 3. Push ──────────────────────────────────────────────────────────────────
if [ "$SKIP_PUSH" = "1" ]; then
  echo ""
  echo "==> [3/4] Skipping push (SKIP_PUSH=1)"
else
  echo ""
  echo "==> [3/4] Pushing to Docker Hub"
  for svc in "${SERVICES[@]}"; do
    docker push $DOCKER_HUB_USER/kreaimggen-$svc:$TAG
    docker push $DOCKER_HUB_USER/kreaimggen-$svc:latest
  done
fi

# ── 4. Deploy ────────────────────────────────────────────────────────────────
if [ "$SKIP_DEPLOY" = "1" ]; then
  echo ""
  echo "==> [4/4] Skipping deploy (SKIP_DEPLOY=1)"
else
  echo ""
  echo "==> [4/4] Rendering Helm chart → kustomize/base/all.yaml"
  helm template kreaimggen ./helm/kreaimggen \
    --namespace "$KUBE_NAMESPACE" \
    --set global.imageRegistry="docker.io/$DOCKER_HUB_USER/" \
    --set backend.image.tag="$TAG" \
    --set worker.image.tag="$TAG" \
    --set frontend.image.tag="$TAG" \
    > kustomize/base/all.yaml

  echo ""
  echo "==> Applying kustomize production overlay"
  kubectl apply -k kustomize/overlays/production

  echo ""
  echo "==> Waiting for rollout (timeout 5 min)"
  kubectl rollout status deployment \
    --namespace "$KUBE_NAMESPACE" \
    --timeout=300s
fi

echo ""
echo "✓ Release $TAG complete."
