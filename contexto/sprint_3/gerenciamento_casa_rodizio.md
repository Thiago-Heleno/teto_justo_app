# Gerenciamento de casa e rodízio — revisão da versão 9

## Diagnóstico da versão recebida

A home responsiva já usa MotionPressable, DetalhesCasa e MoradoresCasa.
MoradoresCasa lista moradores e remove vínculos com confirmação exclusiva
para administrador. Os serviços listarMoradoresCasa e removerMoradorCasa
já existem e são preservados. Faltam edição/exclusão de casa, gerenciamento
completo das operações disponíveis de rodízio e consulta de regras por morador.
A criação de rodízio já existe na tela Criar; não é descartada.

## Alterações

* Home: somente dois links novos, sem remover código. 435 para 455 linhas.
* Stack raiz: registra gerenciar-casa e rotatividades sob token e casa ativa.
* gerenciar-casa: dados, edição de nome/endereço/fuso e exclusão confirmada.
Reutiliza MoradoresCasa para listagem/remoção e DetalhesCasa para foto/dados.
Não duplica o componente de moradores nem suas funções do serviço.
* casas-api: acrescenta CasaAtualizar, carregarCasa, atualizarCasa, excluirCasa.
As funções e o tipo MoradorCasa existentes permanecem intactos.
* rotatividade-api: novo CRUD de regras no padrão requisitar. tarefas-api
reexporta criação e tipo para preservar os imports da tela Criar.
* FormularioRotatividade: criação com participantes e dias, dificuldade,
prazo/tolerância e intervalo; edição somente dos campos suportados.
* useGerenciamentoCasa: consulta casa e identidade, verifica admin, evita
envio duplicado e cancela requisições ao sair da tela. Na tela da casa,
não consulta moradores novamente: essa consulta é feita por MoradoresCasa.
* Backend: listar\_rotatividades usa garantir\_acesso, permitindo dono e
moradores ativos. Criação/edição/exclusão continuam exigindo admin.

Admin é o usuário autenticado cujo ID corresponde a fk\_usuario\_id da casa,
seguindo os serviços de autorização atuais. A permissão visual não substitui
as verificações backend. 401 continua limpando a sessão pelo cliente comum.
422 exibe mensagens com o caminho do campo; 403 e 409 exibem a mensagem original.
Após 403 em escrita, a consulta de identidade precisa ser refeita antes de
liberar as ações novamente.

A edição da casa atualiza casaAtiva após a confirmação da API. Exclusão da
casa limpa a seleção e volta ao seletor. Não é implementada exclusão em cascata.
Foto continua disponível para consulta; upload de foto não é acrescentado.

## Limites do contrato de rodízio

PATCH permite apenas nome, descricao e ativa. Participantes/calendário/
dificuldade/tolerância são definidos na criação; a listagem nem retorna todos
esses campos. Não são enviados campos que o backend rejeita.
Rodízio com tarefas geradas retorna 409 na exclusão; é possível pausá-lo em
Editar. Não há migrations ou funções SQL novas.

## Validações desta revisão

* TypeScript sem erros e lint integral sem erros/warnings.
* 7 testes de contrato do serviço, 43 de casas e 47 de autenticação/tarefas
passaram: 97 frontend. A suíte foi executada em America/Sao\_Paulo.
* 22 testes unitários backend de acesso, agendamento, schemas e autorização
passaram; banco simulado, sem gravações em banco real.
* Exportação web passou com as duas rotas novas e perfil existente preservado.
* Patch verificado contra a versão 9 original.



