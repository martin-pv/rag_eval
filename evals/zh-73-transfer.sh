#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SCRIPT_DIR/backend"
DEST="${1:-$SCRIPT_DIR/backend}"

echo "[ZH-73] Transferring Document Builder management command to: $DEST"

mkdir -p "$DEST/app_chatbot/management/commands"

cp "$SRC/app_chatbot/management/__init__.py" \
   "$DEST/app_chatbot/management/__init__.py"

cp "$SRC/app_chatbot/management/commands/__init__.py" \
   "$DEST/app_chatbot/management/commands/__init__.py"

cp "$SRC/app_chatbot/management/commands/create_doc_builder_assistant.py" \
   "$DEST/app_chatbot/management/commands/create_doc_builder_assistant.py"

echo "[ZH-73] Done. Run on the target machine:"
echo "  python manage.py create_doc_builder_assistant"
echo ""
echo "  Verify:"
echo "  python manage.py shell -c \\"
echo "    \"from app_chatbot.models import ChatAssistant; a = ChatAssistant.objects.get(name='Document Builder'); print(a.pk, a.description)\""
