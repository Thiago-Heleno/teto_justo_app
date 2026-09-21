BEGIN;

-- pontuacao passa a ser obrigatoria: e a pontuacao-base da tarefa (10, 20,
-- 30 ou 40, conforme CK_Tarefa_pontuacao), independente de peso/dificuldade,
-- que serve apenas para dividir o trabalho entre os responsaveis.
ALTER TABLE tarefa
    ALTER COLUMN pontuacao SET NOT NULL;

COMMIT;
