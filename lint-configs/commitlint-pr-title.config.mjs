import config from "./commitlint.config.mjs";

// PR titles are squash subjects, so commit-history exemptions do not apply.
export default { ...config, defaultIgnores: false };
