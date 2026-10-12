#!/usr/bin/env bash
# Stage 1: mondo-international.owl(.gz) -> mondo-international.obo.gz
# Prefer .owl.gz when both the uncompressed and gzipped inputs exist.
# ROBOT cannot reliably read gzipped inputs, so .gz is decompressed to a temp file.
# ROBOT can write gzipped OBO directly.
set -euo pipefail

owl_gz=mondo-international.owl.gz
owl_plain=mondo-international.owl
obo_gz=mondo-international.obo.gz
rule=preprocess_labels_for_obo.ru

if [[ -f ${owl_gz} ]]; then
  owl_src=${owl_gz}
elif [[ -f ${owl_plain} ]]; then
  owl_src=${owl_plain}
else
  echo "error: neither ${owl_gz} nor ${owl_plain} found" >&2
  exit 1
fi

tmp=
cleanup() {
  if [[ -n ${tmp} && -e ${tmp} ]]; then
    rm -f "${tmp}"
  fi
}
trap cleanup EXIT

if [[ ${owl_src} == *.gz ]]; then
  tmp=$(mktemp "./.tmp-mondo-international.owl.XXXXXX")
  echo "Decompressing ${owl_src} -> ${tmp}" >&2
  gzip -dc "${owl_src}" > "${tmp}"
  # mktemp creates mode 0600; the bind-mounted file must be readable inside Docker.
  chmod a+r "${tmp}"
  owl_input=${tmp}
else
  owl_input=${owl_src}
fi

docker pull obolibrary/robot
set +e
docker run \
  -v "$PWD:/work" \
  -w /work \
  -e JAVA_TOOL_OPTIONS="-Xmx16G -Dfile.encoding=UTF-8" \
  --rm \
  -i \
  obolibrary/robot \
  robot query \
  --input "${owl_input}" \
  --update "${rule}" \
  --format obo \
  --output "${obo_gz}"
docker_exit=$?
set -e
if [[ ${docker_exit} -ne 0 ]]; then
  echo "error: docker robot query failed (exit ${docker_exit})" >&2
  exit "${docker_exit}"
fi

echo "Wrote ${obo_gz}" >&2
