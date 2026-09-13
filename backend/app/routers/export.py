import csv
import io
import json
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.actor_service import get_actor_detail
from ..models import Actor

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/{actor_id}")
def export_actor(
    actor_id: str,
    format: str = Query("json", description="Export format: csv or json"),
    db: Session = Depends(get_db),
):
    """
    Export full actor intelligence dossier in CSV or JSON format.
    """
    actor_data = get_actor_detail(actor_id=actor_id, db=db)
    if not actor_data:
        raise HTTPException(
            status_code=404,
            detail=f"Actor '{actor_id}' not found.",
        )

    if format.lower() == "json":
        json_content = json.dumps(actor_data, indent=2)
        return Response(
            content=json_content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{actor_id}_intelligence_dossier.json"'
            },
        )

    # CSV Format
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["SECTION", "FIELD_1", "FIELD_2", "FIELD_3", "FIELD_4", "FIELD_5"])

    # Actor Overview
    writer.writerow(["PROFILE", "Actor ID", actor_data["id"], "Primary Handle", actor_data["handle"], ""])
    writer.writerow(["PROFILE", "Confidence", actor_data["confidence"], "Priority", actor_data["priority"], ""])
    writer.writerow(["PROFILE", "First Seen", actor_data["firstSeen"], "Last Seen", actor_data["lastSeen"], ""])
    writer.writerow([])

    # Aliases
    writer.writerow(["ALIASES", "ID", "Handle", "Detail", "Confidence", ""])
    for a in actor_data.get("aliases", []):
        writer.writerow(["ALIAS", a.get("id"), a.get("handle"), a.get("detail"), a.get("confidence")])
    writer.writerow([])

    # Signing Keys
    writer.writerow(["KEYS", "ID", "Title", "Algorithm", "Fingerprint / Value", "Source"])
    for k in actor_data.get("keys", []):
        writer.writerow(["KEY", k.get("id"), k.get("title"), k.get("algorithm"), k.get("value"), k.get("source")])
    writer.writerow([])

    # Wallets
    writer.writerow(["WALLETS", "ID", "Title", "Network", "Address / Value", "Source"])
    for w in actor_data.get("wallets", []):
        writer.writerow(["WALLET", w.get("id"), w.get("title"), w.get("network"), w.get("value"), w.get("source")])
    writer.writerow([])

    # Evidence
    writer.writerow(["EVIDENCE", "ID", "Title", "Method", "Detail", "Confidence"])
    for e in actor_data.get("evidence", []):
        writer.writerow(["EVIDENCE", e.get("id"), e.get("title"), e.get("method"), e.get("detail"), e.get("confidence")])
    writer.writerow([])

    # Sources
    writer.writerow(["SOURCES", "ID", "Source Name", "Detail", "Observed Date", "URL"])
    for s in actor_data.get("sources", []):
        writer.writerow(["SOURCE", s.get("id"), s.get("name") or s.get("title"), s.get("detail"), s.get("observedAt") or s.get("date"), s.get("url")])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{actor_id}_intelligence_dossier.csv"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )