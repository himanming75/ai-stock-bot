# Production Deployment Checklist

## Required before deployment

- [ ] Replace example domain
- [ ] Generate strong APP_SECRET_KEY
- [ ] Configure PostgreSQL
- [ ] Run database migrations
- [ ] Create verified database backup
- [ ] Install HTTPS certificate
- [ ] Configure firewall
- [ ] Enable CSRF protection
- [ ] Enable rate limiting
- [ ] Configure centralized logs
- [ ] Configure monitoring and alerts
- [ ] Test graceful shutdown
- [ ] Test restore in an isolated environment
- [ ] Verify Broker Write remains OFF
- [ ] Verify Order Submission remains OFF
- [ ] Verify Live Trading remains OFF

## Explicitly disabled in this release

- Stripe external charges
- Public production deployment
- Broker credential storage
- Broker write access
- Order submission
- Live trading
