# LOMINII Social + EDU Extraction

## Purpose
Preserve the current Social and EDU source files and their identified shared
backend dependencies before any migration or removal from the active LOMINII
application.

## Source
See SOURCE_COMMIT.txt for the source Git commit.

## Preserved application code
- apps/lominii/social/
- apps/lominii/edu/

## Authoritative shared model paths
- backend/lominii_platform/models/__init__.py
- backend/lominii_platform/models/public.py
- backend/lominii_platform/models/social.py
- backend/lominii_platform/models/messages.py
- backend/lominii_platform/models/news.py
- backend/lominii_platform/models/edu.py

## Shared backend support copied
The extraction includes the platform package initializer, authentication,
content filtering, database setup, GSP, NSID, schemas, and the migration
SQL file.

## Known limitations requiring follow-up
1. Social and EDU source files import modules using the `platform.*` package
   name, while the current backend package is `lominii_platform`. Imports
   must be reconciled when migrating or running the extracted code.
2. The EDU router references modules that were not found in the inspected
   apps/backend source paths: practice, dashboard, curriculum, exams,
   analytics, AI, institutions, notifications, library, bookshop, settings,
   and profile.
3. The EDU router contains malformed-looking text and requires a separate
   repair and validation task.
4. No standalone News router or News implementation file was found in the
   inspected apps/backend paths. The news model exists, and Social files
   reference News models. News functionality is not certified complete.
5. The parent-level platform Python files in this backup are retained from
   the initial extraction pass. The copies under models/ are authoritative
   for model files. No duplicate files are deleted during preservation.

## Safety
This is a preservation backup, not a production-ready standalone package.
No active application files were removed or rewritten during extraction.
