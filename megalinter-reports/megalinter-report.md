## ✅⚠️[MegaLinter](https://megalinter.io/9.4.0) analysis: Success with warnings



| Descriptor  |                                       Linter                                        |Files|Fixed|Errors|Warnings|Elapsed time|
|-------------|-------------------------------------------------------------------------------------|----:|----:|-----:|-------:|-----------:|
|✅ ACTION    |[actionlint](https://megalinter.io/9.4.0/descriptors/action_actionlint)              |    4|     |     0|       0|       2.26s|
|✅ BASH      |[shellcheck](https://megalinter.io/9.4.0/descriptors/bash_shellcheck)                |    9|     |     0|       0|       0.67s|
|⚠️ BASH      |[shfmt](https://megalinter.io/9.4.0/descriptors/bash_shfmt)                          |    9|     |     5|       0|       0.16s|
|⚠️ COPYPASTE |[pmd-cpd](https://megalinter.io/9.4.0/descriptors/copypaste_pmd_cpd)                 |  yes|     |     1|      no|       6.11s|
|⚠️ DOCKERFILE|[dclint](https://megalinter.io/9.4.0/descriptors/dockerfile_dclint)                  |   27|     |     1|       0|       2.82s|
|✅ DOCKERFILE|[hadolint](https://megalinter.io/9.4.0/descriptors/dockerfile_hadolint)              |    1|     |     0|       0|       0.86s|
|⚠️ JSON      |[prettier](https://megalinter.io/9.4.0/descriptors/json_prettier)                    |   10|     |     1|       0|       3.02s|
|✅ JSON      |[v8r](https://megalinter.io/9.4.0/descriptors/json_v8r)                              |   10|     |     0|       0|      12.87s|
|⚠️ MARKDOWN  |[markdownlint](https://megalinter.io/9.4.0/descriptors/markdown_markdownlint)        |    5|     |   296|       0|       3.58s|
|✅ PYTHON    |[pyright](https://megalinter.io/9.4.0/descriptors/python_pyright)                    |    8|     |     0|       0|       7.05s|
|✅ PYTHON    |[ruff](https://megalinter.io/9.4.0/descriptors/python_ruff)                          |    8|     |     0|       0|       0.36s|
|✅ REPOSITORY|[gitleaks](https://megalinter.io/9.4.0/descriptors/repository_gitleaks)              |  yes|     |    no|      no|       1.07s|
|✅ REPOSITORY|[git_diff](https://megalinter.io/9.4.0/descriptors/repository_git_diff)              |  yes|     |    no|      no|       0.13s|
|✅ REPOSITORY|[just-fmt](https://megalinter.io/9.4.0/descriptors/repository_just_fmt)              |    1|     |     0|       0|       0.06s|
|✅ REPOSITORY|[knip](https://megalinter.io/9.4.0/descriptors/repository_knip)                      |  yes|     |    no|      no|       3.24s|
|✅ REPOSITORY|[license-checker](https://megalinter.io/9.4.0/descriptors/repository_license_checker)|  yes|     |    no|      no|       1.36s|
|✅ REPOSITORY|[npm-audit](https://megalinter.io/9.4.0/descriptors/repository_npm_audit)            |  yes|     |    no|      no|       2.93s|
|✅ REPOSITORY|[semgrep](https://megalinter.io/9.4.0/descriptors/repository_semgrep)                |  yes|     |    no|      no|       19.8s|
|✅ REPOSITORY|[trivy](https://megalinter.io/9.4.0/descriptors/repository_trivy)                    |  yes|     |    no|      no|       3.15s|
|⚠️ SPELL     |[lychee](https://megalinter.io/9.4.0/descriptors/spell_lychee)                       |   42|     |     6|       0|       2.29s|
|⚠️ YAML      |[prettier](https://megalinter.io/9.4.0/descriptors/yaml_prettier)                    |   27|     |     1|      17|        2.8s|
|⚠️ YAML      |[v8r](https://megalinter.io/9.4.0/descriptors/yaml_v8r)                              |   27|     |     1|       0|      13.35s|
|⚠️ YAML      |[yamllint](https://megalinter.io/9.4.0/descriptors/yaml_yamllint)                    |   27|     |    47|       0|       1.91s|

## Detailed Issues

<details>
<summary>⚠️ DOCKERFILE / dclint - 1 error</summary>

```
FileNotFoundError: File or directory not found: lint
    at findFilesForLinting (/usr/local/lib/node_modules/dclint/bin/dclint.cjs:5949:19)
    at DCLinter.lintFiles (/usr/local/lib/node_modules/dclint/bin/dclint.cjs:6427:23)
    at main (/usr/local/lib/node_modules/dclint/bin/dclint.cjs:6577:30)
    at Object.<anonymous> (/usr/local/lib/node_modules/dclint/bin/dclint.cjs:6610:1)
    at Module._compile (node:internal/modules/cjs/loader:1760:14)
    at Object..js (node:internal/modules/cjs/loader:1893:10)
    at Module.load (node:internal/modules/cjs/loader:1480:32)
    at Module._load (node:internal/modules/cjs/loader:1299:12)
    at TracingChannel.traceSync (node:diagnostics_channel:328:14)
    at wrapModuleLoad (node:internal/modules/cjs/loader:244:24)
```

</details>

<details>
<summary>⚠️ SPELL / lychee - 6 errors</summary>

```
[404] https://pmd.github.io/latest/pmd_userdocs_cpd.html | Network error: Not Found
[404] https://raw.githubusercontent.com/alxleo/coding-standards/main/scripts/report-statuses.py | Network error: Not Found
[404] https://github.com/aquasecurity/trivy/releases/download/v$%7BVERSION%7D | Network error: Not Found
[404] https://github.com/opentofu/opentofu/releases/download/v$%7BVERSION%7D | Network error: Not Found
[404] https://github.com/casey/just/releases/download/$%7BVERSION%7D | Network error: Not Found
[404] https://github.com/terraform-linters/tflint/releases/download/v$%7BVERSION%7D | Network error: Not Found
📝 Summary
---------------------
🔍 Total...........54
✅ Successful......47
⏳ Timeouts.........0
🔀 Redirected.......0
👻 Excluded.........1
❓ Unknown..........0
🚫 Errors...........6

Errors in plugins/pmd-cpd.megalinter-descriptor.yml
[404] https://pmd.github.io/latest/pmd_userdocs_cpd.html | Network error: Not Found

Errors in .github/workflows/lint.yml
[404] https://github.com/opentofu/opentofu/releases/download/v$%7BVERSION%7D | Network error: Not Found
[404] https://github.com/aquasecurity/trivy/releases/download/v$%7BVERSION%7D | Network error: Not Found
[404] https://github.com/terraform-linters/tflint/releases/download/v$%7BVERSION%7D | Network error: Not Found
[404] https://github.com/casey/just/releases/download/$%7BVERSION%7D | Network error: Not Found

Errors in examples/lint-docker.yml
[404] https://raw.githubusercontent.com/alxleo/coding-standards/main/scripts/report-statuses.py | Network error: Not Found
   [WARN ] There were issues with GitHub URLs. You could try setting a GitHub token and running lychee again.
```

</details>

<details>
<summary>⚠️ MARKDOWN / markdownlint - 296 errors</summary>

```
CLAUDE.md:3:81 error MD013/line-length Line length [Expected: 80; Actual: 235]
CLAUDE.md:5:81 error MD013/line-length Line length [Expected: 80; Actual: 244]
CLAUDE.md:7:81 error MD013/line-length Line length [Expected: 80; Actual: 103]
CLAUDE.md:12 error MD031/blanks-around-fences Fenced code blocks should be surrounded by blank lines [Context: "```bash"]
CLAUDE.md:14:81 error MD013/line-length Line length [Expected: 80; Actual: 103]
CLAUDE.md:15:81 error MD013/line-length Line length [Expected: 80; Actual: 119]
CLAUDE.md:19 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "1. Auto-detects which linters ..."]
CLAUDE.md:70:81 error MD013/line-length Line length [Expected: 80; Actual: 90]
CLAUDE.md:71:81 error MD013/line-length Line length [Expected: 80; Actual: 90]
CLAUDE.md:77:81 error MD013/line-length Line length [Expected: 80; Actual: 89]
CLAUDE.md:89:81 error MD013/line-length Line length [Expected: 80; Actual: 176]
CLAUDE.md:96:81 error MD013/line-length Line length [Expected: 80; Actual: 147]
CLAUDE.md:102:81 error MD013/line-length Line length [Expected: 80; Actual: 92]
CLAUDE.md:103:81 error MD013/line-length Line length [Expected: 80; Actual: 283]
CLAUDE.md:104:81 error MD013/line-length Line length [Expected: 80; Actual: 163]
CLAUDE.md:106:81 error MD013/line-length Line length [Expected: 80; Actual: 87]
CLAUDE.md:111:81 error MD013/line-length Line length [Expected: 80; Actual: 108]
CLAUDE.md:117:81 error MD013/line-length Line length [Expected: 80; Actual: 125]
CLAUDE.md:121:81 error MD013/line-length Line length [Expected: 80; Actual: 217]
CLAUDE.md:137:81 error MD013/line-length Line length [Expected: 80; Actual: 115]
CLAUDE.md:139:81 error MD013/line-length Line length [Expected: 80; Actual: 206]
CLAUDE.md:147:81 error MD013/line-length Line length [Expected: 80; Actual: 152]
CLAUDE.md:149:81 error MD013/line-length Line length [Expected: 80; Actual: 113]
CLAUDE.md:150:81 error MD013/line-length Line length [Expected: 80; Actual: 107]
CLAUDE.md:161:81 error MD013/line-length Line length [Expected: 80; Actual: 107]
CLAUDE.md:162:81 error MD013/line-length Line length [Expected: 80; Actual: 106]
CLAUDE.md:163:81 error MD013/line-length Line length [Expected: 80; Actual: 130]
docs/architecture-decisions.md:9:81 error MD013/line-length Line length [Expected: 80; Actual: 102]
docs/architecture-decisions.md:20:81 error MD013/line-length Line length [Expected: 80; Actual: 340]
docs/architecture-decisions.md:22:81 error MD013/line-length Line length [Expected: 80; Actual: 200]
docs/architecture-decisions.md:24:81 error MD013/line-length Line length [Expected: 80; Actual: 104]
docs/architecture-decisions.md:30:81 error MD013/line-length Line length [Expected: 80; Actual: 193]
docs/architecture-decisions.md:35:5 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/architecture-decisions.md:35:9 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/architecture-decisions.md:35:13 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/architecture-decisions.md:35:1 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/architecture-decisions.md:35:5 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/architecture-decisions.md:35:9 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/architecture-decisions.md:36:81 error MD013/line-length Line length [Expected: 80; Actual: 94]
docs/architecture-decisions.md:43:81 error MD013/line-length Line length [Expected: 80; Actual: 233]
docs/architecture-decisions.md:44:81 error MD013/line-length Line length [Expected: 80; Actual: 179]
docs/architecture-decisions.md:45:81 error MD013/line-length Line length [Expected: 80; Actual: 131]
docs/architecture-decisions.md:46:81 error MD013/line-length Line length [Expected: 80; Actual: 167]
docs/architecture-decisions.md:47:81 error MD013/line-length Line length [Expected: 80; Actual: 105]
docs/architecture-decisions.md:48:81 error MD013/line-length Line length [Expected: 80; Actual: 171]
docs/architecture-decisions.md:49:81 error MD013/line-length Line length [Expected: 80; Actual: 139]
docs/architecture-decisions.md:50:81 error MD013/line-length Line length [Expected: 80; Actual: 135]
docs/architecture-decisions.md:54:81 error MD013/line-length Line length [Expected: 80; Actual: 151]
docs/architecture-decisions.md:61:81 error MD013/line-length Line length [Expected: 80; Actual: 162]
docs/architecture-decisions.md:63:81 error MD013/line-length Line length [Expected: 80; Actual: 173]
docs/architecture-decisions.md:65:81 error MD013/line-length Line length [Expected: 80; Actual: 101]
docs/architecture-decisions.md:70:5 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/architecture-decisions.md:70:9 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/architecture-decisions.md:70:13 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/architecture-decisions.md:70:1 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/architecture-decisions.md:70:5 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/architecture-decisions.md:70:9 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/architecture-decisions.md:81:81 error MD013/line-length Line length [Expected: 80; Actual: 270]
docs/architecture-decisions.md:82:81 error MD013/line-length Line length [Expected: 80; Actual: 127]
docs/architecture-decisions.md:83:81 error MD013/line-length Line length [Expected: 80; Actual: 127]
docs/architecture-decisions.md:87:81 error MD013/line-length Line length [Expected: 80; Actual: 107]
docs/architecture-decisions.md:90:81 error MD013/line-length Line length [Expected: 80; Actual: 173]
docs/architecture-decisions.md:91:81 error MD013/line-length Line length [Expected: 80; Actual: 109]
docs/architecture-decisions.md:99:81 error MD013/line-length Line length [Expected: 80; Actual: 225]
docs/architecture-decisions.md:142:81 error MD013/line-length Line length [Expected: 80; Actual: 88]
docs/architecture-decisions.md:194:81 error MD013/line-length Line length [Expected: 80; Actual: 124]
docs/architecture-decisions.md:199:5 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/architecture-decisions.md:199:9 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/architecture-decisions.md:199:13 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/architecture-decisions.md:199:1 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/architecture-decisions.md:199:5 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/architecture-decisions.md:199:9 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/architecture-decisions.md:200:81 error MD013/line-length Line length [Expected: 80; Actual: 104]
docs/architecture-decisions.md:201:81 error MD013/line-length Line length [Expected: 80; Actual: 91]
docs/architecture-decisions.md:203:81 error MD013/line-length Line length [Expected: 80; Actual: 90]
docs/architecture-decisions.md:204:81 error MD013/line-length Line length [Expected: 80; Actual: 88]
docs/architecture-decisions.md:205:81 error MD013/line-length Line length [Expected: 80; Actual: 85]
docs/architecture-decisions.md:208:81 error MD013/line-length Line length [Expected: 80; Actual: 87]
docs/architecture-decisions.md:210:81 error MD013/line-length Line length [Expected: 80; Actual: 168]
docs/architecture-decisions.md:211:81 error MD013/line-length Line length [Expected: 80; Actual: 147]
docs/architecture-decisions.md:212:81 error MD013/line-length Line length [Expected: 80; Actual: 126]
docs/architecture-decisions.md:214:81 error MD013/line-length Line length [Expected: 80; Actual: 101]
docs/architecture-decisions.md:215:81 error MD013/line-length Line length [Expected: 80; Actual: 102]
docs/architecture-decisions.md:216:81 error MD013/line-length Line length [Expected: 80; Actual: 87]
docs/architecture-decisions.md:217:81 error MD013/line-length Line length [Expected: 80; Actual: 161]
docs/architecture-decisions.md:222:5 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/architecture-decisions.md:222:9 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/architecture-decisions.md:222:13 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/architecture-decisions.md:222:1 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/architecture-decisions.md:222:5 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/architecture-decisions.md:222:9 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/architecture-decisions.md:223:81 error MD013/line-length Line length [Expected: 80; Actual: 160]
docs/architecture-decisions.md:224:81 error MD013/line-length Line length [Expected: 80; Actual: 114]
docs/architecture-decisions.md:225:81 error MD013/line-length Line length [Expected: 80; Actual: 109]
docs/architecture-decisions.md:226:81 error MD013/line-length Line length [Expected: 80; Actual: 131]
docs/architecture-decisions.md:227:81 error MD013/line-length Line length [Expected: 80; Actual: 126]
docs/config-decisions.md:5 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "## Architecture"]
docs/config-decisions.md:6 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- **MegaLinter cupcake base** ..."]
docs/config-decisions.md:8:81 error MD013/line-length Line length [Expected: 80; Actual: 113]
docs/config-decisions.md:9:81 error MD013/line-length Line length [Expected: 80; Actual: 136]
docs/config-decisions.md:10:81 error MD013/line-length Line length [Expected: 80; Actual: 87]
docs/config-decisions.md:14 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Python: ruff only (+ pyright standard)"]
docs/config-decisions.md:15 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- flake8/black/isort: 100% sup..."]
docs/config-decisions.md:18:81 error MD013/line-length Line length [Expected: 80; Actual: 167]
docs/config-decisions.md:21 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Security: trivy + semgrep only"]
docs/config-decisions.md:22 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- checkov/kics: IaC overlap wi..."]
docs/config-decisions.md:27 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Secrets: gitleaks only in CI"]
docs/config-decisions.md:28 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- secretlint: strict subset of..."]
docs/config-decisions.md:31 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Config files: keep existing stack"]
docs/config-decisions.md:32 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- jsonlint: redundant with che..."]
docs/config-decisions.md:38 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Added from audit"]
docs/config-decisions.md:39 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- stylelint (CSS), sqlfluff (S..."]
docs/config-decisions.md:41 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Watch list"]
docs/config-decisions.md:42 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- oxlint: when v1.0 + type-awa..."]
docs/config-decisions.md:47 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Activation: allowlist (ENABLE_LINTERS)"]
docs/config-decisions.md:48 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- Prevents surprise linters on..."]
docs/config-decisions.md:50 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Blocking: two tiers"]
docs/config-decisions.md:51 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- Error: security + types + sy..."]
docs/config-decisions.md:55 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Auto-fix: caller flag"]
docs/config-decisions.md:56 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- Default: APPLY_FIXES=none (c..."]
docs/config-decisions.md:59 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Config paths: explicit for every linter"]
docs/config-decisions.md:60:81 error MD013/line-length Line length [Expected: 80; Actual: 94]
docs/config-decisions.md:60 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- Every linter with a config f..."]
docs/config-decisions.md:65 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Config distribution: baked + override"]
docs/config-decisions.md:66 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- Image ships .mega-linter.yml..."]
docs/config-decisions.md:71 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Reporters"]
docs/config-decisions.md:72 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- TAP: OFF. Breaks project-mod..."]
docs/config-decisions.md:77 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Performance"]
docs/config-decisions.md:78 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- VALIDATE_ALL_CODEBASE: true ..."]
docs/config-decisions.md:82 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Security"]
docs/config-decisions.md:83 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- SECURED_ENV_VARIABLES: GITEA..."]
docs/config-decisions.md:86 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### PRE_COMMANDS"]
docs/config-decisions.md:87 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- git safe.directory + autocrl..."]
docs/config-decisions.md:90 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Supply chain"]
docs/config-decisions.md:91:81 error MD013/line-length Line length [Expected: 80; Actual: 90]
docs/config-decisions.md:91 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- SHA-pin everything: Docker i..."]
docs/config-decisions.md:94 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Multi-tier strategy"]
docs/config-decisions.md:95 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "1. MegaLinter image (primary) ..."]
docs/config-decisions.md:99 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Ruff per-file-ignores for test/CI code"]
docs/config-decisions.md:100 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- Security rules (S prefix) pr..."]
docs/config-decisions.md:101:81 error MD013/line-length Line length [Expected: 80; Actual: 171]
docs/config-decisions.md:102:81 error MD013/line-length Line length [Expected: 80; Actual: 124]
docs/config-decisions.md:103:81 error MD013/line-length Line length [Expected: 80; Actual: 113]
docs/config-decisions.md:105 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Performance optimizations applied"]
docs/config-decisions.md:106 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- jscpd → PMD-CPD: 177s → 5s (..."]
docs/config-decisions.md:108:81 error MD013/line-length Line length [Expected: 80; Actual: 111]
docs/config-decisions.md:112 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Skipped"]
docs/config-decisions.md:113 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- LLM Advisor: the agent consu..."]
docs/megalinter-migration-plan.md:6 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- Runs identically everywhere:..."]
docs/megalinter-migration-plan.md:14 error MD040/fenced-code-language Fenced code blocks should have a language specified [Context: "```"]
docs/megalinter-migration-plan.md:39:81 error MD013/line-length Line length [Expected: 80; Actual: 196]
docs/megalinter-migration-plan.md:44:12 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/megalinter-migration-plan.md:44:19 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/megalinter-migration-plan.md:44:27 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/megalinter-migration-plan.md:44:1 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/megalinter-migration-plan.md:44:12 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/megalinter-migration-plan.md:44:19 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/megalinter-migration-plan.md:64:8 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/megalinter-migration-plan.md:64:22 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/megalinter-migration-plan.md:64:1 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/megalinter-migration-plan.md:64:8 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/megalinter-migration-plan.md:67:81 error MD013/line-length Line length [Expected: 80; Actual: 85]
docs/megalinter-migration-plan.md:77:81 error MD013/line-length Line length [Expected: 80; Actual: 87]
docs/megalinter-migration-plan.md:80:81 error MD013/line-length Line length [Expected: 80; Actual: 81]
docs/megalinter-migration-plan.md:86:81 error MD013/line-length Line length [Expected: 80; Actual: 83]
docs/megalinter-migration-plan.md:86:27 error MD060/table-column-style Table column style [Table pipe does not align with header for style "aligned"]
docs/megalinter-migration-plan.md:86:83 error MD060/table-column-style Table column style [Table pipe does not align with header for style "aligned"]
docs/megalinter-migration-plan.md:87:81 error MD013/line-length Line length [Expected: 80; Actual: 96]
docs/megalinter-migration-plan.md:87:27 error MD060/table-column-style Table column style [Table pipe does not align with header for style "aligned"]
docs/megalinter-migration-plan.md:87:96 error MD060/table-column-style Table column style [Table pipe does not align with header for style "aligned"]
docs/megalinter-migration-plan.md:92:8 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/megalinter-migration-plan.md:92:24 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/megalinter-migration-plan.md:92:44 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/megalinter-migration-plan.md:92:55 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/megalinter-migration-plan.md:92:1 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/megalinter-migration-plan.md:92:8 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/megalinter-migration-plan.md:92:24 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/megalinter-migration-plan.md:92:44 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/megalinter-migration-plan.md:93:81 error MD013/line-length Line length [Expected: 80; Actual: 121]
docs/megalinter-migration-plan.md:94:81 error MD013/line-length Line length [Expected: 80; Actual: 96]
docs/megalinter-migration-plan.md:95:81 error MD013/line-length Line length [Expected: 80; Actual: 132]
docs/megalinter-migration-plan.md:97:81 error MD013/line-length Line length [Expected: 80; Actual: 104]
docs/megalinter-migration-plan.md:98:81 error MD013/line-length Line length [Expected: 80; Actual: 108]
docs/megalinter-migration-plan.md:99:81 error MD013/line-length Line length [Expected: 80; Actual: 108]
docs/megalinter-migration-plan.md:100:81 error MD013/line-length Line length [Expected: 80; Actual: 128]
docs/megalinter-migration-plan.md:101:81 error MD013/line-length Line length [Expected: 80; Actual: 114]
docs/megalinter-migration-plan.md:102:81 error MD013/line-length Line length [Expected: 80; Actual: 141]
docs/megalinter-migration-plan.md:103:81 error MD013/line-length Line length [Expected: 80; Actual: 109]
docs/megalinter-migration-plan.md:104:81 error MD013/line-length Line length [Expected: 80; Actual: 138]
docs/megalinter-migration-plan.md:181:12 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/megalinter-migration-plan.md:181:22 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/megalinter-migration-plan.md:181:28 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
docs/megalinter-migration-plan.md:181:1 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/megalinter-migration-plan.md:181:12 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/megalinter-migration-plan.md:181:22 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
docs/megalinter-migration-plan.md:210:61 error MD050/strong-style Strong style [Expected: asterisk; Actual: underscore]
docs/megalinter-migration-plan.md:210:70 error MD050/strong-style Strong style [Expected: asterisk; Actual: underscore]
docs/megalinter-migration-plan.md:229 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Image produces (capability):"]
docs/megalinter-migration-plan.md:229:32 error MD026/no-trailing-punctuation Trailing punctuation in heading [Punctuation: ':']
docs/megalinter-migration-plan.md:230 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- `megalinter-reports/mega-lin..."]
docs/megalinter-migration-plan.md:237 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### CI produces (interface):"]
docs/megalinter-migration-plan.md:237:28 error MD026/no-trailing-punctuation Trailing punctuation in heading [Punctuation: ':']
docs/megalinter-migration-plan.md:238 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- Per-linter commit statuses v..."]
docs/megalinter-migration-plan.md:242 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Agent consumption:"]
docs/megalinter-migration-plan.md:242:22 error MD026/no-trailing-punctuation Trailing punctuation in heading [Punctuation: ':']
docs/megalinter-migration-plan.md:243 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- Agents read raw CI logs (res..."]
docs/megalinter-migration-plan.md:250:29 error MD026/no-trailing-punctuation Trailing punctuation in heading [Punctuation: ':']
docs/megalinter-migration-plan.md:272:81 error MD013/line-length Line length [Expected: 80; Actual: 120]
docs/megalinter-migration-plan.md:279:34 error MD026/no-trailing-punctuation Trailing punctuation in heading [Punctuation: ':']
docs/megalinter-migration-plan.md:300 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Skip mechanism:"]
docs/megalinter-migration-plan.md:300:19 error MD026/no-trailing-punctuation Trailing punctuation in heading [Punctuation: ':']
docs/megalinter-migration-plan.md:301 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- `DISABLE_LINTERS` for indivi..."]
docs/megalinter-migration-plan.md:318:1 error MD029/ol-prefix Ordered list item prefix [Expected: 1; Actual: 7; Style: 1/2/3]
docs/megalinter-migration-plan.md:319:1 error MD029/ol-prefix Ordered list item prefix [Expected: 2; Actual: 8; Style: 1/2/3]
docs/megalinter-migration-plan.md:320:1 error MD029/ol-prefix Ordered list item prefix [Expected: 3; Actual: 9; Style: 1/2/3]
docs/megalinter-migration-plan.md:321:1 error MD029/ol-prefix Ordered list item prefix [Expected: 4; Actual: 10; Style: 1/2/3]
docs/megalinter-migration-plan.md:325:81 error MD013/line-length Line length [Expected: 80; Actual: 87]
docs/megalinter-migration-plan.md:325:1 error MD029/ol-prefix Ordered list item prefix [Expected: 1; Actual: 11; Style: 1/2/3]
docs/megalinter-migration-plan.md:326:81 error MD013/line-length Line length [Expected: 80; Actual: 101]
docs/megalinter-migration-plan.md:326:1 error MD029/ol-prefix Ordered list item prefix [Expected: 2; Actual: 12; Style: 1/2/3]
docs/megalinter-migration-plan.md:327:1 error MD029/ol-prefix Ordered list item prefix [Expected: 3; Actual: 13; Style: 1/2/3]
docs/megalinter-migration-plan.md:328:1 error MD029/ol-prefix Ordered list item prefix [Expected: 4; Actual: 14; Style: 1/2/3]
docs/megalinter-migration-plan.md:334:81 error MD013/line-length Line length [Expected: 80; Actual: 89]
docs/megalinter-migration-plan.md:363 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### What gets pinned:"]
docs/megalinter-migration-plan.md:363:21 error MD026/no-trailing-punctuation Trailing punctuation in heading [Punctuation: ':']
docs/megalinter-migration-plan.md:364 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- **Docker base image**: `FROM..."]
docs/megalinter-migration-plan.md:370 error MD022/blanks-around-headings Headings should be surrounded by blank lines [Expected: 1; Actual: 0; Below] [Context: "### Automated maintenance:"]
docs/megalinter-migration-plan.md:370:26 error MD026/no-trailing-punctuation Trailing punctuation in heading [Punctuation: ':']
docs/megalinter-migration-plan.md:371 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- Renovate watches Dockerfile,..."]
docs/megalinter-migration-plan.md:378:81 error MD013/line-length Line length [Expected: 80; Actual: 87]
docs/megalinter-migration-plan.md:379:81 error MD013/line-length Line length [Expected: 80; Actual: 176]
docs/megalinter-migration-plan.md:381:81 error MD013/line-length Line length [Expected: 80; Actual: 92]
docs/megalinter-migration-plan.md:382:81 error MD013/line-length Line length [Expected: 80; Actual: 93]
docs/megalinter-migration-plan.md:384:81 error MD013/line-length Line length [Expected: 80; Actual: 104]
docs/megalinter-migration-plan.md:385:81 error MD013/line-length Line length [Expected: 80; Actual: 95]
docs/megalinter-migration-plan.md:386:81 error MD013/line-length Line length [Expected: 80; Actual: 105]
docs/megalinter-migration-plan.md:391 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- `.github/workflows/lint.yml`..."]
docs/megalinter-migration-plan.md:395:81 error MD013/line-length Line length [Expected: 80; Actual: 99]
docs/megalinter-migration-plan.md:399:81 error MD013/line-length Line length [Expected: 80; Actual: 102]
docs/megalinter-migration-plan.md:399 error MD032/blanks-around-lists Lists should be surrounded by blank lines [Context: "- `lint-configs-626465/` — lin..."]
docs/megalinter-migration-plan.md:400:81 error MD013/line-length Line length [Expected: 80; Actual: 98]
README.md:3:81 error MD013/line-length Line length [Expected: 80; Actual: 272]
README.md:30:81 error MD013/line-length Line length [Expected: 80; Actual: 97]
README.md:45:81 error MD013/line-length Line length [Expected: 80; Actual: 154]
README.md:49:81 error MD013/line-length Line length [Expected: 80; Actual: 207]
README.md:51:81 error MD013/line-length Line length [Expected: 80; Actual: 248]
README.md:60:81 error MD013/line-length Line length [Expected: 80; Actual: 97]
README.md:70:9 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
README.md:70:17 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
README.md:70:1 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
README.md:70:9 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
README.md:80:81 error MD013/line-length Line length [Expected: 80; Actual: 177]
README.md:88:81 error MD013/line-length Line length [Expected: 80; Actual: 160]
README.md:104:81 error MD013/line-length Line length [Expected: 80; Actual: 258]
README.md:122:81 error MD013/line-length Line length [Expected: 80; Actual: 140]
README.md:131:81 error MD013/line-length Line length [Expected: 80; Actual: 94]
README.md:135:81 error MD013/line-length Line length [Expected: 80; Actual: 122]
README.md:145:81 error MD013/line-length Line length [Expected: 80; Actual: 204]
README.md:158:81 error MD013/line-length Line length [Expected: 80; Actual: 179]
README.md:172:9 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
README.md:172:17 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
README.md:172:34 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
README.md:172:1 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
README.md:172:9 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
README.md:172:17 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
README.md:173:81 error MD013/line-length Line length [Expected: 80; Actual: 232]
README.md:174:81 error MD013/line-length Line length [Expected: 80; Actual: 109]
README.md:181:81 error MD013/line-length Line length [Expected: 80; Actual: 95]
README.md:190:10 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
README.md:190:24 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
README.md:190:1 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
README.md:190:10 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
README.md:191:81 error MD013/line-length Line length [Expected: 80; Actual: 96]
README.md:192:81 error MD013/line-length Line length [Expected: 80; Actual: 83]
README.md:194:81 error MD013/line-length Line length [Expected: 80; Actual: 96]
README.md:195:81 error MD013/line-length Line length [Expected: 80; Actual: 119]
README.md:196:81 error MD013/line-length Line length [Expected: 80; Actual: 89]
README.md:204:9 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
README.md:204:19 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
README.md:204:33 error MD060/table-column-style Table column style [Table pipe is missing space to the left for style "compact"]
README.md:204:1 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
README.md:204:9 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
README.md:204:19 error MD060/table-column-style Table column style [Table pipe is missing space to the right for style "compact"]
README.md:206:81 error MD013/line-length Line length [Expected: 80; Actual: 86]
README.md:209:81 error MD013/line-length Line length [Expected: 80; Actual: 82]
README.md:225:81 error MD013/line-length Line length [Expected: 80; Actual: 158]
README.md:231:81 error MD013/line-length Line length [Expected: 80; Actual: 154]
README.md:232:81 error MD013/line-length Line length [Expected: 80; Actual: 96]
README.md:236:81 error MD013/line-length Line length [Expected: 80; Actual: 119]
README.md:246:81 error MD013/line-length Line length [Expected: 80; Actual: 137]
README.md:247:81 error MD013/line-length Line length [Expected: 80; Actual: 179]
README.md:248:81 error MD013/line-length Line length [Expected: 80; Actual: 135]
README.md:252:81 error MD013/line-length Line length [Expected: 80; Actual: 98]
README.md:255:81 error MD013/line-length Line length [Expected: 80; Actual: 96]
README.md:256:81 error MD013/line-length Line length [Expected: 80; Actual: 97]
README.md:257:81 error MD013/line-length Line length [Expected: 80; Actual: 103]
```

</details>

<details>
<summary>⚠️ COPYPASTE / pmd-cpd - 1 error</summary>

```
[ERROR] Error collecting .: ./.coding-standards
[WARN] No such file node_modules,vendor,.terraform,.git,megalinter-reports,test
```

</details>

<details>
<summary>⚠️ JSON / prettier - 1 error</summary>

```
Checking formatting...
[warn] .claude/history/2026-03-04_1258_pr-review-merge-git-chaos_b816a393.json
[warn] .claude/history/2026-03-13_1040_drop-cspell-extract-ci-python_bb40c6b3.json
[warn] Code style issues found in 2 files. Run Prettier with --write to fix.
```

</details>

<details>
<summary>⚠️ YAML / prettier - 1 error</summary>

```
Checking formatting...
[warn] .mega-linter-default.yml
[warn] examples/lint-docker.yml
[warn] lint-configs-626465/.hadolint.yaml
[warn] lint-configs-626465/.pre-commit-config.yaml
[warn] plugins/caddy-fmt.megalinter-descriptor.yml
[warn] plugins/commitlint.megalinter-descriptor.yml
[warn] plugins/dclint.megalinter-descriptor.yml
[warn] plugins/dependency-cruiser.megalinter-descriptor.yml
[warn] plugins/just-fmt.megalinter-descriptor.yml
[warn] plugins/knip.megalinter-descriptor.yml
[warn] plugins/license-checker.megalinter-descriptor.yml
[warn] plugins/npm-audit.megalinter-descriptor.yml
[warn] plugins/pmd-cpd.megalinter-descriptor.yml
[warn] plugins/trivy.megalinter-descriptor.yml
[warn] plugins/tsc.megalinter-descriptor.yml
[warn] plugins/zizmor.megalinter-descriptor.yml
[warn] Code style issues found in 16 files. Run Prettier with --write to fix.
```

</details>

<details>
<summary>⚠️ BASH / shfmt - 5 errors</summary>

```
diff scripts/ci/apply-configs.sh.orig scripts/ci/apply-configs.sh
--- scripts/ci/apply-configs.sh.orig
+++ scripts/ci/apply-configs.sh
@@ -20,8 +20,8 @@
 # Extracts skip-hooks and per-tool override paths in one pass.
 PARSED='{"skip":"","overrides":{}}'
 if [ -f "$CONFIG_FILE" ]; then
-  echo "Found override file: $CONFIG_FILE"
-  PARSED=$(uv run --no-project --with pyyaml python3 -c "
+	echo "Found override file: $CONFIG_FILE"
+	PARSED=$(uv run --no-project --with pyyaml python3 -c "
 import yaml, json, os
 try:
     with open(os.environ['CONFIG_FILE']) as f:
@@ -41,34 +41,34 @@
 
 SKIP=""
 if [ -n "$INPUT_SKIP" ]; then
-  SKIP="$INPUT_SKIP"
+	SKIP="$INPUT_SKIP"
 fi
 if [ -n "$SKIP_FROM_OVERRIDE" ]; then
-  if [ -n "$SKIP" ]; then
-    SKIP="$SKIP,$SKIP_FROM_OVERRIDE"
-  else
-    SKIP="$SKIP_FROM_OVERRIDE"
-  fi
-fi
-echo "skip-hooks=$SKIP" >> "$GITHUB_OUTPUT"
+	if [ -n "$SKIP" ]; then
+		SKIP="$SKIP,$SKIP_FROM_OVERRIDE"
+	else
+		SKIP="$SKIP_FROM_OVERRIDE"
+	fi
+fi
+echo "skip-hooks=$SKIP" >>"$GITHUB_OUTPUT"
 if [ -n "$SKIP" ]; then
-  echo "Will skip: $SKIP"
+	echo "Will skip: $SKIP"
 fi
 
 # ── Helper: read override path for a tool ─────────────
 get_override() {
-  printf '%s' "$PARSED" | jq -r ".overrides[\"$1\"] // \"\""
+	printf '%s' "$PARSED" | jq -r ".overrides[\"$1\"] // \"\""
 }
 
 # ── Configs without --config support (must live at repo root) ──
 copy_configs=(.shellcheckrc .editorconfig)
 for cfg in "${copy_configs[@]}"; do
-  if [ ! -f "$cfg" ]; then
-    cp "$CS/$cfg" "$cfg"
-    echo "  Copied to root: $cfg"
-  else
-    echo "  Kept (consumer override): $cfg"
-  fi
+	if [ ! -f "$cfg" ]; then
+		cp "$CS/$cfg" "$cfg"
+		echo "  Copied to root: $cfg"
+	else
+		echo "  Kept (consumer override): $cfg"
+	fi
 done
 
 # ── Extends-capable configs ──────────────────────────
@@ -76,23 +76,23 @@
 # override file (which extends our .baseline) in .coding-standards.yml.
 # Format: tool_key|active_config|baseline_config
 extends_configs=(
-  "yamllint|.yamllint|.yamllint.baseline"
-  "gitleaks|.gitleaks.toml|.gitleaks.baseline.toml"
-  "markdownlint|.markdownlint-cli2.yaml|.markdownlint-cli2.baseline.yaml"
-  "commitlint|commitlint.config.mjs|commitlint.config.baseline.mjs"
+	"yamllint|.yamllint|.yamllint.baseline"
+	"gitleaks|.gitleaks.toml|.gitleaks.baseline.toml"
+	"markdownlint|.markdownlint-cli2.yaml|.markdownlint-cli2.baseline.yaml"
+	"commitlint|commitlint.config.mjs|commitlint.config.baseline.mjs"
 )
 
 for entry in "${extends_configs[@]}"; do
-  IFS='|' read -r tool active baseline <<< "$entry"
-  override_path=$(get_override "$tool")
-
-  if [ -n "$override_path" ] && [ -f "$override_path" ]; then
-    cp "$override_path" "$CS/$active"
-    echo "  Override: $tool → $override_path (extends $baseline)"
-  else
-    # No override — baseline IS the active config
-    cp "$CS/$baseline" "$CS/$active"
-  fi
+	IFS='|' read -r tool active baseline <<<"$entry"
+	override_path=$(get_override "$tool")
+
+	if [ -n "$override_path" ] && [ -f "$override_path" ]; then
+		cp "$override_path" "$CS/$active"
+		echo "  Override: $tool → $override_path (extends $baseline)"
+	else
+		# No override — baseline IS the active config
+		cp "$CS/$baseline" "$CS/$active"
+	fi
 done
 
 # ── Non-extends configs: full replacement ─────────────
@@ -100,10 +100,10 @@
 # overlay it into our config dir so the --config path resolves correctly.
 replace_configs=(.hadolint.yaml .jscpd.json .prettierrc)
 for cfg in "${replace_configs[@]}"; do
-  if [ -f "$cfg" ]; then
-    cp "$cfg" "$CS/$cfg"
-    echo "  Consumer override: $cfg → $CS/$cfg"
-  fi
+	if [ -f "$cfg" ]; then
+		cp "$cfg" "$CS/$cfg"
+		echo "  Consumer override: $cfg → $CS/$cfg"
+	fi
 done
 
 # Always apply pre-commit config — this IS the standard
diff scripts/ci/install-tool.sh.orig scripts/ci/install-tool.sh
--- scripts/ci/install-tool.sh.orig
+++ scripts/ci/install-tool.sh
@@ -23,8 +23,8 @@
 
 # Skip if binary already exists (Docker volume persistence on Gitea)
 if [ -x "$BIN_DIR/$BINARY" ]; then
-  echo "$TOOL_NAME already installed at $BIN_DIR/$BINARY — skipping download"
-  exit 0
+	echo "$TOOL_NAME already installed at $BIN_DIR/$BINARY — skipping download"
+	exit 0
 fi
 
 # Expand ${VERSION} placeholders
@@ -40,15 +40,15 @@
 grep "  ${ARTIFACT}" "$CHECKSUMS" | sha256sum -c -
 
 case "$TOOL_EXTRACT" in
-  tar)  tar -xzf "$ARTIFACT" -C "$BIN_DIR" "$BINARY" ;;
-  unzip)
-    unzip -o "$ARTIFACT" "$BINARY" -d "$BIN_DIR"
-    chmod +x "$BIN_DIR/$BINARY"
-    ;;
-  *)
-    echo "ERROR: unknown TOOL_EXTRACT=$TOOL_EXTRACT (expected tar or unzip)"
-    exit 1
-    ;;
+tar) tar -xzf "$ARTIFACT" -C "$BIN_DIR" "$BINARY" ;;
+unzip)
+	unzip -o "$ARTIFACT" "$BINARY" -d "$BIN_DIR"
+	chmod +x "$BIN_DIR/$BINARY"
+	;;
+*)
+	echo "ERROR: unknown TOOL_EXTRACT=$TOOL_EXTRACT (expected tar or unzip)"
+	exit 1
+	;;
 esac
 
 echo "Installed $TOOL_NAME $VERSION to $BIN_DIR"
diff scripts/ci/lint-run.sh.orig scripts/ci/lint-run.sh
--- scripts/ci/lint-run.sh.orig
+++ scripts/ci/lint-run.sh
@@ -5,7 +5,8 @@
 # and emits ::error annotations for PR inline display.
 set -uo pipefail
 
-logkey="$1"; shift
+logkey="$1"
+shift
 logdir="${LINT_LOG_DIR:-/tmp/lint-results}"
 mkdir -p "$logdir"
 logfile="${logdir}/${logkey}.log"
@@ -17,35 +18,35 @@
 
 # Record outcome for summary.sh and report-statuses.sh
 if [ "$rc" -eq 0 ]; then
-  echo "success" > "${logdir}/${logkey}.outcome"
+	echo "success" >"${logdir}/${logkey}.outcome"
 else
-  echo "failure" > "${logdir}/${logkey}.outcome"
-
-  echo ""
-  echo "── Failures ─────────────────────────────"
-  # Show file:line errors first (most actionable), then other non-noise output
-  grep -E '^\S+:[0-9]+:' "$logfile" | grep -v -E '^::' | head -20 || true
-  # Show non-noise, non-banner summary (hooks that failed, error messages)
-  grep -v -E '^\[INFO\]|^- Installing|^- Using|^Initializing|^- repo:|^\s*$|^::' "$logfile" \
-    | grep -v -E '\.{3,}Passed' \
-    | tail -20
-
-  # Emit ::error annotations for inline PR display (max 10 per step)
-  grep -E '^[^:]+:[0-9]+:[0-9]*:' "$logfile" \
-    | grep -v -E '^\[INFO\]|^- |^::' \
-    | head -10 \
-    | while IFS= read -r line; do
-        file=$(echo "$line" | cut -d: -f1)
-        lineno=$(echo "$line" | cut -d: -f2)
-        col=$(echo "$line" | cut -d: -f3)
-        msg=$(echo "$line" | cut -d: -f4- | sed 's/^[[:space:]]*//')
-        if [ -n "$file" ] && [ -n "$lineno" ] && [ -n "$msg" ]; then
-          if [ -n "$col" ] && [[ "$col" =~ ^[0-9]+$ ]]; then
-            echo "::error file=${file},line=${lineno},col=${col},title=${logkey}::${msg}"
-          else
-            echo "::error file=${file},line=${lineno},title=${logkey}::${msg}"
-          fi
-        fi
-      done
+	echo "failure" >"${logdir}/${logkey}.outcome"
+
+	echo ""
+	echo "── Failures ─────────────────────────────"
+	# Show file:line errors first (most actionable), then other non-noise output
+	grep -E '^\S+:[0-9]+:' "$logfile" | grep -v -E '^::' | head -20 || true
+	# Show non-noise, non-banner summary (hooks that failed, error messages)
+	grep -v -E '^\[INFO\]|^- Installing|^- Using|^Initializing|^- repo:|^\s*$|^::' "$logfile" |
+		grep -v -E '\.{3,}Passed' |
+		tail -20
+
+	# Emit ::error annotations for inline PR display (max 10 per step)
+	grep -E '^[^:]+:[0-9]+:[0-9]*:' "$logfile" |
+		grep -v -E '^\[INFO\]|^- |^::' |
+		head -10 |
+		while IFS= read -r line; do
+			file=$(echo "$line" | cut -d: -f1)
+			lineno=$(echo "$line" | cut -d: -f2)
+			col=$(echo "$line" | cut -d: -f3)
+			msg=$(echo "$line" | cut -d: -f4- | sed 's/^[[:space:]]*//')
+			if [ -n "$file" ] && [ -n "$lineno" ] && [ -n "$msg" ]; then
+				if [ -n "$col" ] && [[ "$col" =~ ^[0-9]+$ ]]; then
+					echo "::error file=${file},line=${lineno},col=${col},title=${logkey}::${msg}"
+				else
+					echo "::error file=${file},line=${lineno},title=${logkey}::${msg}"
+				fi
+			fi
+		done
 fi
 exit "$rc"
diff scripts/download-schemas.sh.orig scripts/download-schemas.sh
--- scripts/download-schemas.sh.orig
+++ scripts/download-schemas.sh
@@ -7,29 +7,29 @@
 mkdir -p "$SCHEMA_DIR"
 
 declare -A SCHEMAS=(
-  [github-workflow]="https://json.schemastore.org/github-workflow.json"
-  [github-action]="https://json.schemastore.org/github-action.json"
-  [package]="https://json.schemastore.org/package.json"
-  [tsconfig]="https://json.schemastore.org/tsconfig.json"
-  [docker-compose]="https://raw.githubusercontent.com/compose-spec/compose-go/main/schema/compose-spec.json"
-  [prettierrc]="https://json.schemastore.org/prettierrc.json"
-  [eslintrc]="https://json.schemastore.org/eslintrc.json"
-  [commitlintrc]="https://json.schemastore.org/commitlintrc.json"
-  [markdownlint]="https://raw.githubusercontent.com/DavidAnson/markdownlint/main/schema/markdownlint-config-schema.json"
-  [yamllint]="https://json.schemastore.org/yamllint.json"
-  [hadolint]="https://raw.githubusercontent.com/hadolint/hadolint/master/contrib/hadolint.json"
-  [renovate]="https://docs.renovatebot.com/renovate-schema.json"
-  [pre-commit]="https://json.schemastore.org/pre-commit-config.json"
-  [pyproject]="https://json.schemastore.org/pyproject.json"
-  [ruff]="https://json.schemastore.org/ruff.json"
-  [dependabot-v2]="https://json.schemastore.org/dependabot-2.0.json"
+	[github - workflow]="https://json.schemastore.org/github-workflow.json"
+	[github - action]="https://json.schemastore.org/github-action.json"
+	[package]="https://json.schemastore.org/package.json"
+	[tsconfig]="https://json.schemastore.org/tsconfig.json"
+	[docker - compose]="https://raw.githubusercontent.com/compose-spec/compose-go/main/schema/compose-spec.json"
+	[prettierrc]="https://json.schemastore.org/prettierrc.json"
+	[eslintrc]="https://json.schemastore.org/eslintrc.json"
+	[commitlintrc]="https://json.schemastore.org/commitlintrc.json"
+	[markdownlint]="https://raw.githubusercontent.com/DavidAnson/markdownlint/main/schema/markdownlint-config-schema.json"
+	[yamllint]="https://json.schemastore.org/yamllint.json"
+	[hadolint]="https://raw.githubusercontent.com/hadolint/hadolint/master/contrib/hadolint.json"
+	[renovate]="https://docs.renovatebot.com/renovate-schema.json"
+	[pre - commit]="https://json.schemastore.org/pre-commit-config.json"
+	[pyproject]="https://json.schemastore.org/pyproject.json"
+	[ruff]="https://json.schemastore.org/ruff.json"
+	[dependabot - v2]="https://json.schemastore.org/dependabot-2.0.json"
 )
 
 for name in "${!SCHEMAS[@]}"; do
-  url="${SCHEMAS[$name]}"
-  dest="$SCHEMA_DIR/${name}.json"
-  echo "  $name"
-  curl -fsSL "$url" -o "$dest"
+	url="${SCHEMAS[$name]}"
+	dest="$SCHEMA_DIR/${name}.json"
+	echo "  $name"
+	curl -fsSL "$url" -o "$dest"
 done
 
 echo "Downloaded ${#SCHEMAS[@]} schemas to $SCHEMA_DIR"
diff scripts/hooks/shell-hygiene.orig scripts/hooks/shell-hygiene
--- scripts/hooks/shell-hygiene.orig
+++ scripts/hooks/shell-hygiene
@@ -10,31 +10,31 @@
 set -uo pipefail
 
 is_shell() {
-    case "$1" in
-        *.sh|*.bash) return 0 ;;
-    esac
-    head -1 "$1" 2>/dev/null | grep -qE '^#!.*\b(ba)?sh\b'
+	case "$1" in
+	*.sh | *.bash) return 0 ;;
+	esac
+	head -1 "$1" 2>/dev/null | grep -qE '^#!.*\b(ba)?sh\b'
 }
 
 rc=0
 for f in "$@"; do
-    # Checks 1 & 2 only apply to shell scripts (not YAML)
-    if is_shell "$f"; then
-        # 1. Forbid bare python/python3 (uv run is required)
-        if grep -nE "(^|[[:space:]])python3?[[:space:]]" "$f" | grep -v "uv run"; then
-            rc=1
-        fi
-
-        # 2. mktemp without trap cleanup
-        if grep -q "mktemp" "$f" && ! grep -q "trap" "$f"; then
-            echo "ERROR: $f uses mktemp without trap EXIT cleanup"
-            rc=1
-        fi
-    fi
-
-    # 3. Unpinned npx versions (applies to shell + yaml)
-    if grep -nE "npx [a-z]" "$f" | grep -vE "npx (--yes|--no|-)|@[0-9]|#.*npx|^[^:]*:.*name:"; then
-        rc=1
-    fi
+	# Checks 1 & 2 only apply to shell scripts (not YAML)
+	if is_shell "$f"; then
+		# 1. Forbid bare python/python3 (uv run is required)
+		if grep -nE "(^|[[:space:]])python3?[[:space:]]" "$f" | grep -v "uv run"; then
+			rc=1
+		fi
+
+		# 2. mktemp without trap cleanup
+		if grep -q "mktemp" "$f" && ! grep -q "trap" "$f"; then
+			echo "ERROR: $f uses mktemp without trap EXIT cleanup"
+			rc=1
+		fi
+	fi
+
+	# 3. Unpinned npx versions (applies to shell + yaml)
+	if grep -nE "npx [a-z]" "$f" | grep -vE "npx (--yes|--no|-)|@[0-9]|#.*npx|^[^:]*:.*name:"; then
+		rc=1
+	fi
 done
 exit "$rc"
```

</details>

<details>
<summary>⚠️ YAML / v8r - 1 error</summary>

```
ℹ No config file found
ℹ Pre-warming the cache
ℹ Processing .github/workflows/ci.yml
ℹ Found schema in https://www.schemastore.org/api/json/catalog.json ...
ℹ Validating .github/workflows/ci.yml against schema from https://www.schemastore.org/github-workflow.json ...
✔ .github/workflows/ci.yml is valid

ℹ Processing .github/workflows/docker-build.yml
ℹ Found schema in https://www.schemastore.org/api/json/catalog.json ...
ℹ Validating .github/workflows/docker-build.yml against schema from https://www.schemastore.org/github-workflow.json ...
✔ .github/workflows/docker-build.yml is valid

ℹ Processing .github/workflows/lint.yml
ℹ Found schema in https://www.schemastore.org/api/json/catalog.json ...
ℹ Validating .github/workflows/lint.yml against schema from https://www.schemastore.org/github-workflow.json ...
✔ .github/workflows/lint.yml is valid

ℹ Processing .github/workflows/release.yml
ℹ Found schema in https://www.schemastore.org/api/json/catalog.json ...
ℹ Validating .github/workflows/release.yml against schema from https://www.schemastore.org/github-workflow.json ...
✔ .github/workflows/release.yml is valid

ℹ Processing .mega-linter-default.yml
✖ Could not find a schema to validate .mega-linter-default.yml

ℹ Processing action.yml
ℹ Found schema in https://www.schemastore.org/api/json/catalog.json ...
ℹ Validating action.yml against schema from https://www.schemastore.org/github-action.json ...
✔ action.yml is valid

ℹ Processing examples/.coding-standards.yml
✖ Could not find a schema to validate examples/.coding-standards.yml

ℹ Processing examples/lint-docker.yml
✖ Could not find a schema to validate examples/lint-docker.yml

ℹ Processing examples/lint.yml
✖ Could not find a schema to validate examples/lint.yml

ℹ Processing lint-configs-626465/.hadolint.yaml
ℹ Found schema in https://www.schemastore.org/api/json/catalog.json ...
ℹ Validating lint-configs-626465/.hadolint.yaml against schema from https://raw.githubusercontent.com/hadolint/hadolint/master/contrib/hadolint.json ...
✔ lint-configs-626465/.hadolint.yaml is valid

ℹ Processing lint-configs-626465/.markdownlint-cli2.baseline.yaml
✖ Could not find a schema to validate lint-configs-626465/.markdownlint-cli2.baseline.yaml

ℹ Processing lint-configs-626465/.markdownlint-cli2.yaml
✖ Could not find a schema to validate lint-configs-626465/.markdownlint-cli2.yaml

ℹ Processing lint-configs-626465/.mega-linter.yml
ℹ Found schema in https://www.schemastore.org/api/json/catalog.json ...
ℹ Validating lint-configs-626465/.mega-linter.yml against schema from https://raw.githubusercontent.com/megalinter/megalinter/main/megalinter/descriptors/schemas/megalinter-configuration.jsonschema.json ...
✖ lint-configs-626465/.mega-linter.yml is invalid

lint-configs-626465/.mega-linter.yml# must NOT have additional properties, found additional property 'BASH_SHELLCHECK_CONFIG_FILE'

ℹ Processing lint-configs-626465/.pre-commit-config.yaml
ℹ Found schema in https://www.schemastore.org/api/json/catalog.json ...
ℹ Validating lint-configs-626465/.pre-commit-config.yaml against schema from https://www.schemastore.org/pre-commit-config.json ...
✔ lint-configs-626465/.pre-commit-config.yaml is valid

ℹ Processing lint-configs-626465/.v8rrc.yml
ℹ Found schema in https://www.schemastore.org/api/json/catalog.json ...
ℹ Validating lint-configs-626465/.v8rrc.yml against schema from https://raw.githubusercontent.com/chris48s/v8r/main/config-schema.json ...
✔ lint-configs-626465/.v8rrc.yml is valid

ℹ Processing plugins/caddy-fmt.megalinter-descriptor.yml
✖ Could not find a schema to validate plugins/caddy-fmt.megalinter-descriptor.yml

ℹ Processing plugins/commitlint.megalinter-descriptor.yml
✖ Could not find a schema to validate plugins/commitlint.megalinter-descriptor.yml

ℹ Processing plugins/dclint.megalinter-descriptor.yml
✖ Could not find a schema to validate plugins/dclint.megalinter-descriptor.yml

ℹ Processing plugins/dependency-cruiser.megalinter-descriptor.yml
✖ Could not find a schema to validate plugins/dependency-cruiser.megalinter-descriptor.yml

ℹ Processing plugins/just-fmt.megalinter-descriptor.yml
✖ Could not find a schema to validate plugins/just-fmt.megalinter-descriptor.yml

ℹ Processing plugins/knip.megalinter-descriptor.yml
✖ Could not find a schema to validate plugins/knip.megalinter-descriptor.yml

ℹ Processing plugins/license-checker.megalinter-descriptor.yml
✖ Could not find a schema to validate plugins/license-checker.megalinter-descriptor.yml

ℹ Processing plugins/npm-audit.megalinter-descriptor.yml
✖ Could not find a schema to validate plugins/npm-audit.megalinter-descriptor.yml

ℹ Processing plugins/pmd-cpd.megalinter-descriptor.yml
✖ Could not find a schema to validate plugins/pmd-cpd.megalinter-descriptor.yml

ℹ Processing plugins/trivy.megalinter-descriptor.yml
✖ Could not find a schema to validate plugins/trivy.megalinter-descriptor.yml

ℹ Processing plugins/tsc.megalinter-descriptor.yml
✖ Could not find a schema to validate plugins/tsc.megalinter-descriptor.yml

ℹ Processing plugins/zizmor.megalinter-descriptor.yml
✖ Could not find a schema to validate plugins/zizmor.megalinter-descriptor.yml
```

</details>

<details>
<summary>⚠️ YAML / yamllint - 47 errors</summary>

```
plugins/caddy-fmt.megalinter-descriptor.yml
  4:1       error    wrong indentation: expected at least 1  (indentation)
  7:3       error    wrong indentation: expected at least 3  (indentation)
  13:3      error    wrong indentation: expected at least 3  (indentation)
  18:3      error    wrong indentation: expected at least 3  (indentation)

plugins/commitlint.megalinter-descriptor.yml
  5:1       error    wrong indentation: expected at least 1  (indentation)
  8:3       error    wrong indentation: expected at least 3  (indentation)
  14:3      error    wrong indentation: expected at least 3  (indentation)
  22:3      error    wrong indentation: expected at least 3  (indentation)

plugins/dclint.megalinter-descriptor.yml
  4:1       error    wrong indentation: expected at least 1  (indentation)
  7:3       error    wrong indentation: expected at least 3  (indentation)
  13:3      error    wrong indentation: expected at least 3  (indentation)
  17:3      error    wrong indentation: expected at least 3  (indentation)
  20:3      error    wrong indentation: expected at least 3  (indentation)

plugins/dependency-cruiser.megalinter-descriptor.yml
  5:1       error    wrong indentation: expected at least 1  (indentation)
  8:3       error    wrong indentation: expected at least 3  (indentation)
  14:3      error    wrong indentation: expected at least 3  (indentation)
  22:3      error    wrong indentation: expected at least 3  (indentation)

plugins/just-fmt.megalinter-descriptor.yml
  4:1       error    wrong indentation: expected at least 1  (indentation)
  7:3       error    wrong indentation: expected at least 3  (indentation)
  13:3      error    wrong indentation: expected at least 3  (indentation)
  20:3      error    wrong indentation: expected at least 3  (indentation)

plugins/knip.megalinter-descriptor.yml
  5:1       error    wrong indentation: expected at least 1  (indentation)
  8:3       error    wrong indentation: expected at least 3  (indentation)
  14:3      error    wrong indentation: expected at least 3  (indentation)
  20:3      error    wrong indentation: expected at least 3  (indentation)

plugins/license-checker.megalinter-descriptor.yml
  5:1       error    wrong indentation: expected at least 1  (indentation)
  8:3       error    wrong indentation: expected at least 3  (indentation)
  14:3      error    wrong indentation: expected at least 3  (indentation)
  22:3      error    wrong indentation: expected at least 3  (indentation)

plugins/npm-audit.megalinter-descriptor.yml
  5:1       error    wrong indentation: expected at least 1  (indentation)
  8:3       error    wrong indentation: expected at least 3  (indentation)
  14:3      error    wrong indentation: expected at least 3  (indentation)
  21:3      error    wrong indentation: expected at least 3  (indentation)

plugins/pmd-cpd.megalinter-descriptor.yml
  5:1       error    wrong indentation: expected at least 1  (indentation)
  8:3       error    wrong indentation: expected at least 3  (indentation)
  14:3      error    wrong indentation: expected at least 3  (indentation)

plugins/trivy.megalinter-descriptor.yml
  5:1       error    wrong indentation: expected at least 1  (indentation)
  8:3       error    wrong indentation: expected at least 3  (indentation)
  14:3      error    wrong indentation: expected at least 3  (indentation)

plugins/tsc.megalinter-descriptor.yml
  4:1       error    wrong indentation: expected at least 1  (indentation)
  7:3       error    wrong indentation: expected at least 3  (indentation)
  13:3      error    wrong indentation: expected at least 3  (indentation)
  20:3      error    wrong indentation: expected at least 3  (indentation)

plugins/zizmor.megalinter-descriptor.yml
  5:1       error    wrong indentation: expected at least 1  (indentation)
  8:3       error    wrong indentation: expected at least 3  (indentation)
  14:3      error    wrong indentation: expected at least 3  (indentation)
  20:3      error    wrong indentation: expected at least 3  (indentation)
```

</details>

See detailed reports in MegaLinter artifacts

[![MegaLinter is graciously provided by OX Security](https://raw.githubusercontent.com/oxsecurity/megalinter/main/docs/assets/images/ox-banner.png)](https://www.ox.security/?ref=megalinter)
Show us your support by [**starring ⭐ the repository**](https://github.com/oxsecurity/megalinter)