// coding-standards baseline ESLint config (flat config format).
// Consumer repos override by placing their own eslint.config.mjs at root.
//
// Plugins baked into the Docker image (cupcake + our installs):
//   - unicorn:     best practices, filename conventions, modernization
//   - security:    injection, unsafe eval, prototype pollution
//   - sonarjs:     complexity, duplication, code smells
//   - react:       React-specific rules
//   - react-hooks: hooks rules (exhaustive-deps)
//   - jsx-a11y:    accessibility for JSX
//   - jest:        test quality
//   - i18next:     internationalization (hardcoded strings in JSX)

import unicorn from "eslint-plugin-unicorn";
import security from "eslint-plugin-security";
import sonarjs from "eslint-plugin-sonarjs";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import jsxA11y from "eslint-plugin-jsx-a11y";
import importPlugin from "eslint-plugin-import";
import testingLibrary from "eslint-plugin-testing-library";
import i18next from "eslint-plugin-i18next";

export default [
  {
    plugins: {
      unicorn,
      security,
      sonarjs,
      import: importPlugin,
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
      "unicorn/no-array-for-each": "warn",
      "unicorn/prefer-node-protocol": "error",
      "unicorn/prefer-module": "warn",
      "unicorn/no-useless-undefined": "warn",
      "unicorn/prefer-string-replace-all": "warn",
      "unicorn/prefer-at": "warn",

      // ── Import hygiene (already in cupcake) ─────────────────
      "import/no-cycle": ["warn", { maxDepth: 2 }], // depth 2 balances coverage vs performance on large codebases
      "import/no-self-import": "error",
      "import/no-mutable-exports": "error",
      "import/no-extraneous-dependencies": "warn",

      // ── Code smells (sonarjs) ─────────────────────────────
      "sonarjs/no-duplicate-string": ["warn", { threshold: 4 }],
      "sonarjs/cognitive-complexity": ["warn", 15],
      "sonarjs/no-identical-functions": "warn",
      "sonarjs/no-collapsible-if": "warn",
      "sonarjs/prefer-single-boolean-return": "warn",
    },
  },
  // ── React/JSX (auto-activates for .jsx/.tsx files) ────────
  {
    files: ["**/*.jsx", "**/*.tsx"],
    plugins: {
      react,
      "react-hooks": reactHooks,
      "jsx-a11y": jsxA11y,
      i18next,
    },
    settings: {
      react: { version: "detect" },
    },
    rules: {
      // Hooks
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",

      // React best practices
      "react/jsx-no-target-blank": "error",
      "react/no-danger": "warn",
      "react/self-closing-comp": "warn",

      // i18n — catch hardcoded strings early (painful to retrofit)
      "i18next/no-literal-string": "warn",

      // Accessibility
      "jsx-a11y/alt-text": "warn",
      "jsx-a11y/anchor-is-valid": "warn",
      "jsx-a11y/click-events-have-key-events": "warn",
      "jsx-a11y/no-autofocus": "warn",
      "jsx-a11y/label-has-associated-control": "warn",
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
