# analysis/

Consumer scripts and notebooks for the paper's analysis. Code here reads the
tidy result tables produced by the pipeline (`results/tables/`) and never
reaches into raw audits or imports internal library internals beyond the public
API. This directory is a consumer of the library, never a dependency of it.
Populated in the statistical-analysis work package.
