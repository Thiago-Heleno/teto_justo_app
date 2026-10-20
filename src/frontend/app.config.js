module.exports = ({ config }) => ({
  ...config,
  android: {
    ...config.android,
    ...(process.env.GOOGLE_SERVICES_JSON && {
      googleServicesFile: process.env.GOOGLE_SERVICES_JSON,
    }),
  },
});
