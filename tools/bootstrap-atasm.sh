#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
revision=46be895a4312205dbcc4cf7a4a6721d72219d711
if [ ! -d .tools/.git ]; then
    if [ -e .tools ]; then
        echo '.tools exists but is not an ATasm checkout; move it aside first.' >&2
        exit 1
    fi
    git clone https://github.com/CycoPH/atasm.git .tools
    git -C .tools checkout --detach "$revision"
fi
actual=$(git -C .tools rev-parse HEAD)
[ "$actual" = "$revision" ] || { echo 'Unexpected ATasm revision in .tools' >&2; exit 1; }
[ -z "$(git -C .tools status --porcelain --untracked-files=no)" ] || {
    echo 'ATasm source has local modifications; refusing to build' >&2; exit 1;
}
make -C .tools/src -j2 > .tools/build.log 2>&1 || {
    cat .tools/build.log >&2; exit 1;
}
.tools/src/atasm 2>&1 | head -1
