#!/bin/bash
# Export pitch deck to various formats

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DECK_FILE="$PROJECT_ROOT/PITCH_DECK.md"

echo "════════════════════════════════════════════════════════════════"
echo "  DAC AGENT - PITCH DECK EXPORT UTILITY"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if deck file exists
if [ ! -f "$DECK_FILE" ]; then
    echo "❌ Error: PITCH_DECK.md not found at $DECK_FILE"
    exit 1
fi

echo "📄 Found pitch deck: $DECK_FILE"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Export options
echo "Select export format:"
echo "  1) PowerPoint (.pptx) - via Marp"
echo "  2) PDF - via Marp"
echo "  3) HTML (web presentation) - via Marp"
echo "  4) PDF - via Pandoc"
echo "  5) PowerPoint (.pptx) - via Pandoc"
echo "  6) All formats"
echo ""
read -p "Enter choice [1-6]: " choice

case $choice in
    1)
        if command_exists marp; then
            echo "🔄 Exporting to PowerPoint..."
            marp "$DECK_FILE" -o "$PROJECT_ROOT/PITCH_DECK.pptx"
            echo "✅ Created: PITCH_DECK.pptx"
        else
            echo "❌ Marp not found. Install with: npm install -g @marp-team/marp-cli"
            exit 1
        fi
        ;;
    2)
        if command_exists marp; then
            echo "🔄 Exporting to PDF..."
            marp "$DECK_FILE" -o "$PROJECT_ROOT/PITCH_DECK.pdf"
            echo "✅ Created: PITCH_DECK.pdf"
        else
            echo "❌ Marp not found. Install with: npm install -g @marp-team/marp-cli"
            exit 1
        fi
        ;;
    3)
        if command_exists marp; then
            echo "🔄 Exporting to HTML..."
            marp "$DECK_FILE" -o "$PROJECT_ROOT/PITCH_DECK.html"
            echo "✅ Created: PITCH_DECK.html"
            echo "   Open with: open PITCH_DECK.html"
        else
            echo "❌ Marp not found. Install with: npm install -g @marp-team/marp-cli"
            exit 1
        fi
        ;;
    4)
        if command_exists pandoc; then
            echo "🔄 Exporting to PDF via Pandoc..."
            pandoc "$DECK_FILE" -o "$PROJECT_ROOT/PITCH_DECK_pandoc.pdf"
            echo "✅ Created: PITCH_DECK_pandoc.pdf"
        else
            echo "❌ Pandoc not found. Install with:"
            echo "   macOS: brew install pandoc"
            echo "   Ubuntu: sudo apt install pandoc"
            exit 1
        fi
        ;;
    5)
        if command_exists pandoc; then
            echo "🔄 Exporting to PowerPoint via Pandoc..."
            pandoc "$DECK_FILE" -o "$PROJECT_ROOT/PITCH_DECK_pandoc.pptx"
            echo "✅ Created: PITCH_DECK_pandoc.pptx"
        else
            echo "❌ Pandoc not found. Install with:"
            echo "   macOS: brew install pandoc"
            echo "   Ubuntu: sudo apt install pandoc"
            exit 1
        fi
        ;;
    6)
        echo "🔄 Exporting to all formats..."

        if command_exists marp; then
            echo "  → PowerPoint (Marp)..."
            marp "$DECK_FILE" -o "$PROJECT_ROOT/PITCH_DECK.pptx"

            echo "  → PDF (Marp)..."
            marp "$DECK_FILE" -o "$PROJECT_ROOT/PITCH_DECK.pdf"

            echo "  → HTML (Marp)..."
            marp "$DECK_FILE" -o "$PROJECT_ROOT/PITCH_DECK.html"

            echo "✅ Marp exports complete"
        else
            echo "⚠️  Marp not found, skipping Marp exports"
        fi

        if command_exists pandoc; then
            echo "  → PDF (Pandoc)..."
            pandoc "$DECK_FILE" -o "$PROJECT_ROOT/PITCH_DECK_pandoc.pdf"

            echo "  → PowerPoint (Pandoc)..."
            pandoc "$DECK_FILE" -o "$PROJECT_ROOT/PITCH_DECK_pandoc.pptx"

            echo "✅ Pandoc exports complete"
        else
            echo "⚠️  Pandoc not found, skipping Pandoc exports"
        fi

        if ! command_exists marp && ! command_exists pandoc; then
            echo ""
            echo "❌ No export tools found!"
            echo ""
            echo "Install at least one:"
            echo "  • Marp: npm install -g @marp-team/marp-cli"
            echo "  • Pandoc: brew install pandoc (macOS) or apt install pandoc (Ubuntu)"
            exit 1
        fi
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ Export complete!"
echo ""
echo "Next steps:"
echo "  1. Review the exported file"
echo "  2. Add visuals/diagrams (use Figma, Excalidraw)"
echo "  3. Customize for your audience"
echo "  4. Practice with: python demo_dashboard.py"
echo "════════════════════════════════════════════════════════════════"
