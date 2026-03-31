// coding-standards baseline ESLint config (flat config format).
// Consumer repos override by placing their own eslint.config.mjs at root.
//
// Plugins baked into the Docker image:
//   - unicorn:  best practices, filename conventions, modernization
//   - security: injection, unsafe eval, prototype pollution
//   - sonarjs:  complexity, duplication, code smells
//   - jest:     test quality (already in MegaLinter cupcake)

import unicorn from "eslint-plugin-unicorn";
import security from "eslint-plugin-security";
import sonarjs from "eslint-plugin-sonarjs";

export default [
  {
    plugins: {
      unicorn,
      security,
      sonarjs,
    },
    rules: {
      // ── Filename conventions ──────────────────────────────
      // Python: snake_case (importability). JS/TS: kebab-case (convention).
      "unicorn/filename-case": [
        "warn",
        { cases: { kebabCase: true, pascalCase: true } },
      ],

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

      // ── Code smells (sonarjs) ─────────────────────────────
      "sonarjs/no-duplicate-string": ["warn", { threshold: 4 }],
      "sonarjs/cognitive-complexity": ["warn", 15],
      "sonarjs/no-identical-functions": "warn",
      "sonarjs/no-collapsible-if": "warn",
      "sonarjs/prefer-single-boolean-return": "warn",
    },
  },
  // ── Test files: add jest rules ────────────────────────────
  {
    files: ["**/*.test.*", "**/*.spec.*", "**/test/**", "**/tests/**"],
    plugins: {},
    rules: {
      // jest plugin is pre-installed in cupcake but needs to be
      // imported by the consumer if they want these rules.
      // These are intentionally commented — consumers add jest plugin:
      // "jest/expect-expect": "warn",
      // "jest/no-disabled-tests": "warn",
      // "jest/no-focused-tests": "error",
    },
  },
];
