BEGIN;

ALTER TABLE dispositivo_push
    DROP CONSTRAINT dispositivo_push_plataforma_check;

ALTER TABLE dispositivo_push
    ADD CONSTRAINT dispositivo_push_plataforma_check
    CHECK (plataforma IN ('android', 'ios', 'web'));

ALTER TABLE dispositivo_push
    ADD COLUMN endpoint TEXT,
    ADD COLUMN p256dh TEXT,
    ADD COLUMN auth TEXT;

ALTER TABLE dispositivo_push
    ALTER COLUMN token DROP NOT NULL;

CREATE UNIQUE INDEX uq_dispositivo_push_endpoint
    ON dispositivo_push (endpoint)
    WHERE endpoint IS NOT NULL;

ALTER TABLE dispositivo_push
    ADD CONSTRAINT dispositivo_push_formato_check CHECK (token IS NOT NULL);

COMMIT;
