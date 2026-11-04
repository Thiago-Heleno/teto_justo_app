BEGIN;

ALTER TABLE dispositivo_push
    DROP CONSTRAINT dispositivo_push_plataforma_check;

ALTER TABLE dispositivo_push
    ADD CONSTRAINT dispositivo_push_plataforma_check
    CHECK (plataforma IN ('android', 'ios', 'web'));

COMMIT;
