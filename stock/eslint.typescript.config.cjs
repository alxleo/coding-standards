const { defineConfig } = require("eslint/config");
const typescript = require("@typescript-eslint/eslint-plugin");

module.exports = defineConfig([
  ...require("./eslint.config.cjs"),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [typescript.configs["flat/recommended"]],
  },
]);
