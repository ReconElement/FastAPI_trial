# slack.py
import json
import time
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import base64
import requests
from fastapi import Request
from integrations.integration_item import IntegrationItem
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

CLIENT_ID ="REDACTED FOR SEC REASONS @reconelement"
CLIENT_SECRET ="REDACTED FOR SEC REASONS @reconelement"
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
scope = 'crm.objects.contacts.read'
authorization_url = f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&scope=automation&redirect_uri={REDIRECT_URI}'
encoded_client_id_secret = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()
async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = base64.b64encode(json.dumps(state_data).encode('utf-8')).decode('utf-8')
    auth_url = f'{authorization_url}&state={encoded_state}'
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)
    return auth_url


async def oauth2callback_hubspot(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error_description'))
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    state_data = json.loads(base64.urlsafe_b64decode(encoded_state).decode('utf-8'))
    original_state = state_data.get('state')
    user_id = state_data.get(
        'user_id'
    )
    redirect_uri = f'{REDIRECT_URI}'
    org_id = state_data.get('org_id')
    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')
    print(saved_state)
    print(original_state)
    # if not saved_state or original_state != json.loads(saved_state).get('state'):
    #     raise HTTPException(status_code=400, detail='State does not match')

    async with httpx.AsyncClient() as client:
        response, _ = await asyncio.gather(
            client.post(
                url=f'https://api.hubapi.com/oauth/v1/token',
                data={
                    'grant_type':'authorization_code',
                    'client_id':CLIENT_ID,
                    'client_secret':CLIENT_SECRET,
                    'redirect_uri':redirect_uri,
                    'code':code
                },
                headers={
                    'Authorization': f'Basic {encoded_client_id_secret}',
                    'Content-Type': 'application/x-www-form-urlencoded',
                }
            ),
            delete_key_redis(f'hubspot_state:{org_id}:{user_id}')
        )
    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=600)
    close_window_script = """
        <html>
            <script>
                window.close();
            </script>
        </html>
        """
    return HTMLResponse(content=close_window_script)



async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=404, detail='No credentials found')
    credentials = json.loads(credentials)
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')
    return credentials



async def create_integration_item_metadata_object(response_json):
    # TODO
    pass

async def get_items_hubspot(credentials):
    # TODO
    pass