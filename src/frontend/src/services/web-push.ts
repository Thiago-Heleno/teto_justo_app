// Web Push só existe na versão web (web-push.web.ts); no app nativo nada é feito.
export const webPushDisponivel = () => false;
export const webPushAtivo = async () => false;
export const ativarWebPush = async () => false;
export const removerWebPush = async () => {};
