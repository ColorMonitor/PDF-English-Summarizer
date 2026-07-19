#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-/www/wwwroot/uscai}"
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$TARGET/495c398d973933b6238f79da1370b759_venv"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$TARGET/backups/pdf_summarizer_$STAMP"

if [[ ! -f "$TARGET/manage.py" || ! -x "$VENV/bin/python3" ]]; then
  echo "USC Django project or virtual environment not found: $TARGET" >&2
  exit 1
fi

if [[ ! -f "$TARGET/certs/unionsupremecourt-ca-bundle.pem" ]]; then
  echo "Missing CA bundle: $TARGET/certs/unionsupremecourt-ca-bundle.pem" >&2
  exit 1
fi

mkdir -p "$BACKUP/apps/publications" "$BACKUP/templates/content"
cp "$TARGET/apps/publications/urls.py" "$BACKUP/apps/publications/urls.py"
cp "$TARGET/templates/content/detail.html" "$BACKUP/templates/content/detail.html"
cp "$TARGET/requirements.txt" "$BACKUP/requirements.txt"

install -D -m 0644 "$SOURCE/apps/publications/summarizer.py" "$TARGET/apps/publications/summarizer.py"
install -D -m 0644 "$SOURCE/apps/publications/summarizer_views.py" "$TARGET/apps/publications/summarizer_views.py"
install -D -m 0644 "$SOURCE/templates/content/project_summarize.html" "$TARGET/templates/content/project_summarize.html"
install -D -m 0644 "$SOURCE/static/publications/project_summarizer.css" "$TARGET/static/publications/project_summarizer.css"
install -D -m 0644 "$SOURCE/static/publications/project_summarizer.js" "$TARGET/static/publications/project_summarizer.js"

"$VENV/bin/python3" "$SOURCE/patch_existing.py" "$TARGET"
"$VENV/bin/pip" install "pypdf==4.3.1"

cd "$TARGET"
"$VENV/bin/python3" manage.py check
"$VENV/bin/python3" manage.py collectstatic --noinput

echo
echo "Deployment files installed. Backup: $BACKUP"
echo "Set BEAM_ENDPOINT_URL and BEAM_API_TOKEN in aaPanel, then restart the USC Python project."
