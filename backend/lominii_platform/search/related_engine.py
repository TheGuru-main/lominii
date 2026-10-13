from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lominii_platform.models.search import (
    Search,
    SearchCache,
    Trending,
)

from lominii_platform.models.ai import (
    AIKnowledge,
    AIRelatedSearch,
)

from lominii_platform.ai.summary_index import AISummaryIndexService
from lominii_platform.ai.inference import infer_query

from lominii_platform.crawler import (
    crawl_url,
)

from lominii_platform.gsp import (
    gsp_place,
    elastic_cloud,
)

from lominii_platform.intent_analyzer import analyze