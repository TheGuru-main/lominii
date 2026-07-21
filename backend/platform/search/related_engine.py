from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from platform.models.search import (
    Search,
    SearchCache,
    Trending,
)

from platform.models.ai import (
    AIKnowledge,
    AIRelatedSearch,
)

from platform.ai.inference import infer_query

from platform.crawler import (
    crawl_url,
)

from platform.gsp import (
    elastic_cloud,
)

from platform.intent_analyzer import analyze