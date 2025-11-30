# Security Guidelines

## Environment Variables

**NEVER commit `.env` files to version control!**

### Setup Instructions

1. Copy `.env.example` to `.env`:
```bash
   cp .env.example .env
```

2. Update `.env` with your actual credentials:
   - Get Google API key from: https://console.cloud.google.com/apis/credentials
   - Generate secret key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

3. Verify `.env` is in `.gitignore`

### What to Do If You Exposed API Keys

1. **Immediately revoke the exposed key**
   - Go to Google Cloud Console
   - Navigate to APIs & Services > Credentials
   - Delete or disable the exposed key

2. **Generate a new API key**

3. **Clean Git history** (if committed):
```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all
```

4. **Force push to GitHub**:
```bash
   git push origin --force --all
```

### Best Practices

- ✅ Use environment variables for all secrets
- ✅ Keep `.env.example` with dummy values
- ✅ Add `.env` to `.gitignore`
- ✅ Use secret management tools in production (AWS Secrets Manager, Google Secret Manager)
- ✅ Rotate API keys regularly
- ❌ Never hardcode API keys in source code
- ❌ Never commit `.env` files
- ❌ Never share API keys in chat/email
