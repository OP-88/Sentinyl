# Environment Setup Required

Before running the application, copy the environment templates to create your configuration files:

## Frontend (.env)

```bash
cd /home/marc/Verba-mvp/Sentinyl/sentinyl-overwatch
cp .env.example .env
```

The defaults should work for local development. The `.env` file is gitignored.

## Bridge (.env)

```bash
cd /home/marc/Verba-mvp/Sentinyl/sentinyl-overwatch/bridge
cp .env.example .env
```

The defaults should work for local development. The `.env` file is gitignored.

## Backend (.env)

The backend already has `.env.example`. If you don't have a `.env` file:

```bash
cd /home/marc/Verba-mvp/Sentinyl
cp .env.example .env
```

Make sure to add:
```
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

**Note**: All `.env` files are gitignored for security. Never commit them to version control!
