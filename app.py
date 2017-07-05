import os
import json
import datetime
from urllib.parse import urlparse, parse_qsl

import jwt
import flask
import flask_cors
import requests

TOKEN_SECRET = os.environ.get('TOKEN_SECRET')
GITHUB_SECRET = os.environ.get('GITHUB_SECRET')
ORGANIZATION_NAME = 'workingmirror'

app = flask.Flask(__name__)
cors = flask_cors.CORS(app, resources={r'/auth/': {'origins': '*', 'supports_credentials': True}})
app.config['CORS_HEADERS'] = 'Content-Type'

def fetch_access_token(client_id, redirect_uri, code):
	r = requests.get('https://github.com/login/oauth/access_token', params={
		'client_id': flask.request.json['clientId'],
		'redirect_uri': flask.request.json['redirectUri'],
		'client_secret': GITHUB_SECRET,
		'code': flask.request.json['code'],
	})
	return dict(parse_qsl(r.text))

def fetch_user(access_token):
	r = requests.get(
		'https://api.github.com/user',
		params=access_token,
		headers={'User-Agent': 'Satellizer'})
	return json.loads(r.text)

def is_member(username):
	r = requests.get('https://api.github.com/orgs/%s/members/%s' % (ORGANIZATION_NAME, username))
	return r.status_code == 204

def create_jwt(user):
	token = jwt.encode({
		'sub': user['id'],
		'iat': datetime.datetime.utcnow(),
		'exp': datetime.datetime.utcnow() + datetime.timedelta(days=14),
	}, TOKEN_SECRET)
	return token.decode('unicode_escape')

def parse_token(req):
	token = req.headers.get('Authorization').split()[1]
	return jwt.decode(token, TOKEN_SECRET)

@app.route('/auth/', methods=['POST', 'OPTIONS'])
@flask_cors.cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
def github():
	access_token = fetch_access_token(
		flask.request.json['clientId'],
		flask.request.json['redirectUri'],
		flask.request.json['code'])

	profile = fetch_user(access_token)
	response = flask.jsonify(token=create_jwt(profile), profile=profile)

	if not is_member(profile['login']):
		response.status_code = 403

	return response

if __name__ == '__main__':
	app.run(port=3000, debug=True)
