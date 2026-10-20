-- LOMINII: additive Lomimail identity migration.
-- Review and apply explicitly to the intended PostgreSQL database.
-- Existing accounts remain valid; new identity fields initially allow NULL.

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS lomimail_address VARCHAR(255),
    ADD COLUMN IF NOT EXISTS lomimail_uid VARCHAR(20),
    ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS lomimail_handshake_at TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS lomimail_startrow SMALLINT NULL;

-- Case-insensitive address uniqueness, excluding legacy NULL values.
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_lomimail_address_ci
    ON public.users (LOWER(lomimail_address))
    WHERE lomimail_address IS NOT NULL;

-- A phone-derived uID must belong to at most one account.
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_lomimail_uid
    ON public.users (lomimail_uid)
    WHERE lomimail_uid IS NOT NULL;
