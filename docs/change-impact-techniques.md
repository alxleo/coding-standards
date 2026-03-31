# Change Impact Analysis — Technique Registry

Algorithms and techniques for answering "how hard is it to make a correct change?"
Each entry records: what it does, the source paper/tool, implementation status, and evaluation criteria.

## Implemented

### 1. Blast Radius (filename reference count)

**What:** Grep every filename across scannable files, count references.
**Source:** Custom — no existing tool covers config-to-code references.
**Implementation:** `scripts/blast_radius.py` → `compute_blast_radius()`
**Strengths:** Language-agnostic, catches config refs that AST tools miss.
**Weaknesses:** False positives from substring matches (e.g., `test.py` matches `pytest.py`). No semantic understanding — can't tell if a string is a reference or documentation.
**Evaluation:** Does it correctly identify all files that need updating when a config changes? Test: rename a file, does the tool flag all stale references?

### 2. Temporal Coupling (Jaccard similarity on git co-changes)

**What:** From git history, find files that always change together.
**Source:** Zimmermann et al. (2005) "Mining Version Histories to Guide Software Changes." Noise filters from CodeScene.
**Formula:** `coupling(A,B) = co_changes(A,B) / (changes(A) + changes(B) - co_changes(A,B))`
**Implementation:** `scripts/blast_radius.py` → `compute_temporal_coupling()`
**Strengths:** Catches implicit coupling that no static analysis can see.
**Weaknesses:** Requires sufficient history (min commits). Pairwise only — misses multi-file patterns.
**Evaluation:** Does it predict which files are missing from a PR? Test: for historical PRs that had follow-up fixes, would the tool have flagged the missing file?

### 3. CIRank (PageRank weighted by co-change frequency)

**What:** PageRank on dependency graph where edge weights are co-change counts.
**Source:** Wang et al. (2014) "Network-Based Analysis of Software Change Propagation." Correlation 0.52-0.81 with actual change propagation.
**Implementation:** `scripts/blast_radius.py` → `compute_criticality()`
**Strengths:** Identifies files whose changes propagate furthest.
**Weaknesses:** Static ranking — doesn't adapt to what you're working on now.
**Evaluation:** Do the top-ranked files correlate with files that cause the most follow-up changes in git history?

### 4. Naming Entropy (Shannon entropy per directory)

**What:** Classify filenames by convention (kebab, snake, camel, etc), compute entropy.
**Source:** Standard information theory. Yakubov et al. (2025) showed naming affects LLM accuracy (34.2% vs 16.6% exact match).
**Implementation:** `scripts/blast_radius.py` → `compute_naming_entropy()`
**Strengths:** Simple, fast, directly actionable (rename offending files).
**Weaknesses:** Doesn't measure content consistency, only naming. Some mixed conventions are intentional (.dotfiles vs scripts).
**Evaluation:** Does reducing entropy correlate with fewer naming-related mistakes?

### 5. Personalized PageRank (context-aware criticality)

**What:** Instead of uniform PageRank, boost files being worked on. "Given I'm editing ruff.toml, which OTHER files become more critical?"
**Source:** Aider's repomap (2023). Uses NetworkX personalized PageRank. Context-window utilization 4.3-6.5% vs 54-70% for iterative search.
**Implementation:** `scripts/blast_radius.py` → `_personalized_pagerank()`, used in `pr_review()`
**Strengths:** Context-aware — ruff.toml criticality jumps from 0.059 (static) to 0.281 (personalized when editing it).
**Weaknesses:** Sensitive to personalization weights (currently 100:1 ratio).
**Evaluation:** For a given set of changed files, does personalized ranking surface the actually-needed files higher than static CIRank?

### 6. Python AST Import Graph

**What:** Parse Python `import` / `from X import Y` statements via stdlib `ast` module. Build actual import dependency graph.
**Source:** Standard static analysis. Tree-sitter and Depwire do this for multiple languages.
**Implementation:** `scripts/blast_radius.py` → `_extract_python_imports()`, edges fed into `_build_dependency_graph()`
**Strengths:** More precise than grep for .py files. Resolves `import manifest_schema` to `scripts/manifest_schema.py`.
**Weaknesses:** Python only. Doesn't handle dynamic imports (`importlib.import_module`). Ambiguous stems (two files with same name) safely unresolved.
**Evaluation:** Does the AST graph catch import-chain dependencies that grep misses?

## Planned — To Implement and Evaluate

### 7. Multi-file Association Rules (Apriori algorithm)

**What:** Beyond pairwise coupling — find rules like "when A AND B change, C almost always changes too."
**Source:** Zimmermann et al. (2005) ROSE tool. Agrawal & Srikant (1994) Apriori algorithm.
**Implementation status:** Not yet. ~80 lines. Needs more git history to be useful.
**Expected improvement:** Catches trio+ patterns (Dockerfile + .mega-linter-default.yml + plugins/*.yml always change together).
**Evaluation:** Do multi-file rules predict missing files better than pairwise Jaccard? Test: measure precision/recall against historical multi-file commits.

### 8. Conceptual Coupling (TF-IDF / LSI on file contents)

**What:** Files that discuss similar concepts (same identifiers, comments, variable names) are semantically coupled.
**Source:** Kagdi, Gethers & Poshyvanyk (2013). Combined with temporal+structural, improved F-measure 14-21%.
**Implementation status:** Not yet. ~50 lines using sklearn TF-IDF or simple term frequency.
**Expected improvement:** New signal dimension — catches "these files are about the same thing" even without references or co-changes.
**Evaluation:** Does conceptual coupling identify related files that structural and temporal coupling miss? Test: find file pairs with high conceptual similarity but zero blast radius and zero coupling — are they actually related?

### 9. Topology Analysis (fan-in, fan-out, bridge nodes)

**What:** Beyond PageRank — identify structural patterns. Fan-in (hub), fan-out (authority), bridge (bottleneck between clusters).
**Source:** Robillard (2008) "Topology Analysis of Software Dependencies" (ACM TOSEM).
**Implementation status:** Not yet. ~30 lines using NetworkX centrality functions.
**Expected improvement:** Identifies architectural roles — "this file is the only connection between CI and scripts."
**Evaluation:** Do bridge nodes correlate with files that cause cross-module breakage?

### 10. Transformer + Program Dependence Graphs

**What:** Neural embeddings of code combined with program dependence graphs for deep semantic understanding.
**Source:** Recent 2024 papers on combining LLMs with static analysis.
**Implementation status:** Out of scope for now. Research frontier.
**Expected improvement:** Unknown — would need evaluation against simpler techniques.

## Evaluation Framework

For each technique, measure against historical git data:

1. **Precision:** Of the files flagged, how many actually needed changing?
2. **Recall:** Of the files that actually needed changing, how many were flagged?
3. **Latency:** How fast does the analysis run?
4. **Signal overlap:** Does this technique find things the others don't?

The compound metric remains: `change_difficulty = blast_radius + coupling + criticality + entropy`
Each new technique either improves an existing signal or adds a new orthogonal one.
