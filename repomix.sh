#!/bin/bash

npx repomix \
  --style markdown \
  --ignore "**/node_modules/**,**/dist/**,**/.git/**,**/backend/data/**,**/backend/saved_models/**,\
**/backend/static/**,**/__pycache__/**,**/.venv/**,**/venv/**,**/.vscode/**,**/.idea/**,\
**/*.png,**/*.jpg,**/*.jpeg,**/*.svg,**/*.ico,**/package-lock.json,**/yarn.lock,**/*.log,\
repomix-output.md,**/*.p,**/*.pickle,**/.pytest_cache/**,**/.mypy_cache/**,**/frontend/public/**,\
**/*.pdf,**/*.docx,**/*.eot,**/*.ttf,**/*.woff,**/*.woff2,**/*.otf,**/*.css,**/*.js.map"
