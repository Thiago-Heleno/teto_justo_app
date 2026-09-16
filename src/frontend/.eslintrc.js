module.exports = {
  extends: [
    "expo",
    "prettier",
    "plugin:security/recommended-legacy", // Ativa as regras de segurança (SAST)
  ],
  plugins: ["prettier", "security"],
  rules: {
    "prettier/prettier": "error",
    //regras de seguranca aqui se necessario.
  },
};
