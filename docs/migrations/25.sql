BEGIN;

-- As três funções abaixo foram migradas para o backend Python (services/tarefa.py,
-- services/pertencer.py) e não têm mais nenhum chamador. Não há intenção de reverter
-- para elas em caso de bug -- qualquer correção futura acontece no Python.
DROP FUNCTION IF EXISTS registrar_conclusao_tarefa(
    UUID, UUID, INT, TIMESTAMPTZ, INT, INT, TIMESTAMP, TIMESTAMP, UUID
);
DROP FUNCTION IF EXISTS excluir_tarefa_sem_credito(UUID);
DROP FUNCTION IF EXISTS excluir_vinculo_sem_credito(UUID, UUID);

COMMIT;
