# THIS IS NOT USED AND DOES NOT WORK AND WOULD NEED CREDENTIALS HIDING ETC....
import requests

# Define connection details
server_url = 'http://192.168.1.205:8096'
username = 'Adults'
password = 'xxxx'

# Build json payload with auth data
auth_data = {
    'username': username,
    'Pw': password
}

headers = {}

# Build required connection headers
authorization = 'MediaBrowser Client="other", Device="my-script", DeviceId="some-unique-id", Version="0.0.0"'

headers['Authorization'] = authorization

# Authenticate to server
r = requests.post(server_url + '/Users/AuthenticateByName', headers=headers, json=auth_data)

# Retrieve auth token and user id from returned data
token = r.json().get('AccessToken')
user_id = r.json().get('User').get('Id')

# Update the headers to include the auth token
headers['Authorization'] = f'{authorization}, Token="{token}"'

# Requests can be made with
requests.get(f'{server_url}/api/Users', headers=headers)

