import asyncio
from app.api.trip_planner import _resolve_edit_add_poi
from app.services.edit_intent_planner import EditIntentPlanner
from app.database import AsyncSessionFactory
from sqlalchemy import select
from app.models.poi import PointOfInterest
from geoalchemy2.functions import ST_AsGeoJSON
from app.api.trip_planner import _poi_row_to_response, _normalize_text
from typing import Any

async def main():
    planner = EditIntentPlanner()
    intent = planner.build("thêm chợ đông ba")
    op = intent.operations[0]
    
    query = op.query
    print(f"Query: {query}")
    
    text = (query or "").strip()
    category_norm = None
    tags = []
    
    # Run the scoring manually on all POIs in DB to see their scores
    POI = PointOfInterest
    async with AsyncSessionFactory() as db_session:
        stmt = (
            select(POI, ST_AsGeoJSON(POI.coordinates).label("geojson"))
            .order_by(POI.priority_score.desc())
        )
        db_res = await db_session.execute(stmt)
        rows = db_res.all()
        
    def score_row(row: Any) -> tuple[float, str, float, list[str]]:
        poi_resp = _poi_row_to_response(row)
        fields = " ".join([
            poi_resp.name or "",
            poi_resp.category or "",
            poi_resp.category_group or "",
            poi_resp.description or "",
            " ".join(poi_resp.tags or []),
        ])
        haystack = _normalize_text(fields)
        poi_category = _normalize_text(poi_resp.category_group or poi_resp.category)

        distance = 0.45
        score = max(0.0, 1.0 - min(distance, 2.0) / 2.0)
        
        token_match = False
        matched_tokens = []
        if text:
            for token in _normalize_text(text).split():
                if len(token) > 2 and token in haystack:
                    token_match = True
                    matched_tokens.append(token)
                    
        if token_match:
            score += 0.12
            
        if poi_category in {"hotel", "accommodation", "lodging"}:
            score -= 1.0
        prio_bonus = min(0.1, float(poi_resp.priority_score or 0.0) * 0.05)
        score += prio_bonus
        return score, poi_resp.name, poi_resp.priority_score, matched_tokens

    scored = [score_row(row) for row in rows]
    scored_sorted = sorted(scored, key=lambda x: x[0], reverse=True)
    
    print("Top 15 scored POIs details:")
    for s, name, prio, matched in scored_sorted[:15]:
        print(f"Score: {s:.4f} | Name: {name} | Priority: {prio} | Matched: {matched}")

if __name__ == "__main__":
    asyncio.run(main())
