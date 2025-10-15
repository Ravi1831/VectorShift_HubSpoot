# hubspot.py

import json
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import requests
from integrations.integration_item import IntegrationItem

from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

# HubSpot app credentials - created for this assessment
CLIENT_ID = '0fb15e09-a191-4834-88bf-ac7985a39f88'
CLIENT_SECRET = '99ffbdf3-d8f9-4a31-89bb-ace76c1d2902'
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
AUTHORIZATION_URL = f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=crm.objects.contacts.read%20crm.objects.contacts.write%20oauth'

async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = json.dumps(state_data)
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)

    return f'{AUTHORIZATION_URL}&state={encoded_state}'

async def oauth2callback_hubspot(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error'))
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    state_data = json.loads(encoded_state)

    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')

    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')

    async with httpx.AsyncClient() as client:
        response, _ = await asyncio.gather(
            client.post(
                'https://api.hubapi.com/oauth/v1/token',
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': REDIRECT_URI,
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                }
            ),
            delete_key_redis(f'hubspot_state:{org_id}:{user_id}'),
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
        raise HTTPException(status_code=400, detail='No credentials found.')
    credentials = json.loads(credentials)
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')

    return credentials

def create_integration_item_metadata_object(response_json, item_type, parent_id=None, parent_name=None):
    # Convert HubSpot API response to our IntegrationItem format
    properties = response_json.get('properties', {})
    
    # Build name depending on whether it's a company or contact
    if item_type == 'Company':
        name = properties.get('name', 'Unnamed Company')
    else:  # Contact
        firstname = properties.get('firstname', '')
        lastname = properties.get('lastname', '')
        # Fallback to email if no first/last name
        name = f"{firstname} {lastname}".strip() or properties.get('email', 'Unnamed Contact')
    
    integration_item = IntegrationItem(
        id=response_json.get('id'),
        name=name,
        type=item_type,
        parent_id=parent_id,
        parent_path_or_name=parent_name,
        creation_time=properties.get('createdate'),
        last_modified_time=properties.get('lastmodifieddate'),
    )

    return integration_item

async def get_items_hubspot(credentials):
    # Pull contacts from HubSpot using the OAuth token
    credentials = json.loads(credentials)
    access_token = credentials.get('access_token')
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    
    integration_items = []
    
    # Fetch contacts with basic info
    contacts_response = requests.get(
        'https://api.hubapi.com/crm/v3/objects/contacts',
        headers=headers,
        params={
            'limit': 100,
            'properties': 'firstname,lastname,email,createdate,lastmodifieddate,company,phone,jobtitle'
        }
    )
    
    if contacts_response.status_code == 200:
        contacts_data = contacts_response.json()
        
        for contact in contacts_data.get('results', []):
            contact_item = create_integration_item_metadata_object(
                contact,
                'Contact'
            )
            integration_items.append(contact_item)
    
    print(f'HubSpot Integration Items: {integration_items}')
    return integration_items