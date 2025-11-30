#!/bin/bash

echo "ÔøΩÔøΩ FMCG Intelligence Hub - Setup Script"
echo "========================================"

# Check if .env exists
if [ -f .env ]; then
    echo "‚ö†Ô∏è  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 1
    fi
fi

# Copy .env.example to .env
cp .env.example .env
echo "‚úÖ Created .env file from template"

# Generate secret key
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32)
sed -i "s/your-secret-key-here/$SECRET_KEY/" .env
echo "‚úÖ Generated SECRET_KEY"

echo ""
echo "‚ö†Ô∏è  IMPORTANT: Update the following in .env file:"
echo "   - GOOGLE_API_KEY (get from: https://console.cloud.google.com/apis/credentials)"
echo ""
echo "Ì≥ù Run: nano .env  (or use your preferred editor)"
echo ""
echo "Ìæâ Setup complete! Next steps:"
echo "   1. Edit .env with your API keys"
echo "   2. Run: docker-compose up -d"
