-- Lomimail registration profile fields.
-- Review and apply only to the intended database.
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS country VARCHAR(100),
    ADD COLUMN IF NOT EXISTS state VARCHAR(100),
    ADD COLUMN IF NOT EXISTS lga VARCHAR(100),
    ADD COLUMN IF NOT EXISTS city VARCHAR(100),
    ADD COLUMN IF NOT EXISTS primary_community_1 VARCHAR(150),
    ADD COLUMN IF NOT EXISTS primary_community_2 VARCHAR(150),
    ADD COLUMN IF NOT EXISTS profile_picture_url VARCHAR(500),
    ADD COLUMN IF NOT EXISTS additional_image_url VARCHAR(500);
