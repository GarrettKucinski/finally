-- Default seed data for FinAlly
-- Inserts the default user, profile ($10k cash), and 10 watchlist tickers.
-- All statements use ON CONFLICT DO NOTHING for idempotency.

-- Default user (fixed UUID for single-user v1)
INSERT INTO users (id, email, password)
VALUES ('00000000-0000-0000-0000-000000000001', 'default@finally.app', 'not-used')
ON CONFLICT DO NOTHING;

-- Default user profile with $10,000 starting cash
INSERT INTO users_profile (user_id, cash_balance)
VALUES ('00000000-0000-0000-0000-000000000001', 10000.0)
ON CONFLICT DO NOTHING;

-- Default watchlist: 10 tickers
INSERT INTO watchlist (user_id, ticker) VALUES ('00000000-0000-0000-0000-000000000001', 'AAPL') ON CONFLICT DO NOTHING;
INSERT INTO watchlist (user_id, ticker) VALUES ('00000000-0000-0000-0000-000000000001', 'GOOGL') ON CONFLICT DO NOTHING;
INSERT INTO watchlist (user_id, ticker) VALUES ('00000000-0000-0000-0000-000000000001', 'MSFT') ON CONFLICT DO NOTHING;
INSERT INTO watchlist (user_id, ticker) VALUES ('00000000-0000-0000-0000-000000000001', 'AMZN') ON CONFLICT DO NOTHING;
INSERT INTO watchlist (user_id, ticker) VALUES ('00000000-0000-0000-0000-000000000001', 'TSLA') ON CONFLICT DO NOTHING;
INSERT INTO watchlist (user_id, ticker) VALUES ('00000000-0000-0000-0000-000000000001', 'NVDA') ON CONFLICT DO NOTHING;
INSERT INTO watchlist (user_id, ticker) VALUES ('00000000-0000-0000-0000-000000000001', 'META') ON CONFLICT DO NOTHING;
INSERT INTO watchlist (user_id, ticker) VALUES ('00000000-0000-0000-0000-000000000001', 'JPM') ON CONFLICT DO NOTHING;
INSERT INTO watchlist (user_id, ticker) VALUES ('00000000-0000-0000-0000-000000000001', 'V') ON CONFLICT DO NOTHING;
INSERT INTO watchlist (user_id, ticker) VALUES ('00000000-0000-0000-0000-000000000001', 'NFLX') ON CONFLICT DO NOTHING;
