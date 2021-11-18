# r-pkgdown-multisite

Github Action to generate multiple versions of pkgdown docs for R packages


```yaml
---
name: Docs 📚

on:
  push:
    branches:
      - main
    paths:
      - inst/templates/**
      - _pkgdown.yml
      - DESCRIPTION
      - '**.md'
      - man/**
      - LICENSE.*
      - NAMESPACE
  pull_request:
    branches:
      - main
      - pre-release

jobs:
  docs:
    name: Pkgdown Docs 📚 
    uses: insightsengineering/r.pkg.template/.github/workflows/pkgdown.yaml@main
    secrets:
      REPO_GITHUB_TOKEN: ${{ secrets.REPO_GITHUB_TOKEN }}

  multisite:
    name: Multisite creation
    if: ${{ (github.event_name == 'push' && github.ref == 'refs/heads/main') || startsWith(github.ref, 'refs/tags/v') }}
    runs-on: ubuntu-latest
    container:
      image: ghcr.io/insightsengineering/rstudio_4.1.0_bioc_3.13:latest
    needs: docs
    steps:
      - name: Change branch multisite docs
        uses: actions/checkout@v2
        with:
          ref: gh-pages

      - name: Multisite docs update links 
        uses: insightsengineering/r-pkgdown-multisite@6-pkg-multisite
        env:
          GITHUB_PAT: ${{ secrets.REPO_GITHUB_TOKEN }}
      
      - name: Setup github user
        uses: fregante/setup-git-user@v1

      - name: Push changes, if any
        uses: EndBug/add-and-commit@v7


```
