import asyncio
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

upload_dir=tempfile.TemporaryDirectory(prefix='adcraft-audit-upload-access-')
os.environ['APP_ENV']='test'
os.environ['LOCAL_UPLOAD_DIR']=upload_dir.name
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.api import conversations

async def main():
    # Inert text fixture: tests HTTP exposure/MIME without executing scripts.
    Path(upload_dir.name,'audit.html').write_text('<html><body>audit fixture</body></html>')
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://audit') as client:
        response=await client.get('/uploads/audit.html')
    repo=MagicMock()
    repo.get_messages=AsyncMock(return_value=[])
    with patch.object(conversations,'MessageRepo',return_value=repo):
        result=await conversations.get_recommendations(
            uuid4(),limit=10,current_user=SimpleNamespace(id=uuid4()),db=AsyncMock(),
        )
    evidence={
        'upload_access':{'environment':'isolated local upload fixture','authenticated':False,'http':response.status_code,'content_type':response.headers.get('content-type'),'content_security_policy':response.headers.get('content-security-policy')},
        'chat_recommendation_membership':{'environment':'mock message repository; no private production messages read','authenticated_user_membership':'no membership lookup/check at this endpoint','message_repository_read_before_membership_validation':repo.get_messages.await_count==1,'response_code':result.get('code')},
        'limitations':'Tests identify missing control boundaries; they do not claim a production exploit or an actual data breach.'
    }
    Path('docs/project-audit-2026-10-26/evidence/security-reproductions.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False))
    print(json.dumps(evidence,indent=2,ensure_ascii=False))
    upload_dir.cleanup()

asyncio.run(main())
