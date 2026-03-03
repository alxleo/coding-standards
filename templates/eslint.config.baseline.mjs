// ESLint flat config baseline — bug catching + modern Node.js patterns.
// Style rules OFF — use Prettier for formatting.
// Adapted per-repo from templates/; not synced as-is.
import nodePlugin from "eslint-plugin-n";

export default [
  {
    files: ["**/*.js", "**/*.mjs"],
    plugins: {
      n: nodePlugin,
    },
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
    },
    rules: {
      // === ERRORS (likely bugs) ===
      "no-undef": "error",
      "no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
      "no-unreachable": "error",
      "no-dupe-keys": "error",
      "no-duplicate-case": "error",
      "no-constant-condition": "error",
      "no-fallthrough": "error",
      "use-isnan": "error",
      "valid-typeof": "error",
      "no-self-assign": "error",
      "no-self-compare": "error",
      "no-template-curly-in-string": "warn",

      // === ASYNC BUGS ===
      "require-await": "error",
      "no-async-promise-executor": "error",
      "no-await-in-loop": "warn",
      "prefer-promise-reject-errors": "error",

      // === ERROR HANDLING ===
      "no-throw-literal": "error",
      "no-useless-catch": "error",

      // === LOGIC ERRORS ===
      eqeqeq: ["error", "always"],
      "no-cond-assign": "error",
      "no-unsafe-negation": "error",

      // === NODE.JS MODERN PATTERNS ===
      "n/no-deprecated-api": "error",
      "n/prefer-promises/fs": "error",
      "n/prefer-promises/dns": "error",
      "n/no-callback-literal": "error",
      "n/handle-callback-err": "error",
      "n/no-path-concat": "error",
    },
  },
  {
    files: ["**/tests/**/*.js", "**/*.test.js", "**/*.test.mjs"],
    rules: {
      "no-unused-vars": "off",
    },
  },
];
