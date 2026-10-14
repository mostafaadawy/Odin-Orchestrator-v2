#!/bin/bash
# P5-3(a) / P9-3 / PP-6: bring ALL paper and program material into v2 (COPY; the sources are only removed in Phase 9 with
# the owner's yes). Paper v1 and paper v2 are two separate folders. The frozen paper-v1 state is copied byte-for-byte
# and re-verified against the paper-v1 fingerprint FROM INSIDE v2.
set -e
W=/Users/mostafaadawy/Desktop/AiAgentWorkSpace; V2=$W/Odin-Orchestrator-v2; R=$V2/research; S=$W/odin-v2-staging
mkdir -p $R/paper-v1/frozen-state $R/paper-v2 $R/phase4 $R/consolidation $R/isolated-research $V2/docs/program
FP=$S/research/paper-v1-fingerprint/paper_v1_sha256.txt
# 1) frozen paper-v1 state: exactly the fingerprinted files, same relative paths
awk '{ $1=""; sub(/^ +/, ""); print }' $FP > /tmp/pv1_files.txt
(cd $W && tar -cf - -T /tmp/pv1_files.txt) | (cd $R/paper-v1/frozen-state && tar -xf -)
cp -R $S/research/paper-v1-fingerprint $S/research/paper-v1-submission $R/paper-v1/
cp $S/research/PAPER_V1_ACCURACY_CHECK.md $R/paper-v1/
cp -R $S/research/v1-restore-patch $S/research/v1-rules-check $R/paper-v1/
# 2) paper v2 (draft, provisional) + the verification reports
cp -R $S/research/paper-v2/. $R/paper-v2/
cp -R $S/research/verification $R/
[ -d $S/research/phase4 ] && cp -R $S/research/phase4/. $R/phase4/
# 3) Jev research (scripts, data, results) — model weights and feature caches are re-creatable (copied in change set c)
(cd $W/Odin-Consolidated/_research/phase4 && tar --exclude=./models --exclude=./cache -cf - .) | (cd $R/phase4 && tar -xf -)
# 4) consolidation research + evidence, isolated research, resulted papers
(cd $W/Odin-Consolidated/_research && tar -cf - rescued results deliverables promotion DECISIONS.md 0*.md) | (cd $R/consolidation && tar -xf -)
(cd $W/Odin-Consolidated && tar --exclude='./_consolidation/pc5_electron/node_modules' -cf - _consolidation/results CHANGELOG.md) | (cd $R/consolidation && tar -xf -)
(cd $W/Odin-Isolated/_research && tar -cf - .) | (cd $R/isolated-research && tar -xf -)
mkdir -p "$R/resulted-papers-and-documents"; cp -R "$W/Resulted Papers and Documents/." "$R/resulted-papers-and-documents/"
# 5) program documents (tracker, inventory, decisions, phase reports)
(cd $S && tar --exclude=./research -cf - .) | (cd $V2/docs/program && tar -xf -)
# 6) verify the frozen paper-v1 state from inside v2
cd $R/paper-v1/frozen-state && shasum -a 256 --quiet -c $R/paper-v1/paper-v1-fingerprint/paper_v1_sha256.txt && echo "PAPER-V1 FROZEN COPY IN V2: OK ($(wc -l < /tmp/pv1_files.txt) files)"
du -sh $R $V2/docs/program
