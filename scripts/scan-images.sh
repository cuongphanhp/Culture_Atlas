#!/usr/bin/env bash
# Quét lỗ hổng (CVE) các image của app bằng Trivy (docker-production-skill.md mục 20).
# Không gắn docker.sock vào container: xuất image ra file tar (hoặc filesystem) rồi cho Trivy đọc.
#   scripts/scan-images.sh            # tổng hợp HIGH/CRITICAL của mọi image
#   scripts/scan-images.sh --detail   # in bảng chi tiết
# object-storage (MinIO) có ngoại lệ đã ghi nhận: docs/security-exceptions.md
set -euo pipefail
TAG="${IMAGE_TAG:-local}"
IMAGES=(culture-atlas/web culture-atlas/backend culture-atlas/ai-local culture-atlas/object-storage)
# Layer của image gốc MinIO (UBI) Trivy không đọc được ở dạng tar → quét filesystem của container
ROOTFS_IMAGES=" culture-atlas/object-storage "
TRIVY="${TRIVY_IMAGE:-public.ecr.aws/aquasecurity/trivy:latest}"
WORK="$(mktemp -d)"
trap 'chmod -R u+w "${WORK:?}" 2>/dev/null; rm -rf "${WORK:?}"' EXIT
FORMAT=json
[ "${1:-}" = "--detail" ] && FORMAT=table

summarize() {
  python3 -c '
import json, sys
name = sys.argv[1]
d = json.load(sys.stdin)
vulns = {(r["Target"], v["PkgName"], v["VulnerabilityID"]): v for r in d.get("Results", []) for v in (r.get("Vulnerabilities") or [])}.values()
crit = sum(v["Severity"] == "CRITICAL" for v in vulns)
high = sum(v["Severity"] == "HIGH" for v in vulns)
fixable = sum(bool(v.get("FixedVersion")) for v in vulns)
pkgs = sorted({v["PkgName"] for v in vulns})
shown = ", ".join(pkgs[:8]) + (" …" if len(pkgs) > 8 else "")
print(f"{name:15} CRITICAL={crit:<3} HIGH={high:<3} có bản vá={fixable:<3} gói: {shown}")
' "$1"
}

for img in "${IMAGES[@]}"; do
  name="$(basename "$img")"
  docker image inspect "$img:$TAG" >/dev/null 2>&1 || { echo "$name: chưa build ($img:$TAG) — bỏ qua"; continue; }
  if [[ "$ROOTFS_IMAGES" == *" $img "* ]]; then
    mkdir -p "$WORK/$name"
    cid="$(docker create "$img:$TAG")"
    docker export "$cid" | tar -x -C "$WORK/$name" 2>/dev/null || true
    docker rm "$cid" >/dev/null
    out="$(docker run --rm -v "$WORK/$name":/fs:ro -v trivy-cache:/root/.cache "$TRIVY" rootfs --quiet \
            --scanners vuln --severity HIGH,CRITICAL --format "$FORMAT" /fs)"
    chmod -R u+w "${WORK:?}/${name:?}" 2>/dev/null; rm -rf "${WORK:?}/${name:?}"
  else
    docker save "$img:$TAG" -o "$WORK/$name.tar"
    out="$(docker run --rm -v "$WORK":/scan:ro -v trivy-cache:/root/.cache "$TRIVY" image --quiet \
            --scanners vuln --severity HIGH,CRITICAL --format "$FORMAT" --input "/scan/$name.tar")"
    rm -f "${WORK:?}/${name:?}.tar"
  fi
  if [ "$FORMAT" = json ]; then echo "$out" | summarize "$name"; else echo "== $img:$TAG"; echo "$out"; fi
done
