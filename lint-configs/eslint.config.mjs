// coding-standards baseline ESLint config (flat config format).
// Consumer repos override by placing their own eslint.config.mjs at root.
//
// Plugins baked into the Docker image:
//   - @eslint/js:  current ESLint recommended rules
//   - typescript-eslint: TypeScript parser and recommended rules
//   - unicorn:     best practices, filename conventions, modernization
//   - security:    injection, unsafe eval, prototype pollution
//   - sonarjs:     complexity, duplication, code smells
//   - @eslint-react: React, hooks, DOM, and web API safety
//   - i18next:     internationalization (hardcoded strings in JSX)

import js from "@eslint/js";
import eslintReact from "@eslint-react/eslint-plugin";
import globals from "globals";
import unicorn from "eslint-plugin-unicorn";
import security from "eslint-plugin-security";
import sonarjs from "eslint-plugin-sonarjs";
import importX from "eslint-plugin-import-x";
import jsxA11y from "eslint-plugin-jsx-a11y-x";
import testingLibrary from "eslint-plugin-testing-library";
import i18next from "eslint-plugin-i18next";
import tseslint from "typescript-eslint";

export default [
  js.configs.recommended,
  {
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
    },
  },
  ...tseslint.configs.recommended.map((config) => ({
    ...config,
    files: ["**/*.ts", "**/*.tsx"],
  })),
  {
    plugins: {
      unicorn,
      security,
      sonarjs,
      "import-x": importX,
    },
    rules: {
      // ── Filename conventions ──────────────────────────────
      "unicorn/filename-case": ["warn", { cases: { kebabCase: true, pascalCase: true } }],

      // ── Security ──────────────────────────────────────────
      "security/detect-eval-with-expression": "error",
      "security/detect-non-literal-fs-filename": "warn",
      "security/detect-non-literal-regexp": "warn",
      "security/detect-object-injection": "warn",
      "security/detect-possible-timing-attacks": "warn",
      "security/detect-unsafe-regex": "error",

      // ── Best practices (unicorn) ──────────────────────────
      "unicorn/no-for-each": "warn",
      "unicorn/prefer-node-protocol": "error",
      "unicorn/prefer-module": "warn",
      "unicorn/no-useless-undefined": "warn",
      "unicorn/prefer-string-replace-all": "warn",
      "unicorn/prefer-at": "warn",

      // ── Import hygiene ────────────────────────────────────
      "import-x/no-cycle": ["warn", { maxDepth: 2 }], // depth 2 balances coverage vs performance on large codebases
      "import-x/no-self-import": "error",
      "import-x/no-mutable-exports": "error",
      "import-x/no-extraneous-dependencies": "warn",

      // ── Code smells (sonarjs) ─────────────────────────────
      "sonarjs/no-duplicate-string": ["warn", { threshold: 4 }],
      "sonarjs/cognitive-complexity": ["warn", 15],
      "sonarjs/no-identical-functions": "warn",
      "sonarjs/no-collapsible-if": "warn",
      "sonarjs/prefer-single-boolean-return": "warn",
    },
  },
  // ── React/JSX (auto-activates for .jsx/.tsx files) ───────
  {
    files: ["**/*.jsx", "**/*.tsx"],
    languageOptions: {
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    plugins: {
      ...eslintReact.configs.recommended.plugins,
      "jsx-a11y": jsxA11y,
      i18next,
    },
    settings: eslintReact.configs.recommended.settings,
    rules: {
      ...eslintReact.configs.recommended.rules,

      // React DOM safety
      "@eslint-react/dom-no-unsafe-target-blank": "error",
      "@eslint-react/dom-no-dangerously-set-innerhtml": "warn",

      // Accessibility
      "jsx-a11y/alt-text": "warn",
      "jsx-a11y/anchor-is-valid": "warn",
      "jsx-a11y/click-events-have-key-events": "warn",
      "jsx-a11y/no-autofocus": "warn",
      "jsx-a11y/label-has-associated-control": "warn",

      // i18n — catch hardcoded strings early (painful to retrofit)
      "i18next/no-literal-string": "warn",
    },
  },
  // ── Test files: testing-library + jest rules ───────────────
  {
    files: ["**/*.test.*", "**/*.spec.*", "**/test/**", "**/tests/**"],
    plugins: {
      "testing-library": testingLibrary,
    },
    rules: {
      // Testing Library — catches flaky async test bugs
      "testing-library/await-async-queries": "error",
      "testing-library/no-await-sync-queries": "error",
      "testing-library/no-wait-for-multiple-assertions": "warn",
      "testing-library/prefer-screen-queries": "warn",
      "testing-library/no-unnecessary-act": "warn",
    },
  },
];
